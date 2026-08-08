import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import database
import feishu_alert
import ota_scraper
import server
import segment_engine
import segment_scheduler


class DatabaseUpsertTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = database.DB_PATH
        self.old_initialized = database._db_initialized
        database.DB_PATH = Path(self.temp_dir.name) / "rms.db"
        database._db_initialized = False

    def tearDown(self):
        database.DB_PATH = self.old_path
        database._db_initialized = self.old_initialized
        self.temp_dir.cleanup()

    def test_daily_metrics_upsert_matches_hotel_date_source_constraint(self):
        metrics = {"hotel_id": 1, "date": "2026-08-08", "source": "manual", "adr": 500}
        database.save_daily_metrics(metrics)
        database.save_daily_metrics({**metrics, "adr": 600})

        conn = database.get_conn()
        rows = conn.execute("SELECT adr FROM daily_metrics").fetchall()
        conn.close()
        self.assertEqual([row["adr"] for row in rows], [600])

    def test_budget_target_upsert_matches_hotel_year_month_constraint(self):
        database.save_budget_target(2026, 8, {"adr": 500})
        database.save_budget_target(2026, 8, {"adr": 600})

        conn = database.get_conn()
        rows = conn.execute("SELECT target_adr FROM budget_targets").fetchall()
        conn.close()
        self.assertEqual([row["target_adr"] for row in rows], [600])


class ScraperAndServerTests(unittest.TestCase):
    def test_fallback_rows_are_explicitly_not_real_prices(self):
        rows = ota_scraper._generate_fallback("2026-08-10")
        self.assertTrue(rows)
        self.assertTrue(all(row["is_real"] is False for row in rows))

    def test_cache_forwards_requested_stay_dates_to_scraper(self):
        expected = {"data": [], "source": "test", "count": 0}
        with patch.object(server, "_SCRAPER_OK", True), patch.object(
            server, "scrape_all", return_value=expected
        ) as scrape:
            server.get_cached_or_fresh(
                force=True,
                checkin="2026-09-01",
                checkout="2026-09-02",
            )

        scrape.assert_called_once_with(
            mode="auto",
            checkin="2026-09-01",
            checkout="2026-09-02",
            timeout=50.0,
        )

    def test_server_feishu_alert_falls_back_to_dual_channel(self):
        """server 的告警在无 webhook 时走 lark-cli 兜底（不再硬拒）。"""
        alerts = [{"hotel": "九寨沟A酒店", "platform": "携程", "current_price": 300,
                   "drop_pct": 25, "avg_price": 420}]
        fake = type("E", (), {"_send": lambda self, payload: True})
        with patch("feishu_alert.AlertEngine", fake):
            ok = server.send_feishu_alert(alerts)
        self.assertTrue(ok)


