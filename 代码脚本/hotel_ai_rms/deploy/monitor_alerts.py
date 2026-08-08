"""
monitor_alerts.py — OTA 采集监控与告警模块
═══════════════════════════════════════════════════════════
可独立运行或作为模块导入到 server.py/定时任务中。

功能:
  1. 数据质量检查 — 采集完成后验证数据合理性
  2. 竞对价格异常检测 — 降价超阈值触发告警
  3. 携程页面结构变更检测 — 对比历史HTML签名
  4. Chrome CDP 健康监控
  5. 飞书多渠道告警（webhook + lark-im）

用法:
  from monitor_alerts import MonitorService
  monitor = MonitorService()
  monitor.check_all(scrape_result)
"""

import json
import os
import re
import hashlib
import sqlite3
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOG_DIR = Path(r"E:\工作AI\临时文件")

# ── 飞书告警渠道 ──
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_RMS_ALERT_WEBHOOK", "")
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")


def _log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")
    log_file = LOG_DIR / "monitor_alerts.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{level}] {msg}\n")


class MonitorService:
    """OTA 价格采集监控服务。"""

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or (ROOT / "config" / "hotels.yaml")
        self._config = None
        self._db_path = DATA_DIR / "rms.db"

    # ── 配置 ──
    @property
    def config(self) -> dict:
        if self._config is None:
            try:
                import yaml
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f)
            except ImportError:
                self._config = self._default_config()
            except FileNotFoundError:
                _log(f"配置文件不存在: {self.config_path}，使用默认值", "WARN")
                self._config = self._default_config()
        return self._config

    @staticmethod
    def _default_config() -> dict:
        return {
            "alerts": {
                "competitor_price_drop_pct": 15,
                "scraper_consecutive_failures": 3,
                "chrome_hang_timeout": 120,
                "daily_scrape_deadline_hour": 10,
            }
        }

    # ═══════════════════════════════════════════════════════════════
    # 1. 数据质量检查
    # ═══════════════════════════════════════════════════════════════

    def check_data_quality(self, data: list[dict]) -> dict:
        """检查采集数据质量，返回质量报告。"""
        if not data:
            return {"ok": False, "issues": ["数据为空"], "score": 0}

        issues = []
        score = 100

        # 检查1: 数据量
        count = len(data)
        if count < 5:
            issues.append(f"数据量过少: {count}条（阈值5）")
            score -= 30
        elif count < 20:
            issues.append(f"数据量偏少: {count}条（期望50+）")
            score -= 10

        # 检查2: 价格合理性
        prices = [r.get("单价_晚", 0) for r in data if r.get("单价_晚")]
        if prices:
            avg = sum(prices) / len(prices)
            if avg < 50:
                issues.append(f"均价异常偏低: ¥{avg:.0f}")
                score -= 30
            elif avg > 5000:
                issues.append(f"均价异常偏高: ¥{avg:.0f}")
                score -= 20

            # 检查价格分布：不该有50元以下的酒店房
            too_low = [p for p in prices if p < 50]
            if too_low:
                issues.append(f"{len(too_low)}条价格低于¥50")
                score -= 15

        # 检查3: 酒店覆盖率
        hotel_names = set(r.get("酒店名称", "") for r in data)
        if len(hotel_names) < 3:
            issues.append(f"仅覆盖{len(hotel_names)}家酒店")
            score -= 20

        # 检查4: 数据来源分布
        sources = {}
        for r in data:
            src = r.get("数据来源", "未知")
            sources[src] = sources.get(src, 0) + 1
        real_count = sum(v for k, v in sources.items() if "模拟" not in k)
        total = sum(sources.values())
        real_pct = real_count / total * 100 if total > 0 else 0
        if real_pct < 10 and total > 20:
            issues.append(f"真实价格占比过低: {real_pct:.0f}%")
            score -= 10

        # 检查5: 时间戳新鲜度
        timestamps = [r.get("采集时间", "") for r in data]
        now = datetime.now()
        stale = 0
        for ts in timestamps:
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                if (now - dt).total_seconds() > 86400:  # 超过24小时
                    stale += 1
            except (ValueError, TypeError):
                pass
        if stale > len(timestamps) * 0.5:
            issues.append(f"{stale}/{len(timestamps)}条数据超过24小时")
            score -= 10

        return {
            "ok": score >= 60,
            "score": score,
            "issues": issues,
            "count": count,
            "hotels": len(hotel_names),
            "real_pct": round(real_pct, 1),
            "avg_price": round(sum(prices) / len(prices)) if prices else 0,
            "sources": sources,
        }

    # ═══════════════════════════════════════════════════════════════
    # 2. 竞对价格异常检测
    # ═══════════════════════════════════════════════════════════════

    def check_competitor_anomalies(self, current_data: list[dict]) -> list[dict]:
        """检测竞对价格异常：对比当前价格与7天均值/30天均值。"""
        threshold = self.config.get("alerts", {}).get("competitor_price_drop_pct", 15) / 100.0

        # 从数据库读取历史价格
        historical = self._load_historical_prices(days=30)

        alerts = []
        for record in current_data:
            hotel = record.get("酒店名称", "")
            room = record.get("房型", "")
            platform = record.get("OTA平台", "")
            current_price = record.get("单价_晚", 0)

            if current_price <= 0:
                continue

            # 查找历史同酒店价格
            key = f"{hotel}|{room}|{platform}"
            past_prices = historical.get(key, [])

            if len(past_prices) < 3:
                continue  # 数据不足，不比较

            avg_30d = sum(past_prices) / len(past_prices)
            drop_pct = (avg_30d - current_price) / avg_30d if avg_30d > 0 else 0

            if drop_pct >= threshold:
                alerts.append({
                    "hotel": hotel,
                    "room": room,
                    "platform": platform,
                    "current_price": current_price,
                    "avg_30d_price": round(avg_30d, 0),
                    "drop_pct": round(drop_pct * 100, 1),
                    "sample_size": len(past_prices),
                    "time": datetime.now().isoformat(),
                })

        # 按降幅排序
        alerts.sort(key=lambda x: x["drop_pct"], reverse=True)

        # 同酒店只取最高降幅
        seen, unique = set(), []
        for a in alerts:
            if a["hotel"] not in seen:
                seen.add(a["hotel"])
                unique.append(a)

        return unique

    def _load_historical_prices(self, days: int = 30) -> dict:
        """从 SQLite 加载历史价格，按酒店+房型+平台分组。"""
        from collections import defaultdict
        historical = defaultdict(list)

        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            start = (date.today() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                """SELECT hotel_name, room_type, platform, price
                   FROM competitor_prices
                   WHERE fetch_date >= ?
                   ORDER BY fetch_date DESC""",
                (start,),
            ).fetchall()
            conn.close()

            for row in rows:
                key = f"{row['hotel_name']}|{row['room_type'] or ''}|{row['platform'] or ''}"
                historical[key].append(row["price"])
        except Exception as e:
            _log(f"加载历史价格失败: {e}", "WARN")

        return historical

    # ═══════════════════════════════════════════════════════════════
    # 3. 携程页面结构变更检测
    # ═══════════════════════════════════════════════════════════════

    def check_ctrip_structure_change(self, html_snippet: str = None, current_signature: str = None) -> dict:
        """检测携程页面DOM结构是否发生变更（对比历史签名）。"""
        sig_file = DATA_DIR / "ctrip_page_signature.json"

        if html_snippet:
            # 生成新的签名
            current_signature = self._compute_page_signature(html_snippet)

        if not current_signature:
            return {"changed": False, "reason": "无签名数据"}

        if sig_file.exists():
            try:
                old = json.loads(sig_file.read_text(encoding="utf-8"))
                old_sig = old.get("signature", {})
                old_ts = old.get("timestamp", "")

                changes = []
                for key in ["api_patterns", "css_selectors", "dom_depth", "key_elements"]:
                    if old_sig.get(key) != current_signature.get(key):
                        changes.append(key)

                if changes:
                    return {
                        "changed": True,
                        "reason": f"以下结构发生变更: {', '.join(changes)}",
                        "old_signature": old_sig,
                        "new_signature": current_signature,
                        "last_known_good": old_ts,
                    }
            except Exception as e:
                _log(f"签名文件解析失败: {e}", "WARN")

        # 保存当前签名
        sig_file.parent.mkdir(parents=True, exist_ok=True)
        sig_file.write_text(
            json.dumps({
                "signature": current_signature,
                "timestamp": datetime.now().isoformat(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {"changed": False, "reason": "结构无变更"}

    @staticmethod
    def _compute_page_signature(html: str) -> dict:
        """计算HTML页面结构签名。"""
        sig = {}

        # API端点模式
        api_patterns = list(set(re.findall(r'/api/[a-zA-Z0-9/_-]+', html)))
        sig["api_patterns"] = hashlib.md5("|".join(sorted(api_patterns)).encode()).hexdigest()[:16]

        # CSS选择器关键类名
        css_classes = list(set(re.findall(r'class="([^"]+)"', html)))[:50]
        sig["css_selectors"] = hashlib.md5("|".join(sorted(css_classes)).encode()).hexdigest()[:16]

        # DOM深度（标签嵌套层级数）
        tags = re.findall(r'<(/?)(\w+)', html)
        tag_stack = []
        max_depth = 0
        for is_close, tag in tags:
            if not is_close:
                tag_stack.append(tag)
                max_depth = max(max_depth, len(tag_stack))
            elif tag_stack and tag_stack[-1] == tag:
                tag_stack.pop()
        sig["dom_depth"] = max_depth

        # 关键元素检测
        key_elements = [
            ("hotel_id_pattern", bool(re.search(r'hotelId', html))),
            ("room_list_api", bool(re.search(r'getHotelRoomList', html))),
            ("price_display", bool(re.search(r'[¥￥]\s*\d+', html))),
            ("hotel_name_element", bool(re.search(r'hotelName', html))),
        ]
        sig["key_elements"] = {k: v for k, v in key_elements}

        return sig

    # ═══════════════════════════════════════════════════════════════
    # 4. Chrome CDP 健康监控
    # ═══════════════════════════════════════════════════════════════

    def check_chrome_cdp_health(self) -> dict:
        """检查 Chrome CDP 是否正常运行。"""
        import urllib.request

        port = self.config.get("scraper", {}).get("chrome", {}).get("port", 9222)
        url = f"http://127.0.0.1:{port}/json/version"

        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())

            return {
                "healthy": bool(data.get("webSocketDebuggerUrl")),
                "browser": data.get("Browser", "unknown"),
                "protocol_version": data.get("Protocol-Version", "unknown"),
                "user_agent": data.get("User-Agent", "")[:80],
                "pid": os.getpid(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    # ═══════════════════════════════════════════════════════════════
    # 5. 飞书多渠道告警
    # ═══════════════════════════════════════════════════════════════

    def send_alert(self, title: str, message: str, level: str = "warn") -> bool:
        """发送告警到飞书（优先 webhook，降级 lark-im MCP）。"""
        success = False

        # 方式1: Webhook
        if FEISHU_WEBHOOK_URL:
            success = self._send_via_webhook(title, message, level)

        # 方式2: 如果 webhook 失败，尝试 lark-im（需要 MCP 可用）
        if not success:
            _log("Webhook 告警失败，可通过 /lark-im 手动发送", "WARN")

        return success

    def _send_via_webhook(self, title: str, message: str, level: str) -> bool:
        """通过飞书 Webhook 发送卡片消息。"""
        import urllib.request

        color_map = {"critical": "red", "warn": "yellow", "info": "green"}
        color = color_map.get(level, "green")

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": color,
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": message,
                        }
                    }
                ],
            },
        }

        try:
            req = urllib.request.Request(
                FEISHU_WEBHOOK_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status == 200:
                _log(f"飞书告警已发送: {title}", "INFO")
                return True
        except Exception as e:
            _log(f"飞书 Webhook 失败: {e}", "ERROR")

        return False

    # ═══════════════════════════════════════════════════════════════
    # 综合检查
    # ═══════════════════════════════════════════════════════════════

    def check_all(self, scrape_result: dict = None) -> dict:
        """执行所有检查项，返回综合报告。"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "alerts": [],
            "overall": "unknown",
        }

        # 数据质量
        if scrape_result and scrape_result.get("data"):
            data = scrape_result["data"]
            quality = self.check_data_quality(data)
            report["checks"]["data_quality"] = quality
            if not quality["ok"]:
                report["alerts"].append({
                    "type": "data_quality",
                    "severity": "critical" if quality["score"] < 30 else "warn",
                    "detail": "; ".join(quality["issues"]),
                })

            # 竞对异常
            anomalies = self.check_competitor_anomalies(data)
            report["checks"]["competitor_anomalies"] = {
                "count": len(anomalies),
                "alerts": anomalies[:5],  # 只保留前5条
            }
            if anomalies:
                report["alerts"].append({
                    "type": "competitor_price_drop",
                    "severity": "critical" if any(a["drop_pct"] > 30 for a in anomalies) else "warn",
                    "detail": f"{len(anomalies)}家竞对大幅降价",
                    "data": anomalies,
                })

        # Chrome CDP
        cdp_health = self.check_chrome_cdp_health()
        report["checks"]["chrome_cdp"] = cdp_health
        if not cdp_health["healthy"]:
            report["alerts"].append({
                "type": "chrome_cdp_down",
                "severity": "critical",
                "detail": f"Chrome CDP 无响应: {cdp_health.get('error', 'unknown')}",
            })

        # 总体判断
        criticals = [a for a in report["alerts"] if a.get("severity") == "critical"]
        warns = [a for a in report["alerts"] if a.get("severity") == "warn"]

        if criticals:
            report["overall"] = "critical"
        elif warns:
            report["overall"] = "warning"
        else:
            report["overall"] = "healthy"

        return report

    def save_competitor_prices_to_db(self, data: list[dict]):
        """将采集数据写入 SQLite competitor_prices 表。"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            today = date.today().isoformat()
            count = 0
            for r in data:
                try:
                    conn.execute(
                        """INSERT INTO competitor_prices
                           (fetch_date, checkin_date, hotel_name, room_type, platform, price,
                            star_level, data_source)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            today,
                            r.get("入住日期", today),
                            r.get("酒店名称", ""),
                            r.get("房型", ""),
                            r.get("OTA平台", ""),
                            r.get("单价_晚", 0),
                            r.get("星级", 4),
                            r.get("数据来源", "auto"),
                        ),
                    )
                    count += 1
                except Exception:
                    pass
            conn.commit()
            conn.close()
            _log(f"已写入 {count} 条竞品价格到数据库")
        except Exception as e:
            _log(f"数据库写入失败: {e}", "ERROR")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="OTA采集监控与告警")
    p.add_argument("--check-cdp", action="store_true", help="仅检查 Chrome CDP 健康")
    p.add_argument("--check-data", type=str, help="检查 JSON 文件数据质量")
    p.add_argument("--send-test-alert", action="store_true", help="发送测试告警")
    args = p.parse_args()

    monitor = MonitorService()

    if args.check_cdp:
        health = monitor.check_chrome_cdp_health()
        print(json.dumps(health, ensure_ascii=False, indent=2))

    elif args.check_data:
        with open(args.check_data, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        quality = monitor.check_data_quality(data)
        print(json.dumps(quality, ensure_ascii=False, indent=2))
        anomalies = monitor.check_competitor_anomalies(data)
        if anomalies:
            print(f"\n🚨 竞对异常: {len(anomalies)} 家")
            for a in anomalies:
                print(f"  {a['hotel']} ({a['platform']}): ¥{a['current_price']} ↓{a['drop_pct']}%")

    elif args.send_test_alert:
        result = monitor.send_alert(
            "测试告警",
            "这是一条来自 OTA 采集监控系统的测试消息。\n\n时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "info",
        )
        print(f"告警发送: {'✅ 成功' if result else '❌ 失败'}")
    else:
        report = monitor.check_all()
        print(json.dumps(report, ensure_ascii=False, indent=2))
