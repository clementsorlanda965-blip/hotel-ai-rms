"""
携程真实房价采集器 v5.0
- 直接使用已确认的携程酒店ID（11家），无需列表页匹配
- 双路径价格提取: cancelInfo (国内) + priceInfo (国际)
- 每4家重启Chrome避免反爬
- 可独立运行，也可被 ota_scraper.py 导入
"""
import asyncio, subprocess, json, re, random, sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
CHROME_PORT = 9222
CHROME_USER_DATA = ROOT / "chrome_cdp_profile"
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 4家目标酒店 + 已确认携程ID
TARGET_HOTELS = [
    {"name": "九寨沟诺富特酒店", "ctrip_id": "133579644"},
    {"name": "九寨沟万怡酒店", "ctrip_id": "110034462"},
    {"name": "九寨沟德尔塔酒店", "ctrip_id": "104424550"},
    {"name": "全季酒店九寨沟九寨大道店", "ctrip_id": "123577708"},
]


def extract_prices(api_body: str) -> list[dict]:
    """
    双路径价格提取:
    - 路径1: cancelInfo.ladderDetailInfo[].customCurrencyPrice.amount (国内酒店)
    - 路径2: priceInfo.price (国际品牌)
    """
    data = json.loads(api_body) if isinstance(api_body, str) else api_body
    srm = data.get("data", {}).get("saleRoomMap", {})
    prm = data.get("data", {}).get("physicRoomMap", {})

    results = {}
    for sid, sinfo in srm.items():
        phys_id = str(sinfo.get("physicalRoomId", ""))
        room_name = prm.get(phys_id, {}).get("name", f"Room_{phys_id}")
        price = None

        # 路径1: cancelInfo.ladderDetailInfo[].customCurrencyPrice.amount
        ci = sinfo.get("cancelInfo", {})
        for ladder in (ci.get("ladderDetailInfo", []) or []):
            ccp = ladder.get("customCurrencyPrice", {})
            amt = ccp.get("amount")
            if amt and isinstance(amt, (int, float)) and 200 < amt < 50000:
                price = amt
                break

        # 路径2: priceInfo.price (希尔顿/丽思/智选等国际品牌)
        if not price:
            pi = sinfo.get("priceInfo", {})
            amt = pi.get("price")
            if amt and isinstance(amt, (int, float)) and 200 < amt < 50000:
                price = amt

        if price and (room_name not in results or price < results[room_name]):
            results[room_name] = price

    return sorted(results.items(), key=lambda x: x[1])