class SegmentEngineTests(unittest.TestCase):
    """客源细分核心逻辑测试。"""

    def test_segment_assignment_covers_all_customers(self):
        """每个客户都能归类到合法客源类型，且六类均有样本。"""
        df = segment_engine.generate_sample_customers(220)
        valid = set(segment_engine.SEGMENT_TYPES.keys())
        self.assertTrue(set(df["segment_type"]).issubset(valid))
        # 六类客源在模拟数据中都应出现
        self.assertEqual(len(df["segment_type"].unique()), 6)

    def test_segment_mix_sums_equal_customer_count(self):
        """segment_mix 汇总客户数 = 明细客户数（无遗漏）。"""
        df = segment_engine.generate_sample_customers(220)
        mix = segment_engine.segment_mix_from_customers(df)
        self.assertEqual(int(mix["customer_count"].sum()), len(df))
        # 佣金>0（OTA有佣金），净贡献 = 收入 - 佣金
        self.assertTrue((mix["commission"] >= 0).all())

    def test_los_distribution_reasonable(self):
        """平均入住时长应在合理区间，长住客明显更长。"""
        df = segment_engine.generate_sample_customers(220)
        self.assertGreaterEqual(df["avg_stay_length"].min(), 1.0)
        self.assertLessEqual(df["avg_stay_length"].max(), 15.0)
        long_stay = df.loc[df["segment_type"] == "长住客", "avg_stay_length"]
        other = df.loc[df["segment_type"] != "长住客", "avg_stay_length"]
        if len(long_stay) and len(other):
            self.assertGreater(long_stay.mean(), other.mean())

    def test_health_diagnosis_and_value_tiers(self):
        """健康诊断返回 5 项；价值分级 A/B/C 齐全且累计占比≈100。"""
        df = segment_engine.generate_sample_customers(220)
        mix = segment_engine.segment_mix_from_customers(df)
        health = segment_engine.diagnose_health(mix)
        self.assertEqual(len(health), len(segment_engine.DEFAULT_HEALTH_RULES))
        ranked = segment_engine.rank_segments(mix)
        self.assertEqual(set(ranked["价值等级"]), {"A", "B", "C"})
        self.assertAlmostEqual(ranked["贡献占比"].sum(), 100.0, delta=1.0)

    def test_csv_import_alias_mapping(self):
        """导入真实CSV支持列别名映射（渠道/los/total_spend）。"""
        raw = pd.DataFrame({
            "id": ["A1", "A2"],
            "渠道": ["携程", "企业协议"],
            "total_spend": [1000, 50000],
            "los": [2, 3],
        })
        out = segment_engine.parse_segment_csv(raw)
        self.assertEqual(list(out["segment_type"]), ["OTA线上客", "企业商务客"])
        self.assertEqual(len(out), 2)

    def test_geo_schema_json_roundtrip(self):
        """GEO 结构化数据块可 JSON 序列化，且含必要语义字段。"""
        block = segment_engine.build_geo_block({"name": "测试酒店"})
        import json
        dumped = json.dumps(block, ensure_ascii=False)
        loaded = json.loads(dumped)
        self.assertIn("name", loaded)
        self.assertIn("room_types", loaded)
        self.assertIn("ota", loaded)


