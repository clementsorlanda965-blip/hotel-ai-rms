"""
九寨沟 OTA 全网价格爬虫
════════════════════════════════════════════════════════
使用 Playwright 无头浏览器抓取 OTA 平台酒店价格。
规避 CORS 限制 + JS 渲染页面，输出结构化 JSON/CSV。

启动: python jiuzhaigou_scraper.py
依赖: pip install playwright && playwright install chromium

⚠️ 免责声明：
- OTA平台有反爬机制，抓取可能不完全
- 仅用于酒店从业者竞品价格研究，请遵守 robots.txt
- 设置合理请求间隔，避免对目标服务器造成压力
"""

import asyncio
import json
import csv
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ 请先安装: pip install playwright --break-system-packages && playwright install chromium")
    sys.exit(1)

# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════
CHECKIN_DATE = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
CHECKOUT_DATE = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
CITY = "九寨沟"
OUTPUT_DIR = Path(__file__).parent if "__file__" in dir() else Path(".")
REQUEST_DELAY = (2, 5)  # 随机延迟秒数，避免被ban

# 九寨沟主要酒店
TARGET_HOTELS = [
    "九寨沟悦榕庄",
    "九寨沟希尔顿度假酒店",
    "九寨沟天堂洲际大饭店",
    "九寨沟喜来登国际大酒店",
    "九寨沟天源豪生度假酒店",
    "九寨沟金龙国际度假酒店",
]


