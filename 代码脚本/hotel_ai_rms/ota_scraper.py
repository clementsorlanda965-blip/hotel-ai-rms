"""
ota_scraper.py — 九寨沟OTA价格采集模块 v4.0
可被 server.py 导入，也可独立运行。

采集策略（三级降级）:
  1. requests + BS4 直抓 Qunar SSR 页面（快，但可能被反爬）
  2. Playwright 无头浏览器（慢但可靠）
  3. 校准模拟数据兜底（标记 "模拟参考"）

用法:
  from ota_scraper import scrape_all, HOTELS
  results = scrape_all(mode="auto")
"""

import csv
import json
import os
import re
import sys
import time
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
OUTPUT_CSV = ROOT / "ota_real_prices.csv"
OUTPUT_JSON = ROOT / "ota_real_prices.json"

HOTELS = [
    {"name": "九寨沟悦榕庄", "star": 5, "base": 1600},
    {"name": "九寨沟希尔顿度假酒店", "star": 5, "base": 1100},
    {"name": "九寨沟天堂洲际大饭店", "star": 5, "base": 1350},
    {"name": "九寨沟喜来登国际大酒店", "star": 5, "base": 950},
    {"name": "九寨沟天源豪生度假酒店", "star": 5, "base": 850},
    {"name": "九寨沟金龙国际度假酒店", "star": 5, "base": 750},
    {"name": "九寨沟亚朵酒店", "star": 4, "base": 500},
    {"name": "星程酒店(九寨沟风景区店)", "star": 4, "base": 430},
    {"name": "全季酒店(九寨沟景区店)", "star": 4, "base": 380},
    {"name": "九寨度假村酒店", "star": 4, "base": 550},
    {"name": "汉庭酒店(九寨沟景区店)", "star": 3, "base": 240},
    {"name": "如家精选酒店(九寨沟店)", "star": 3, "base": 220},
    {"name": "九寨沟眼境民宿", "star": 3, "base": 170},
    {"name": "九寨沟云居客栈", "star": 3, "base": 200},
    {"name": "九寨沟喇嘛岭寺客栈", "star": 3, "base": 150},
]

PLATFORMS = ["携程", "美团", "飞猪", "去哪儿", "同程", "艺龙"]

PLATFORM_BIAS = {
    "携程": {"commission": 0.15, "bias": 1.00},
    "美团": {"commission": 0.12, "bias": 0.97},
    "飞猪": {"commission": 0.10, "bias": 0.95},
    "去哪儿": {"commission": 0.13, "bias": 0.93},
    "同程": {"commission": 0.11, "bias": 0.96},
    "艺龙": {"commission": 0.14, "bias": 0.98},
}

ROOM_TYPES = ["大床房", "双床房", "标准间", "套房", "亲子房", "行政房"]

SEASON_FACTORS = {
    1: 0.65, 2: 0.70, 3: 0.80, 4: 1.30, 5: 1.40,
    6: 1.10, 7: 1.35, 8: 1.35, 9: 1.30, 10: 1.50, 11: 0.90, 12: 0.75,
}