class CtripScraper:
    """携程CDP采集器"""

    def __init__(self):
        self.browser = None
        self.ctx = None
        self._proc = None
        self._pw = None

    async def start(self, force_restart: bool = False):
        """启动Chrome CDP（精确PID管理，不杀其他Chrome）。
        force_restart=True 时强制杀掉当前CDP进程重新启动，避免复用旧会话。
        """
        if force_restart:
            await self._kill_port_owner()
            await asyncio.sleep(2)

        # 检查端口是否已有可用的 Chrome CDP
        if not force_restart and await self._check_cdp_alive():
            print("  Chrome CDP 已运行，直接复用")
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().__aenter__()
            self.browser = await self._pw.chromium.connect_over_cdp(
                f"http://127.0.0.1:{CHROME_PORT}")
            self.ctx = self.browser.contexts[0]
            return

        # 仅杀本端口关联的僵尸进程（不杀用户正在用的 Chrome）
        if not force_restart:
            await self._kill_port_owner()

        self._proc = subprocess.Popen(
            [CHROME_EXE, f"--remote-debugging-port={CHROME_PORT}",
             f"--user-data-dir={CHROME_USER_DATA}",
             "--no-first-run", "--no-default-browser-check",
             "--disable-background-networking", "--disable-sync",
             "--disable-component-update"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        print(f"  Chrome CDP 已启动 PID={self._proc.pid}")

        # 等待就绪（最多15秒）
        for i in range(15):
            await asyncio.sleep(1)
            if await self._check_cdp_alive():
                print(f"  Chrome CDP 就绪 (耗时{i+1}s)")
                break

        from playwright.async_api import async_playwright
        self._pw = await async_playwright().__aenter__()
        self.browser = await self._pw.chromium.connect_over_cdp(
            f"http://127.0.0.1:{CHROME_PORT}")
        self.ctx = self.browser.contexts[0]

    async def stop(self):
        """仅关闭 Playwright 连接，不杀 Chrome 进程（保留给 Watchdog 管理）。"""
        try:
            if self.browser:
                await self.browser.close()
        except:
            pass
        try:
            if self._pw:
                await self._pw.stop()
        except:
            pass
        # 不再 kill Chrome——留给 Watchdog 管理生命周期

    async def shutdown_chrome(self):
        """关闭本次启动的 Chrome 进程（仅批次间重启时调用）。"""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
                print(f"  Chrome PID={self._proc.pid} 已终止")
            except subprocess.TimeoutExpired:
                self._proc.kill()
                print(f"  Chrome PID={self._proc.pid} 已强制终止")
            except Exception as e:
                print(f"  Chrome 终止异常: {e}")
            self._proc = None

    async def _check_cdp_alive(self) -> bool:
        """检查 CDP 端口是否响应。"""
        import urllib.request
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{CHROME_PORT}/json/version")
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            return bool(data.get("webSocketDebuggerUrl"))
        except Exception:
            return False

    async def _kill_port_owner(self):
        """仅终止占用 CDP 端口的进程（不伤及用户正在用的 Chrome）。"""
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{CHROME_PORT} | findstr LISTENING',
                capture_output=True, text=True, shell=True,
            )
            pids = set()
            for line in result.stdout.strip().split("\n"):
                parts = line.strip().split()
                if parts and parts[-1].isdigit():
                    pids.add(int(parts[-1]))
            for pid in pids:
                try:
                    proc = subprocess.run(
                        f'wmic process where ProcessId={pid} get Name',
                        capture_output=True, text=True, shell=True,
                    )
                    if "chrome" in proc.stdout.lower():
                        subprocess.run(
                            f"taskkill /PID {pid} /F",
                            capture_output=True, shell=True,
                        )
                        print(f"  终止 CDP 端口占用进程 PID={pid}")
                except Exception:
                    pass
        except Exception:
            pass

    async def scrape(self, checkin=None, checkout=None, hotels=None):
        """采集所有有携程ID的目标酒店"""
        if hotels is None:
            hotels = [h for h in TARGET_HOTELS if h.get("ctrip_id")]

        ci = checkin or (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        co = checkout or (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")

        await self.start(force_restart=True)

        print(f"携程采集 {len(hotels)} 家酒店，日期: {ci}→{co}")

        page = await self.ctx.new_page()
        results = {}
        api_data = {}

        BATCH_SIZE = 4

        for start in range(0, len(hotels), BATCH_SIZE):
            batch = hotels[start:start + BATCH_SIZE]
            print(f"\n批次 {start // BATCH_SIZE + 1}:")

            for i, hotel in enumerate(batch):
                hid = hotel["ctrip_id"]
                hname = hotel["name"]
                cname = hotel.get("ctrip_name", "")

                if i > 0 or start > 0:
                    delay = 10 + random.uniform(0, 6)
                    print(f"  ⏳ {delay:.0f}s")
                    await asyncio.sleep(delay)

                api_data.clear()

                async def on_resp(response):
                    if "getHotelRoomListInland" in response.url:
                        try:
                            api_data[response.url] = await response.text()
                        except:
                            pass

                page.on("response", on_resp)

                try:
                    url = f"https://hotels.ctrip.com/hotels/{hid}.html?checkInDate={ci}&checkOutDate={co}"
                    await page.goto(url, wait_until="commit",
                                    timeout=30000)
                    await asyncio.sleep(10)

                    for _ in range(2):
                        await page.evaluate(
                            f"window.scrollBy(0, {random.randint(300,600)})")
                        await asyncio.sleep(random.uniform(0.5, 1.0))

                    title = await page.title()
                    if "登录" in title and "酒店" not in title:
                        print(f"  ⚠️ {hname}: 重定向登录页")
                        continue

                    if api_data:
                        rooms = extract_prices(list(api_data.values())[0])
                        if rooms:
                            min_price = rooms[0][1]
                            results[hname] = {
                                "price": round(min_price),
                                "ctrip_name": cname or title[:40],
                                "ctrip_id": hid,
                                "rooms": [{"room": r, "price": p}
                                          for r, p in rooms[:5]],
                            }
                            print(f"  🏨 {hname}: ¥{min_price:.0f} "
                                  f"({len(rooms)}种)")
                        else:
                            print(f"  ⚠️ {hname}: API无有效价格")
                    else:
                        print(f"  ⚠️ {hname}: 未捕获API")

                except Exception as e:
                    err = str(e)[:80]
                    print(f"  ❌ {hname}: {err}")

                try:
                    page.remove_listener("response", on_resp)
                except:
                    pass

            # 批次间重启Chrome（彻底关闭旧实例，启动新实例）
            if start + BATCH_SIZE < len(hotels):
                print("  🔄 重启Chrome...")
                await self.stop()          # 断开 Playwright
                await self.shutdown_chrome()  # 终止 Chrome 进程
                await asyncio.sleep(3)
                await self.start()         # 启动新 Chrome
                page = await self.ctx.new_page()

        try:
            await page.close()
        except:
            pass
        await self.stop()  # 最终：仅断开连接，Chrome留给Watchdog管理

        return results


# ── 同步包装器 ──
def scrape_ctrip_sync(checkin=None, checkout=None, timeout=120):
    scraper = CtripScraper()
    return asyncio.run(scraper.scrape(checkin, checkout))


# ── 独立测试 ──
if __name__ == "__main__":
    async def main():
        scraper = CtripScraper()
        results = await scraper.scrape()

        print(f"\n{'='*60}")
        print(f"携程真实价格: {len(results)} 家")
        print(f"{'='*60}")
        for name in sorted(results, key=lambda n: results[n]["price"]):
            info = results[name]
            print(f"  {name:30s} ¥{info['price']:>6}")
            for r in info["rooms"][:3]:
                print(f"    {r['room'][:35]:35s} ¥{r['price']}")

    asyncio.run(main())