class OTAScraper:
    """OTA 价格爬虫 — Playwright 驱动"""

    def __init__(self):
        self.results = []
        self.browser = None
        self.context = None

    async def init_browser(self):
        """启动无头浏览器。价值：模拟真实用户行为，突破JS渲染+反爬。"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
        """)

    async def delay(self):
        """随机延迟，模拟人类浏览行为。"""
        await asyncio.sleep(random.uniform(*REQUEST_DELAY))

    # ═══════════════════════════════════════════════════
    # 携程 (Ctrip) 搜索
    # ═══════════════════════════════════════════════════
    async def scrape_ctrip(self, hotel_name: str) -> list[dict]:
        """
        抓取携程酒店价格。
        URL: https://hotels.ctrip.com/hotel/{city}/{hotel_id}
        注：携程有强反爬（验证码+sign加密），此函数搜索页价格卡片。
        """
        results = []
        try:
            page = await self.context.new_page()
            search_url = (
                f"https://hotels.ctrip.com/hotel/search?"
                f"keyword={hotel_name}&city={CITY}"
                f"&checkin={CHECKIN_DATE}&checkout={CHECKOUT_DATE}"
            )
            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await self.delay()

            # 等待价格卡片加载
            await page.wait_for_timeout(3000)

            # 提取价格（携程用 .price 或 [data-price] 等选择器）
            price_elements = await page.query_selector_all(
                ".real-price, .price-number, .J_price, [class*='price']"
            )
            for elem in price_elements[:5]:
                text = await elem.inner_text()
                price = self._parse_price(text)
                if price and 100 < price < 10000:
                    results.append({
                        "酒店": hotel_name,
                        "平台": "携程",
                        "单价": price,
                        "日期": CHECKIN_DATE,
                        "来源URL": page.url,
                        "爬取时间": datetime.now().isoformat(),
                    })

            await page.close()
        except Exception as e:
            print(f"  ⚠️ 携程抓取异常: {e}")

        return results

    # ═══════════════════════════════════════════════════
    # 美团酒店搜索
    # ═══════════════════════════════════════════════════
    async def scrape_meituan(self, hotel_name: str) -> list[dict]:
        """
        抓取美团酒店价格。
        URL: https://hotel.meituan.com/
        注：美团酒店页面大量JS渲染+反爬，仅尝试首页搜索。
        """
        results = []
        try:
            page = await self.context.new_page()
            url = f"https://hotel.meituan.com/s/{hotel_name}/"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await self.delay()
            await page.wait_for_timeout(3000)

            # 美团价格选择器
            price_elements = await page.query_selector_all(
                "[class*='price'], [class*='Price'], [class*='money']"
            )
            for elem in price_elements[:5]:
                text = await elem.inner_text()
                price = self._parse_price(text)
                if price and 100 < price < 10000:
                    results.append({
                        "酒店": hotel_name,
                        "平台": "美团",
                        "单价": price,
                        "日期": CHECKIN_DATE,
                        "来源URL": page.url,
                        "爬取时间": datetime.now().isoformat(),
                    })

            await page.close()
        except Exception as e:
            print(f"  ⚠️ 美团抓取异常: {e}")

        return results

    # ═══════════════════════════════════════════════════
    # 去哪儿 (Qunar) 搜索 — 相对最易爬的OTA
    # ═══════════════════════════════════════════════════
    async def scrape_qunar(self, hotel_name: str) -> list[dict]:
        """
        抓取去哪儿酒店价格。
        去哪儿网页版反爬相对较弱，JSON API 可能可以直接访问。
        """
        results = []
        try:
            page = await self.context.new_page()

            # 去哪儿酒店搜索
            url = (
                f"https://hotel.qunar.com/city/jiuzhaigou/"
                f"?q={hotel_name}&fromDate={CHECKIN_DATE}&toDate={CHECKOUT_DATE}"
            )
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await self.delay()
            await page.wait_for_timeout(3000)

            price_elements = await page.query_selector_all(
                ".price, .js_price, [data-price], .item_price, [class*='price']"
            )
            for elem in price_elements[:5]:
                text = await elem.inner_text()
                price = self._parse_price(text)
                if price and 100 < price < 10000:
                    results.append({
                        "酒店": hotel_name,
                        "平台": "去哪儿",
                        "单价": price,
                        "日期": CHECKIN_DATE,
                        "来源URL": page.url,
                        "爬取时间": datetime.now().isoformat(),
                    })

            await page.close()
        except Exception as e:
            print(f"  ⚠️ 去哪儿抓取异常: {e}")

        return results

    # ═══════════════════════════════════════════════════
    # 飞猪 (Fliggy) 搜索
    # ═══════════════════════════════════════════════════
    async def scrape_fliggy(self, hotel_name: str) -> list[dict]:
        """
        抓取飞猪酒店价格。
        注：飞猪需要淘宝登录token，未登录只能看到有限价格信息。
        """
        results = []
        try:
            page = await self.context.new_page()
            url = (
                f"https://hotel.fliggy.com/search.htm?"
                f"keywords={hotel_name}&city=510100"  # 成都=510100，九寨沟在附近
                f"&checkIn={CHECKIN_DATE}&checkOut={CHECKOUT_DATE}"
            )
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await self.delay()
            await page.wait_for_timeout(3000)

            price_elements = await page.query_selector_all(
                "[class*='price'], [class*='Price'], .rmb, [class*='num']"
            )
            for elem in price_elements[:5]:
                text = await elem.inner_text()
                price = self._parse_price(text)
                if price and 100 < price < 10000:
                    results.append({
                        "酒店": hotel_name,
                        "平台": "飞猪",
                        "单价": price,
                        "日期": CHECKIN_DATE,
                        "来源URL": page.url,
                        "爬取时间": datetime.now().isoformat(),
                    })

            await page.close()
        except Exception as e:
            print(f"  ⚠️ 飞猪抓取异常: {e}")

        return results

    async def close(self):
        """清理资源。"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        """从文本中提取价格数字。"""
        # 匹配 ¥xxx 或 ￥xxx 格式
        m = re.search(r"[¥￥]?\s*(\d{2,5}(?:\.\d{1,2})?)", text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return None


# ═══════════════════════════════════════════════════════
# 降级方案：当爬虫失败时生成模拟参考数据
# ═══════════════════════════════════════════════════════
def generate_fallback_data(hotels: list[str]) -> list[dict]:
    """
    价值：即使爬虫因反爬失效，仍能输出参考价格区间供收益分析用。
    数据基于九寨沟公开信息 + 行业价格分布经验。
    """
    platforms = ["携程", "美团", "飞猪", "去哪儿", "同程", "艺龙"]
    platform_bias = {
        "携程": 1.00, "美团": 0.97, "飞猪": 0.95,
        "去哪儿": 0.93, "同程": 0.96, "艺龙": 0.98,
    }
    base_prices = {
        "九寨沟悦榕庄": 1680,
        "九寨沟希尔顿度假酒店": 1280,
        "九寨沟天堂洲际大饭店": 1480,
        "九寨沟喜来登国际大酒店": 1080,
        "九寨沟天源豪生度假酒店": 980,
        "九寨沟金龙国际度假酒店": 880,
    }

    results = []
    for hotel in hotels:
        base = base_prices.get(hotel, 600)
        for plat, bias in platform_bias.items():
            noise = 1 + (random.random() - 0.5) * 0.10
            price = round(base * bias * noise / 10) * 10
            results.append({
                "酒店": hotel,
                "平台": plat,
                "单价": price,
                "日期": CHECKIN_DATE,
                "来源": "模拟参考（爬虫降级）",
                "爬取时间": datetime.now().isoformat(),
            })
    return results


# ═══════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════
async def main():
    print("═" * 55)
    print("🏔️  九寨沟 OTA 全网价格爬虫")
    print(f"📅 入住: {CHECKIN_DATE}  离店: {CHECKOUT_DATE}")
    print(f"🎯 目标: {len(TARGET_HOTELS)} 家酒店 × 4 大OTA")
    print("═" * 55)

    scraper = OTAScraper()
    all_results = []
    use_fallback = False

    try:
        await scraper.init_browser()
        print("✅ 浏览器已启动 (无头模式)\n")

        # 逐个酒店、逐个平台抓取
        for idx, hotel in enumerate(TARGET_HOTELS, 1):
            print(f"[{idx}/{len(TARGET_HOTELS)}] 🏨 {hotel}")

            # — 去哪儿（最可能成功）—
            qunar_results = await scraper.scrape_qunar(hotel)
            all_results.extend(qunar_results)
            print(f"    去哪儿: {len(qunar_results)} 条")

            # — 携程 —
            ctrip_results = await scraper.scrape_ctrip(hotel)
            all_results.extend(ctrip_results)
            print(f"    携程:   {len(ctrip_results)} 条")

            # — 美团 —
            mt_results = await scraper.scrape_meituan(hotel)
            all_results.extend(mt_results)
            print(f"    美团:   {len(mt_results)} 条")

            # — 飞猪 —
            fg_results = await scraper.scrape_fliggy(hotel)
            all_results.extend(fg_results)
            print(f"    飞猪:   {len(fg_results)} 条")

            await scraper.delay()
            print()

    except Exception as e:
        print(f"\n❌ 爬虫运行异常: {e}")
        print("⚠️ 将使用降级方案生成模拟参考数据…")
        use_fallback = True

    finally:
        await scraper.close()

    # 降级方案
    if not all_results or use_fallback:
        if not all_results:
            print("\n⚠️ 未抓取到任何真实价格。原因可能是：")
            print("  1. OTA平台需要登录（飞猪/美团）")
            print("  2. 反爬验证码拦截（携程）")
            print("  3. JS渲染未完成（页面加载超时）")
        all_results = generate_fallback_data(TARGET_HOTELS)
        print(f"\n📋 降级方案: 已生成 {len(all_results)} 条模拟参考数据")

    # 去重
    seen = set()
    unique = []
    for r in all_results:
        key = (r["酒店"], r["平台"], r["单价"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"\n📊 最终结果: {len(unique)} 条价格记录\n")

    # ── 输出 JSON ──
    json_path = OUTPUT_DIR / f"jiuzhaigou_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"📄 JSON: {json_path}")

    # ── 输出 CSV ──
    csv_path = OUTPUT_DIR / f"jiuzhaigou_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=unique[0].keys())
        writer.writeheader()
        writer.writerows(unique)
    print(f"📄 CSV:  {csv_path}")

    # ── 汇总打印 ──
    print("\n" + "═" * 55)
    print("📊 价格汇总")
    print("═" * 55)

    # 按酒店汇总
    hotel_summary = {}
    for r in unique:
        h = r["酒店"]
        if h not in hotel_summary:
            hotel_summary[h] = {"min": 99999, "max": 0, "avg": 0, "platforms": {}}
        p = r["单价"]
        hotel_summary[h]["min"] = min(hotel_summary[h]["min"], p)
        hotel_summary[h]["max"] = max(hotel_summary[h]["max"], p)
        hotel_summary[h]["platforms"][r["平台"]] = p
        hotel_summary[h]["avg"] = round(
            sum(hotel_summary[h]["platforms"].values()) /
            len(hotel_summary[h]["platforms"])
        )

    for hotel, info in hotel_summary.items():
        spread = info["max"] - info["min"]
        pct = round(spread / info["avg"] * 100, 1) if info["avg"] > 0 else 0
        print(f"\n🏨 {hotel}")
        print(f"   最低: ¥{info['min']} | 最高: ¥{info['max']} | 均价: ¥{info['avg']}")
        print(f"   价差: ¥{spread} ({pct}%) ← 比价可节省金额")
        for plat, price in sorted(info["platforms"].items(), key=lambda x: x[1]):
            marker = " 👈 最低" if price == info["min"] else ""
            print(f"     {plat}: ¥{price}{marker}")

    print("\n✅ 爬取完成！")


if __name__ == "__main__":
    asyncio.run(main())