TODAY = date.today()
DEFAULT_CHECKIN = (TODAY + timedelta(days=3)).strftime("%Y-%m-%d")
DEFAULT_CHECKOUT = (TODAY + timedelta(days=4)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _extract_price(text: str) -> Optional[int]:
    """从文本提取价格数字 (80-10000区间)。"""
    for p in re.findall(r"[¥￥]\s*(\d{2,5})", str(text).replace(",", "")):
        price = int(p)
        if 80 < price < 10000:
            return price
    return None


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _season_multiplier(checkin_date: str = None) -> float:
    """根据入住日期计算季节系数。"""
    if checkin_date:
        try:
            m = datetime.strptime(checkin_date, "%Y-%m-%d").month
        except ValueError:
            m = TODAY.month
    else:
        m = TODAY.month
    base = SEASON_FACTORS.get(m, 1.0)
    # 周末加成
    try:
        d = datetime.strptime(checkin_date, "%Y-%m-%d") if checkin_date else TODAY
        if d.weekday() >= 5:
            base *= 1.12
    except ValueError:
        pass
    return base


# ═══════════════════════════════════════════════════════════════
# 策略1: requests + BS4 直抓 Qunar
# ═══════════════════════════════════════════════════════════════

def _scrape_qunar_requests(hotel_name: str, checkin: str, checkout: str) -> list[dict]:
    """纯 requests 抓取去哪儿搜索结果页。"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    results = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }

    try:
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://hotel.qunar.com/", timeout=10)
        time.sleep(random.uniform(1, 2))

        url = (
            f"https://hotel.qunar.com/city/jiuzhaigou/"
            f"?q={hotel_name}&fromDate={checkin}&toDate={checkout}"
        )
        resp = session.get(url, timeout=15)
        resp.encoding = "utf-8"

        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # 策略A: script标签中的JSON数据
        for script in soup.find_all("script"):
            text = script.string or ""
            if "price" in text.lower() and len(text) > 100:
                for pm in re.findall(r'"price"\s*:\s*(\d{2,5}(?:\.\d+)?)', text):
                    price = int(float(pm))
                    if 80 < price < 10000:
                        results.append({
                            "酒店名称": hotel_name, "房型": "标准房",
                            "OTA平台": "去哪儿", "单价_晚": price,
                            "数据来源": "Qunar直抓", "采集时间": _now(),
                        })

        # 策略B: 价格CSS选择器
        for sel in ["[class*='price']", "[class*='Price']", ".js_price", "[data-price]"]:
            for elem in soup.select(sel):
                price = _extract_price(elem.get_text(strip=True))
                if price:
                    results.append({
                        "酒店名称": hotel_name, "房型": "标准房",
                        "OTA平台": "去哪儿", "单价_晚": price,
                        "数据来源": "Qunar直抓", "采集时间": _now(),
                    })

        # 策略C: 全文正则兜底
        if not results:
            for p in re.findall(r"[¥￥]\s*(\d{2,5})", soup.get_text()):
                price = int(p)
                if 80 < price < 10000:
                    results.append({
                        "酒店名称": hotel_name, "房型": "标准房",
                        "OTA平台": "去哪儿", "单价_晚": price,
                        "数据来源": "Qunar文本", "采集时间": _now(),
                    })

    except requests.exceptions.Timeout:
        pass
    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        pass

    return results


# ═══════════════════════════════════════════════════════════════
# 策略2: Playwright 无头浏览器
# ═══════════════════════════════════════════════════════════════

async def _scrape_playwright(hotel_name: str, checkin: str, checkout: str) -> list[dict]:
    """Playwright 无头浏览器抓取。"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    results = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled",
                      "--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            await ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                window.chrome = { runtime: {} };
            """)

            page = await ctx.new_page()
            url = (
                f"https://hotel.qunar.com/city/jiuzhaigou/"
                f"?q={hotel_name}&fromDate={checkin}&toDate={checkout}"
            )
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

            for sel in [".price", "[class*='price']", "span:has-text('¥')"]:
                for elem in await page.query_selector_all(sel):
                    try:
                        price = _extract_price(await elem.inner_text())
                        if price:
                            results.append({
                                "酒店名称": hotel_name, "房型": "标准房",
                                "OTA平台": "去哪儿", "单价_晚": price,
                                "数据来源": "Playwright", "采集时间": _now(),
                            })
                    except Exception:
                        continue

            if not results:
                full = await page.inner_text("body")
                for p in re.findall(r"[¥￥]\s*(\d{2,5})", full)[:30]:
                    price = int(p)
                    if 80 < price < 10000:
                        results.append({
                            "酒店名称": hotel_name, "房型": "标准房",
                            "OTA平台": "去哪儿", "单价_晚": price,
                            "数据来源": "Playwright全文", "采集时间": _now(),
                        })

            await browser.close()
    except Exception:
        pass

    return results


# ═══════════════════════════════════════════════════════════════
# 策略3: 校准模拟数据兜底
# ═══════════════════════════════════════════════════════════════

def _generate_fallback(checkin: str = None) -> list[dict]:
    """基于公开信息校准的模拟价格，含季节系数和平台偏差。"""
    season = _season_multiplier(checkin)
    results = []

    for hotel in HOTELS:
        for plat in PLATFORMS:
            bias = PLATFORM_BIAS[plat]["bias"]
            noise = 1 + (random.random() - 0.5) * 0.08
            price = max(80, round(hotel["base"] * season * bias * noise / 10) * 10)

            room = "大床房"
            results.append({
                "酒店名称": hotel["name"],
                "星级": hotel["star"],
                "房型": room,
                "OTA平台": plat,
                "单价_晚": int(price),
                "总价": int(price),
                "含早": "是" if hotel["star"] >= 4 and random.random() > 0.3 else "否",
                "可取消": "是" if price > 500 and random.random() > 0.3 else "否",
                "数据来源": "模拟参考",
                "采集时间": _now(),
                "入住日期": checkin or DEFAULT_CHECKIN,
            })

    return results


# ═══════════════════════════════════════════════════════════════
# 主采集函数
# ═══════════════════════════════════════════════════════════════

def scrape_html_mode(hotels: list[str] = None, checkin: str = None, checkout: str = None) -> list[dict]:
    """策略1: requests 直抓所有酒店（同步，快）。"""
    ci = checkin or DEFAULT_CHECKIN
    co = checkout or DEFAULT_CHECKOUT
    names = hotels or [h["name"] for h in HOTELS]
    all_results = []

    for name in names:
        results = _scrape_qunar_requests(name, ci, co)
        if results:
            prices = [r["单价_晚"] for r in results]
            median = sorted(prices)[len(prices) // 2]
            # 过滤噪音
            filtered = [r for r in results if abs(r["单价_晚"] - median) < median * 2]
            all_results.extend(filtered or results[:3])
        time.sleep(random.uniform(0.8, 1.5))

    return _dedupe(all_results)


def scrape_playwright_mode(hotels: list[str] = None, checkin: str = None, checkout: str = None) -> list[dict]:
    """策略2: Playwright 异步抓取。"""
    try:
        import asyncio
    except ImportError:
        return []

    ci = checkin or DEFAULT_CHECKIN
    co = checkout or DEFAULT_CHECKOUT
    names = hotels or [h["name"] for h in HOTELS][:8]

    async def _run():
        results = []
        for name in names:
            r = await _scrape_playwright(name, ci, co)
            results.extend(r)
            await asyncio.sleep(random.uniform(1.5, 3))
        return results

    try:
        return _dedupe(asyncio.run(_run()))
    except Exception:
        return []


def scrape_all(mode: str = "auto", checkin: str = None, checkout: str = None, timeout: float = 15.0) -> dict:
    """统一采集入口，返回 {"data": [...], "source": "...", "count": N, "checkin": "..."}

    mode:
      "auto"  — 先 HTML直抓，无结果则 Playwright，再无则模拟兜底
      "html"  — 仅 requests 直抓
      "pw"    — 仅 Playwright
      "fallback" — 仅模拟兜底
    """
    ci = checkin or DEFAULT_CHECKIN
    co = checkout or DEFAULT_CHECKOUT
    data = []
    source = "模拟参考"

    if mode in ("auto", "html"):
        import threading

        result_container = []

        def _run_html():
            try:
                result_container.append(scrape_html_mode(checkin=ci, checkout=co))
            except Exception:
                pass

        t = threading.Thread(target=_run_html, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            data = []
        elif result_container and result_container[0]:
            data = result_container[0]
            source = "Qunar直抓"

    if (mode in ("auto", "pw")) and not data:
        import threading

        result_container = []

        def _run_pw():
            try:
                result_container.append(scrape_playwright_mode(checkin=ci, checkout=co))
            except Exception:
                pass

        t = threading.Thread(target=_run_pw, daemon=True)
        t.start()
        t.join(timeout=max(timeout, 30))

        if not t.is_alive() and result_container and result_container[0]:
            data = result_container[0]
            source = "Playwright采集"

    if not data:
        data = _generate_fallback(ci)
        source = "模拟参考"

    return {
        "data": data,
        "source": source,
        "count": len(data),
        "checkin": ci,
        "checkout": co,
        "fetched_at": _now(),
        "hotels_covered": len(set(r["酒店名称"] for r in data)),
    }


def _dedupe(results: list[dict]) -> list[dict]:
    """按 酒店+房型+平台+价格 去重。"""
    seen = set()
    unique = []
    for r in results:
        key = f"{r.get('酒店名称','')}|{r.get('房型','')}|{r.get('OTA平台','')}|{r.get('单价_晚',0)}"
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# ═══════════════════════════════════════════════════════════════
# 持久化
# ═══════════════════════════════════════════════════════════════

def save_results(data: list[dict], csv_path: Path = None, json_path: Path = None):
    """保存到CSV + JSON。"""
    csv_p = csv_path or OUTPUT_CSV
    json_p = json_path or OUTPUT_JSON

    fieldnames = ["酒店名称", "星级", "房型", "OTA平台", "单价_晚", "总价",
                  "含早", "可取消", "数据来源", "采集时间", "入住日期"]
    with open(csv_p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(data)

    with open(json_p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return csv_p, json_p


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="九寨沟OTA价格采集 v4.0")
    p.add_argument("--mode", default="auto", choices=["auto", "html", "pw", "fallback"])
    p.add_argument("--checkin", default=DEFAULT_CHECKIN)
    p.add_argument("--checkout", default=DEFAULT_CHECKOUT)
    p.add_argument("--output", default=None)
    args = p.parse_args()

    print(f"🔍 采集模式: {args.mode} | {args.checkin} → {args.checkout}")
    result = scrape_all(mode=args.mode, checkin=args.checkin, checkout=args.checkout)
    print(f"📡 数据来源: {result['source']}")
    print(f"📊 采集到 {result['count']} 条，覆盖 {result['hotels_covered']} 家酒店")

    csv_p, json_p = save_results(result["data"])
    print(f"📄 CSV: {csv_p}")
    print(f"📄 JSON: {json_p}")

    if result["source"] == "模拟参考":
        print("⚠️ 未获取到真实价格，使用校准模拟数据。")
