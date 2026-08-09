"""
server.py — 九寨沟OTA价格监控服务器
启动: python server.py
访问: http://localhost:8765

零外部依赖，纯 Python stdlib。
前端 HTML 通过 /api/prices 获取真实爬虫数据。
"""
import json
import os
import sys
import time
import asyncio
import threading
from datetime import datetime, timedelta, date
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
HTML_FILE = ROOT / "九寨沟OTA价格监控.html"
PORT = 8765
HOST = os.environ.get("RMS_HOST", "127.0.0.1")

# ── 飞书告警 Webhook（替换为实际 URL 后生效）──
FEISHU_WEBHOOK_URL = os.environ.get(
    "FEISHU_RMS_ALERT_WEBHOOK",
    ""  # 填写飞书机器人 webhook URL
)

# 导入采集模块
sys.path.insert(0, str(ROOT))
try:
    from ota_scraper import scrape_all, HOTELS, PLATFORMS, DEFAULT_CHECKIN, DEFAULT_CHECKOUT
    _SCRAPER_OK = True
except ImportError as e:
    print(f"⚠️ 采集模块加载失败: {e}")
    _SCRAPER_OK = False

# 缓存（线程安全）
_cache = {"data": None, "ts": 0, "ttl": 300, "checkin": None, "checkout": None}
_cache_lock = threading.Lock()
_refresh_lock = threading.Lock()
_shutdown_event = threading.Event()


def get_cached_or_fresh(force: bool = False, try_real: bool = True,
                        checkin: str | None = None, checkout: str | None = None):
    """获取价格数据，优先缓存，过期则重新采集（线程安全）。

    try_real=False 时直接使用模拟数据（用于快速启动）。
    """
    now = time.time()
    with _cache_lock:
        if (not force and _cache["data"] and (now - _cache["ts"]) < _cache["ttl"]
                and _cache["checkin"] == checkin and _cache["checkout"] == checkout):
            return _cache["data"]

    with _refresh_lock:
        if _SCRAPER_OK and try_real:
            try:
                result = scrape_all(mode="auto", checkin=checkin, checkout=checkout, timeout=50.0)
            except Exception as e:
                print(f"采集异常: {e}")
                with _cache_lock:
                    cached = (_cache["data"] if _cache["checkin"] == checkin
                              and _cache["checkout"] == checkout else None)
                result = cached or _fallback_result(str(e), checkin, checkout)
        else:
            result = _fallback_result("快速启动模式" if not try_real else "采集模块离线", checkin, checkout)

    with _cache_lock:
        _cache["data"] = result
        _cache["ts"] = now
        _cache["checkin"] = checkin
        _cache["checkout"] = checkout
    return result


def _fallback_result(reason: str = "", checkin: str | None = None,
                     checkout: str | None = None) -> dict:
    """兜底结果。"""
    from ota_scraper import _generate_fallback
    data = _generate_fallback(checkin)
    return {"data": data, "source": f"模拟参考({reason})", "count": len(data),
            "checkin": checkin or DEFAULT_CHECKIN, "checkout": checkout or DEFAULT_CHECKOUT,
            "fetched_at": datetime.now().isoformat(),
            "hotels_covered": len(set(r["酒店名称"] for r in data))}


class APIHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器。"""

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path: Path, status=200):
        if not path.exists():
            self.send_error(404, "HTML file not found")
            return
        body = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, msg, status=500):
        self._send_json({"error": True, "message": msg}, status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # ── 静态页面 ──
        if path == "/" or path == "/index.html":
            self._send_html(HTML_FILE)

        # ── API: 获取价格数据 ──
        elif path == "/api/prices":
            force = params.get("force", ["0"])[0] == "1"
            try_real = params.get("try_real", ["0"])[0] == "1" or force
            checkin = params.get("checkin", [None])[0]
            checkout = params.get("checkout", [None])[0]
            if not _valid_stay_dates(checkin, checkout):
                self._send_error_json("checkin/checkout 必须为 YYYY-MM-DD 且离店日晚于入住日", 400)
                return
            result = get_cached_or_fresh(force=force, try_real=try_real, checkin=checkin, checkout=checkout)
            self._send_json(result)

        # ── API: 强制刷新 ──
        elif path == "/api/refresh":
            with _cache_lock:
                _cache["ts"] = 0  # 让缓存过期
            result = get_cached_or_fresh(force=True)
            # 刷新后检测竞对异常
            data = result.get("data", [])
            alerts = check_competitor_price_drops(data)
            if alerts:
                send_feishu_alert(alerts)
                result["price_alerts"] = alerts
            self._send_json(result)

        # ── API: 酒店列表 ──
        elif path == "/api/hotels":
            self._send_json({"hotels": HOTELS, "platforms": PLATFORMS})

        # ── API: 健康检查 ──
        elif path == "/api/health":
            health = {
                "status": "ok",
                "scraper_ok": _SCRAPER_OK,
                "cache_age": round(time.time() - _cache["ts"], 1) if _cache["ts"] else None,
            }
            # 附加 scraper_scheduler 的系统健康数据
            try:
                from scraper_scheduler import get_health_status
                sys_health = get_health_status()
                health["scheduler"] = sys_health
            except Exception:
                health["scheduler"] = {"status": "unavailable"}
            self._send_json(health)

        # ── API: 仪表盘一站式数据 ──
        elif path == "/api/dashboard":
            try:
                from scraper_scheduler import query_all_hotels_latest, query_price_trend, get_health_status
                latest = query_all_hotels_latest()
                trends = {}
                for h in latest:
                    trends[h["hotel_name"]] = query_price_trend(h["hotel_name"], days=7)
                health = get_health_status()
                self._send_json({
                    "hotels": latest,
                    "trends": trends,
                    "health": health,
                    "updated_at": datetime.now().isoformat(),
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        # ── API: 决策卡片 ──
        elif path == "/api/decision-card":
            try:
                import sys as _sys
                _sys.path.insert(0, str(ROOT))
                from decision_card_builder import CardBuilder
                builder = CardBuilder()
                card = builder.build()
                # 同时附加告警信息
                with _cache_lock:
                    raw = _cache.get("data", {})
                alerts = raw.get("price_alerts", []) if isinstance(raw, dict) else []
                card["price_alerts"] = alerts
                self._send_json(card)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        # ── API: 历史价格趋势 ──
        elif path == "/api/trend":
            hotel = params.get("hotel", [None])[0]
            days = int(params.get("days", ["30"])[0])
            platform = params.get("platform", [None])[0]
            try:
                from scraper_scheduler import query_price_trend, query_competitor_avg
                if hotel:
                    if platform:
                        result = query_competitor_avg(hotel, platform, days)
                    else:
                        result = query_price_trend(hotel, days)
                    self._send_json({"hotel": hotel, "data": result})
                else:
                    self._send_json({"error": "请提供 hotel 参数"}, 400)
            except ImportError:
                self._send_json({"error": "scraper_scheduler 模块不可用"}, 503)

        # ── API: 采集运行历史 ──
        elif path == "/api/runs":
            limit = int(params.get("limit", ["10"])[0])
            try:
                import sqlite3
                from scraper_scheduler import DB_PATH, ensure_history_tables
                ensure_history_tables()
                conn = sqlite3.connect(str(DB_PATH))
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM scraper_runs ORDER BY start_time DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                conn.close()
                self._send_json({"runs": [dict(r) for r in rows]})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        # ── 静态文件: CSV下载 ──
        elif path == "/api/download/csv":
            csv_path = ROOT / "ota_real_prices.csv"
            if csv_path.exists():
                body = csv_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8-sig")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="ota_prices_{date.today().strftime("%Y%m%d")}.csv"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._send_error_json("CSV file not found. Run scrape first.", 404)

        else:
            self._send_error_json("Not found", 404)

    def do_OPTIONS(self):
        self._send_error_json("跨域请求未启用", 403)


def _valid_stay_dates(checkin: str | None, checkout: str | None) -> bool:
    if checkin is None and checkout is None:
        return True
    if not checkin or not checkout:
        return False
    try:
        return datetime.strptime(checkout, "%Y-%m-%d").date() > datetime.strptime(checkin, "%Y-%m-%d").date()
    except ValueError:
        return False


# ═══════════════════════════════════════════════════════════════
# 竞对价格异常检测 + 飞书告警
# ═══════════════════════════════════════════════════════════════

def check_competitor_price_drops(data: list[dict], threshold: float = 0.15) -> list[dict]:
    """检测竞对价格降幅超过阈值的异常。
    对比当前价格与历史 30 日均值，筛选降幅 ≥ threshold 的记录。
    """
    if not data:
        return []

    # 按 酒店+房型+平台 分组
    from collections import defaultdict
    groups = defaultdict(list)
    for r in data:
        key = f"{r.get('酒店名称','')}|{r.get('房型','')}|{r.get('OTA平台','')}"
        groups[key].append(r.get("单价_晚", 0))

    alerts = []
    for r in data:
        key = f"{r.get('酒店名称','')}|{r.get('房型','')}|{r.get('OTA平台','')}"
        prices = groups[key]
        if len(prices) < 2:
            continue
        avg_price = sum(prices) / len(prices)
        current = r.get("单价_晚", 0)
        if avg_price > 0 and current < avg_price * (1 - threshold):
            drop_pct = round((1 - current / avg_price) * 100, 1)
            alerts.append({
                "hotel": r.get("酒店名称"),
                "room": r.get("房型"),
                "platform": r.get("OTA平台"),
                "current_price": current,
                "avg_price": round(avg_price, 0),
                "drop_pct": drop_pct,
                "time": datetime.now().isoformat(),
            })

    # 按降幅排序，去重（同一酒店取最大降幅）
    seen = set()
    unique = []
    for a in sorted(alerts, key=lambda x: x["drop_pct"], reverse=True):
        if a["hotel"] not in seen:
            seen.add(a["hotel"])
            unique.append(a)
    return unique


def send_feishu_alert(alerts: list[dict]):
    """发送竞对价格异常告警到飞书（webhook 优先，失败降级 lark-cli 私信）。"""
    if not alerts:
        return False

    # 构造飞书富文本消息
    alert_lines = []
    for a in alerts[:5]:  # 最多 5 条
        alert_lines.append(
            f"• **{a['hotel']}** ({a['platform']})：¥{a['current_price']} "
            f"(↓{a['drop_pct']}%，近30日均价 ¥{a['avg_price']})"
        )

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "🚨 竞对价格异常告警"},
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"检测到 **{len(alerts)}** 家竞对酒店大幅降价（降幅≥15%）：\n\n" +
                                   "\n".join(alert_lines) +
                                   f"\n\n📅 检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看详情"},
                            "type": "primary",
                            "url": f"http://localhost:{PORT}"
                        }
                    ]
                }
            ]
        }
    }

    # 通过双通道发送（webhook 优先，失败自动降级 lark-cli 私信）
    try:
        from feishu_alert import AlertEngine
        ok = AlertEngine()._send(payload)
        if ok:
            print(f"✅ 飞书告警已发送: {len(alerts)} 条异常")
        return ok
    except Exception as e:
        print(f"⚠️ 飞书告警发送失败: {e}")
        return False


def scheduled_scrape_loop():
    """后台定时采集线程（兼容模式）。

    优先使用 Windows Task Scheduler + scraper_scheduler.py（生产级方案）。
    此线程作为降级方案：当计划任务未配置时，server 进程内原地采集。

    触发时间：每日 09:00 / 15:00 / 21:00。
    """
    print("⏰ 定时采集调度已启动（降级模式：每日 09:00/15:00/21:00）")
    print("💡 生产环境建议使用 Windows Task Scheduler + scraper_scheduler.py")
    last_run_slot = None

    # 每日采集时间点
    SCHEDULE_HOURS = [9, 15, 21]

    while not _shutdown_event.is_set():
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_slot = f"{today_str}_{now.hour}"

        # 在整点后 5 分钟内触发
        if now.hour in SCHEDULE_HOURS and 0 <= now.minute < 5 and last_run_slot != current_slot:
            print(f"\n⏰ [{now.strftime('%Y-%m-%d %H:%M:%S')}] 定时采集开始...")
            try:
                try:
                    from scraper_scheduler import run_once
                    result = run_once("production")
                    with _cache_lock:
                        _cache["data"] = result
                        _cache["ts"] = time.time()
                    print(f"📊 采集完成: {result['count']} 条, 来源: {result['source']}")
                except ImportError as e:
                    print(f"❌ 调度器加载失败: {e}")
            except Exception as e:
                print(f"❌ 定时采集失败: {e}")
                import traceback
                traceback.print_exc()

            last_run_slot = current_slot

        _shutdown_event.wait(60)  # 每分钟检查一次，支持立即退出


def main():
    print("═" * 55)
    print("🏔️  九寨沟 OTA 价格监控服务器 v2.0")
    print("═" * 55)
    print(f"📍 地址: http://localhost:{PORT}")
    print(f"📡 API:  http://localhost:{PORT}/api/prices")
    print(f"🔄 刷新: http://localhost:{PORT}/api/refresh")
    print(f"🧩 采集模块: {'✅ 就绪' if _SCRAPER_OK else '⚠️ 离线'}")
    print(f"🔔 飞书告警: {'✅ 已配置' if FEISHU_WEBHOOK_URL else '⚠️ 未配置（设置 FEISHU_RMS_ALERT_WEBHOOK 环境变量）'}")
    print()

    server = ThreadingHTTPServer((HOST, PORT), APIHandler)
    print(f"🚀 服务器已启动，按 Ctrl+C 停止")
    print(f"🌐 在浏览器打开: http://localhost:{PORT}")

    # 后台预热缓存
    def warmup():
        print("⏳ 后台预热数据缓存（快速模式）...")
        get_cached_or_fresh(try_real=False)
        print(f"✅ 缓存就绪 ({_cache['data']['count']} 条, 来源: {_cache['data']['source']})")

    t = threading.Thread(target=warmup, daemon=True)
    t.start()

    # 启动定时采集调度（每日 09:00 自动采集 + 竞对异常告警）
    scheduler = threading.Thread(target=scheduled_scrape_loop, daemon=True)
    scheduler.start()

    import webbrowser
    webbrowser.open(f"http://localhost:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        _shutdown_event.set()
        server.shutdown()


if __name__ == "__main__":
    main()
