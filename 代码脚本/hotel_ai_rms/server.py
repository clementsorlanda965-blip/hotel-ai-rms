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
from datetime import datetime, timedelta, date
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
HTML_FILE = ROOT / "九寨沟OTA价格监控.html"
PORT = 8765

# 导入采集模块
sys.path.insert(0, str(ROOT))
try:
    from ota_scraper import scrape_all, HOTELS, PLATFORMS, DEFAULT_CHECKIN, DEFAULT_CHECKOUT
    _SCRAPER_OK = True
except ImportError as e:
    print(f"⚠️ 采集模块加载失败: {e}")
    _SCRAPER_OK = False

# 缓存
_cache = {"data": None, "ts": 0, "ttl": 300}  # 5分钟缓存


def get_cached_or_fresh(force: bool = False, try_real: bool = True):
    """获取价格数据，优先缓存，过期则重新采集。

    try_real=False 时直接使用模拟数据（用于快速启动）。
    """
    now = time.time()
    if not force and _cache["data"] and (now - _cache["ts"]) < _cache["ttl"]:
        return _cache["data"]

    if _SCRAPER_OK and try_real:
        try:
            result = scrape_all(mode="auto", timeout=8.0)
            _cache["data"] = result
        except Exception as e:
            print(f"采集异常: {e}")
            result = _fallback_result(str(e)) if not _cache.get("data") else _cache["data"]
    else:
        result = _fallback_result("快速启动模式" if not try_real else "采集模块离线")

    _cache["ts"] = now
    return result


def _fallback_result(reason: str = "") -> dict:
    """兜底结果。"""
    from ota_scraper import _generate_fallback
    data = _generate_fallback()
    return {"data": data, "source": f"模拟参考({reason})", "count": len(data),
            "checkin": DEFAULT_CHECKIN, "fetched_at": datetime.now().isoformat(),
            "hotels_covered": len(set(r["酒店名称"] for r in data))}


class APIHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器。"""

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
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
            result = get_cached_or_fresh(force=force, try_real=try_real)
            if checkin:
                result["checkin"] = checkin
            self._send_json(result)

        # ── API: 强制刷新 ──
        elif path == "/api/refresh":
            _cache["ts"] = 0  # 让缓存过期
            result = get_cached_or_fresh(force=True)
            self._send_json(result)

        # ── API: 酒店列表 ──
        elif path == "/api/hotels":
            self._send_json({"hotels": HOTELS, "platforms": PLATFORMS})

        # ── API: 健康检查 ──
        elif path == "/api/health":
            self._send_json({
                "status": "ok",
                "scraper_ok": _SCRAPER_OK,
                "cache_age": round(time.time() - _cache["ts"], 1) if _cache["ts"] else None,
            })

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
        """CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    print("═" * 55)
    print("🏔️  九寨沟 OTA 价格监控服务器 v1.0")
    print("═" * 55)
    print(f"📍 地址: http://localhost:{PORT}")
    print(f"📡 API:  http://localhost:{PORT}/api/prices")
    print(f"🔄 刷新: http://localhost:{PORT}/api/refresh")
    print(f"🧩 采集模块: {'✅ 就绪' if _SCRAPER_OK else '⚠️ 离线'}")
    print()

    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    print(f"🚀 服务器已启动，按 Ctrl+C 停止")
    print(f"🌐 在浏览器打开: http://localhost:{PORT}")

    # 后台预热缓存
    import threading
    def warmup():
        print("⏳ 后台预热数据缓存（快速模式）...")
        get_cached_or_fresh(try_real=False)
        print(f"✅ 缓存就绪 ({_cache['data']['count']} 条, 来源: {_cache['data']['source']})")
    t = threading.Thread(target=warmup, daemon=True)
    t.start()

    import webbrowser
    webbrowser.open(f"http://localhost:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
