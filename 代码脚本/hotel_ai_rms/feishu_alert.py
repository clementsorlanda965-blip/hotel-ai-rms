"""
飞书告警模块 — 价格异常检测 + 飞书消息推送
可独立使用，也可被 server.py / scraper_scheduler.py 导入

用法:
  from feishu_alert import AlertEngine
  engine = AlertEngine()
  engine.send_price_drop_alert([{"hotel_name": "XX", "prev_price": 500, "current_price": 400, "drop_pct": 20}])
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent

FEISHU_WEBHOOK_URL = os.environ.get(
    "FEISHU_RMS_ALERT_WEBHOOK",
    ""  # 填写飞书机器人 webhook URL: https://open.feishu.cn/open-apis/bot/v2/hook/xxx
)

# 兜底通道：无 webhook 时用 lark-cli（bot 身份）直发用户私信
# lark-cli 实际是 .ps1/.cmd 包装器，subprocess 不可直接调用，改用 node 直接执行其脚本入口
_LARK_ENTRY = r"E:\claude-code\node_modules\@larksuite\cli\scripts\run.js"
LARK_CLI = os.environ.get("LARK_CLI_NODE_ENTRY", _LARK_ENTRY if Path(_LARK_ENTRY).exists() else "lark-cli")
FEISHU_USER_ID = os.environ.get("FEISHU_RMS_USER_ID", "")


def _resolve_user_id() -> str:
    """解析飞书接收人 open_id。

    优先级：
      1. 环境变量 FEISHU_RMS_USER_ID（含持久化注册表，新进程可读）
      2. Windows 注册表 HKCU\\Environment（会话缓存时兜底）
      3. lark-cli auth status 自动探测当前登录用户
    """
    user_id = FEISHU_USER_ID.strip()
    if user_id:
        return user_id

    # 注册表兜底（解决会话内新进程读不到 User 级变量的情况）
    if sys.platform == "win32":
        try:
            proc = subprocess.run(
                ["reg", "query", "HKCU\\Environment", "/v", "FEISHU_RMS_USER_ID"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in proc.stdout.splitlines():
                if "REG_SZ" in line:
                    parts = line.strip().split()
                    candidate = parts[-1].strip()
                    if candidate.startswith("ou_"):
                        return candidate
        except Exception:
            pass

    # lark-cli auth status 探测
    try:
        proc = _lark_cli_run("auth", "status", timeout=15)
        data = json.loads(proc.stdout or "{}")
        identities = data.get("identities", {})
        # 优先 bot 身份的用户？这里取登录用户（user）的 openId
        user = identities.get("user", {})
        oid = user.get("openId", "")
        if oid:
            return oid
        # 兜底：任一 identity 里的 openId
        for v in identities.values():
            if isinstance(v, dict) and v.get("openId"):
                return v["openId"]
    except Exception:
        pass
    return ""


def _lark_cli_run(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """执行 lark-cli 子命令。LARK_CLI 可能是绝对 node 入口或命令名。"""
    if Path(LARK_CLI).exists():
        return subprocess.run(
            ["node", LARK_CLI, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    return subprocess.run(
        [LARK_CLI, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _lark_cli_available() -> bool:
    """lark-cli 是否可调用（一次探测缓存）。"""
    if not hasattr(_lark_cli_available, "_probed"):
        try:
            proc = _lark_cli_run("auth", "status", timeout=15)
            _lark_cli_available._probed = proc.returncode == 0
        except Exception:
            _lark_cli_available._probed = False
    return _lark_cli_available._probed


class AlertEngine:
    """飞书告警引擎"""

    def __init__(self, webhook_url: str = None):
        self.webhook = webhook_url or FEISHU_WEBHOOK_URL
        self._sent_cache = set()  # 防重复发送

    # ── 价格降幅告警 ──

    def send_price_drop_alert(self, alerts: list[dict]) -> bool:
        """发送竞对价格降幅告警
        alerts: [{"hotel_name", "prev_price", "current_price", "drop_pct"}, ...]
        """
        if not alerts:
            return False

        # 按降幅排序
        sorted_alerts = sorted(alerts, key=lambda x: x.get("drop_pct", 0), reverse=True)

        alert_lines = []
        for a in sorted_alerts[:10]:
            cache_key = f"{a['hotel_name']}|{a.get('current_price', 0)}|{datetime.now().strftime('%Y%m%d')}"
            if cache_key in self._sent_cache:
                continue
            self._sent_cache.add(cache_key)

            emoji = "🔴" if a.get("drop_pct", 0) >= 30 else ("🟠" if a.get("drop_pct", 0) >= 20 else "🟡")
            alert_lines.append(
                f"{emoji} **{a['hotel_name']}**：¥{a.get('prev_price', '?')} → "
                f"¥{a.get('current_price', '?')}（↓{a.get('drop_pct', 0)}%）"
            )

        if not alert_lines:
            return False  # 全部已发送过

        total = len(sorted_alerts)
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "🚨 竞对价格异常告警"},
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"检测到 **{total}** 家竞对酒店大幅降价（降幅≥15%）：\n\n"
                                + "\n".join(alert_lines)
                                + f"\n\n📅 检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
                            ),
                        }
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "查看监控面板"},
                                "type": "primary",
                                "url": "http://localhost:8765",
                            }
                        ],
                    },
                ],
            },
        }

        return self._send(payload)

    # ── 价格倒挂告警（自己酒店在美团/同程低于携程>5%）──

    def send_price_inversion_alert(self, own_hotel: str, inversions: list[dict]) -> bool:
        """价格倒挂告警。
        inversions: [{"platform", "ctrip_price", "other_price", "gap_pct"}, ...]
        """
        if not inversions:
            return False

        lines = []
        for inv in inversions:
            lines.append(
                f"⚠️ **{inv['platform']}** ¥{inv['other_price']} vs "
                f"携程 ¥{inv['ctrip_price']}（倒挂 {inv['gap_pct']}%）"
            )

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"⚡ {own_hotel} 价格倒挂风险"},
                    "template": "orange",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**{own_hotel}** 在其他渠道价格低于携程：\n\n"
                                + "\n".join(lines)
                                + f"\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                            ),
                        }
                    }
                ],
            },
        }
        return self._send(payload)

    # ── 采集失败告警 ──

    def send_scrape_failure_alert(self, error_msg: str, hotels_missing: list[str] = None) -> bool:
        """采集失败告警"""
        missing_text = ""
        if hotels_missing:
            missing_text = f"\n\n缺失酒店：{', '.join(hotels_missing)}"

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "❌ OTA价格采集异常"},
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**采集失败**\n\n错误：{error_msg}"
                                + missing_text
                                + f"\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                            ),
                        }
                    }
                ],
            },
        }
        return self._send(payload)

    # ── 每日汇总报告 ──

    def send_daily_summary(self, summary: dict) -> bool:
        """发送每日价格监控汇总"""
        hotels = summary.get("hotels_covered", 0)
        total = summary.get("total_hotels", 15)
        source = summary.get("source", "未知")
        prices = summary.get("prices", {})

        price_lines = []
        for name in sorted(prices, key=lambda n: prices[n])[:15]:
            price_lines.append(f"• {name}：¥{prices[name]}")

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "📊 OTA价格日报"},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**覆盖：{hotels}/{total} 家** | 数据来源：{source}\n\n"
                                + "\n".join(price_lines)
                                + f"\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                            ),
                        }
                    }
                ],
            },
        }
        return self._send(payload)

    # ── 客源细分日报 ──

    def send_segment_report(self, summary: dict) -> bool:
        """发送客源细分日报（渠道占比/入住时长/价值分级 + 健康告警）。

        summary 结构（来自 segment_engine.build_daily_summary）：
          {"ok", "date", "lines", "health", "alerts"}
        webhook 优先，未配置/失败时自动降级 lark-cli 私信。
        """
        if not summary or not summary.get("ok"):
            return False

        lines = summary.get("lines", [])
        alerts = summary.get("alerts", [])

        content_lines = []
        if lines:
            content_lines.append("**🎯 客源价值分级（按净贡献）**\n")
            content_lines.extend(lines[:6])

        # 健康诊断
        health = summary.get("health", [])
        if health:
            warn = [h for h in health if h["status"] == "WARN"]
            ok_count = len(health) - len(warn)
            content_lines.append(f"\n**🏥 渠道健康度：** {len(warn)} 项待关注 / {ok_count} 项正常")
            for h in health:
                mark = "⚠️" if h["status"] == "WARN" else "✅"
                content_lines.append(
                    f"{mark} {h['label']}：当前 {h['actual']}%（目标 {h['target']}）"
                )

        if alerts:
            content_lines.append("\n## 🔴 红牌告警")
            for a in alerts[:5]:
                content_lines.append(f"- {a['title']}：{a['detail']}")

        header_title = "📊 九寨沟酒店 · 客源细分日报"
        template = "red" if alerts else "blue"
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": header_title},
                    "template": template,
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "\n".join(content_lines)
                            + f"\n\n📅 报告日期：{summary.get('date', '')}",
                        },
                    }
                ],
            },
        }
        return self._send(payload)

    # ── 底层发送 ──

    def _send(self, payload: dict) -> bool:
        """webhook 优先，失败/未配置时降级 lark-cli 私信。"""
        if self.webhook and str(self.webhook).startswith("http"):
            try:
                req = urllib.request.Request(
                    self.webhook,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
                resp = urllib.request.urlopen(req, timeout=10)
                result = json.loads(resp.read().decode())
                ok = result.get("code") == 0 or result.get("StatusCode") == 0
                if ok:
                    print("✅ 飞书告警已发送（webhook）")
                    return True
                print(f"⚠️ 飞书返回异常: {result}")
            except Exception as e:
                print(f"⚠️ 飞书 webhook 发送失败({e})，尝试 lark-cli 降级…")
        return self._send_via_lark_cli(payload)

    def _send_via_lark_cli(self, payload: dict) -> bool:
        """通过 lark-cli（bot 身份）发送同内容卡片到用户私信。"""
        user_id = _resolve_user_id()
        if not user_id:
            print("⚠️ 未发送（无 webhook 且无法解析 FEISHU_RMS_USER_ID）")
            return False
        if not _lark_cli_available():
            print("⚠️ 未发送（lark-cli 不可用）")
            return False

        title = ""
        content = ""
        try:
            header = payload.get("card", {}).get("header", {})
            t = header.get("title", {})
            title = t.get("content", "") if isinstance(t, dict) else str(t)
            elements = payload.get("card", {}).get("elements", [])
            if elements:
                el = elements[0]
                text = el.get("text", {})
                if isinstance(text, dict):
                    content = text.get("content", "")
                elif isinstance(text, str):
                    content = text
        except Exception:
            pass

        md = f"**{title or '飞书告警'}**\n\n{content}" if title else f"{content}"
        md = md.replace("\n📅", "\n\n📅")
        try:
            proc = _lark_cli_run(
                "im", "+messages-send",
                "--as", "bot",
                "--user-id", user_id,
                "--markdown", md,
                timeout=30,
            )
            result = json.loads(proc.stdout or "{}")
            ok = bool(result.get("ok")) or result.get("code", 1) == 0
            if ok:
                print("✅ 飞书告警已发送（lark-cli bot 私信）")
            else:
                err = result.get("error", {}).get("message", proc.stdout[:200] if proc.stdout else "")
                print(f"⚠️ lark-cli 发送失败: {err}")
            return ok
        except Exception as e:
            print(f"⚠️ lark-cli 发送异常: {e}")
            return False


# ── 便捷函数 ──

def send_price_drop_alert(alerts: list[dict]) -> bool:
    """发送价格降幅告警（便捷函数）"""
    return AlertEngine().send_price_drop_alert(alerts)