class SegmentSchedulerTests(unittest.TestCase):
    """飞书日报调度器：安全降级 + 日级去重。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = database.DB_PATH
        self.old_initialized = database._db_initialized
        database.DB_PATH = Path(self.tmp.name) / "rms.db"
        database._db_initialized = False

    def tearDown(self):
        database.DB_PATH = self.old_path
        database._db_initialized = self.old_initialized
        self.tmp.cleanup()

    def test_daily_report_safe_when_no_webhook(self):
        """无 webhook 且无法解析接收人时应安全失败，不抛异常也不误标记已发送。"""
        with patch("feishu_alert.FEISHU_WEBHOOK_URL", ""), \
             patch.object(feishu_alert, "_resolve_user_id", return_value=""):
            result = segment_scheduler.run_daily()
        self.assertTrue(result["ok"])
        self.assertFalse(result["sent"])
        self.assertIsNone(database.get_report_state("segment_daily"))

    def test_daily_report_deduplication(self):
        """当日已发送后再次运行应跳过（force=True 除外）。"""
        sent = {"count": 0}

        class FakeEngine:
            def __init__(self):
                pass

            def send_segment_report(self, summary):
                sent["count"] += 1
                return True

        with patch("feishu_alert.AlertEngine", FakeEngine):
            first = segment_scheduler.run_daily()
            second = segment_scheduler.run_daily()
        self.assertTrue(first["sent"])
        self.assertFalse(second["sent"])
        self.assertEqual(sent["count"], 1)
        self.assertEqual(database.get_report_state("segment_daily"),
                         segment_scheduler.date.today().isoformat())


class FeishuDualChannelTests(unittest.TestCase):
    """飞书双通道：webhook 优先、lark-cli 兜底、空配置安全降级。"""

    def setUp(self):
        self.old_webhook = os.environ.get("FEISHU_RMS_ALERT_WEBHOOK")
        self.old_user = os.environ.get("FEISHU_RMS_USER_ID")
        os.environ.pop("FEISHU_RMS_ALERT_WEBHOOK", None)
        os.environ.pop("FEISHU_RMS_USER_ID", None)

    def tearDown(self):
        for k, v in [
            ("FEISHU_RMS_ALERT_WEBHOOK", self.old_webhook),
            ("FEISHU_RMS_USER_ID", self.old_user),
        ]:
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _engine(self):
        # 每次重建以重新读取环境变量
        return feishu_alert.AlertEngine(webhook_url=None)

    def test_dual_channel_uses_webhook_when_configured(self):
        """配置 webhook 时优先走 webhook 且不回退 lark。"""
        feishu_alert.FEISHU_WEBHOOK_URL = ""
        fake_resp = type("R", (), {"read": lambda self: b'{"code":0}'})()
        with patch("urllib.request.urlopen", return_value=fake_resp), \
             patch.object(feishu_alert, "_lark_cli_run") as run:
            ok = feishu_alert.AlertEngine(webhook_url="https://open.feishu.cn/hook/test").send_price_drop_alert(
                [{"hotel_name": "A", "prev_price": 500, "current_price": 400, "drop_pct": 20}]
            )
        self.assertTrue(ok)
        run.assert_not_called()

    def test_dual_channel_falls_back_to_lark_cli(self):
        """webhook 发送失败时降级 lark-cli，且内容保留标题。"""
        with patch.object(feishu_alert, "_resolve_user_id", return_value="ou_test_user"), \
             patch.object(feishu_alert, "_lark_cli_available", return_value=True), \
             patch("urllib.request.urlopen", side_effect=Exception("network down")), \
             patch.object(feishu_alert, "_lark_cli_run") as run:
            run.return_value = type("P", (), {"stdout": '{"ok":true}', "returncode": 0})()
            ok = feishu_alert.AlertEngine(webhook_url="http://bad").send_price_drop_alert(
                [{"hotel_name": "A", "prev_price": 500, "current_price": 400, "drop_pct": 20}]
            )
        self.assertTrue(ok)
        run.assert_called_once()
        args = run.call_args[0]
        self.assertIn("+messages-send", args)
        # 降级通道应把卡片标题带进 markdown
        md = args[args.index("--markdown") + 1]
        self.assertIn("竞对价格异常告警", md)

    def test_dual_channel_safe_without_any_config(self):
        """无 webhook 且无法解析 USER_ID 时安全返回 False，不抛异常不误发。"""
        with patch.object(feishu_alert, "_resolve_user_id", return_value=""):
            ok = feishu_alert.AlertEngine(webhook_url="").send_price_drop_alert(
                [{"hotel_name": "A", "prev_price": 500, "current_price": 400, "drop_pct": 20}]
            )
        self.assertFalse(ok)

    def test_resolve_user_id_auto_discovers(self):
        """进程环境为空时，能从注册表/lark-cli 自动解析 open_id。"""
        with patch.object(feishu_alert, "FEISHU_USER_ID", ""):
            user_id = feishu_alert._resolve_user_id()
        self.assertIn("ou_", user_id)

    def test_segment_card_payload_structure(self):
        """客源日报卡片 payload 结构：标题/分级/健康度/告警齐全。"""
        import json
        mix = segment_engine.segment_mix_from_customers(segment_engine.generate_sample_customers(220))
        summary = segment_engine.build_daily_summary(mix)
        payload = feishu_alert.AlertEngine(webhook_url="http://x")._build_segment_payload(summary) \
            if hasattr(feishu_alert.AlertEngine, "_build_segment_payload") else None
        if payload is None:
            # 无独立构造方法时，直接走真实 send 并用假 webhook 捕获 payload
            captured = {}
            def fake_urlopen(req, timeout=10):
                captured["payload"] = json.loads(req.data.decode("utf-8"))
                return type("R", (), {"read": lambda self: b'{"code":0}'})()
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                ok = feishu_alert.AlertEngine(webhook_url="http://x").send_segment_report(summary)
            self.assertTrue(ok)
            payload = captured["payload"]

        card = payload["card"]
        title = card["header"]["title"]["content"]
        self.assertIn("客源细分日报", title)
        text = card["elements"][0]["text"]["content"]
        self.assertIn("客源价值分级", text)
        self.assertIn("渠道健康度", text)
        # 价值分级行数与健康度 5 项
        self.assertGreaterEqual(text.count("等级"), 3)


if __name__ == "__main__":
    unittest.main()
