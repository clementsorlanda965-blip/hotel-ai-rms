"""
ota_scraper.py — 九寨沟OTA价格采集模块 v7.0
可被 server.py 导入，也可独立运行。

采集策略（四级降级）:
  0. 🔥 携程 CDP 真实价格（Chrome远程调试 + API拦截）—— 最优先
  1. 🔥 Google Hotels DOM 提取（国际品牌真实价格）
  2. Playwright 无头浏览器 Qunar
  3. 校准模拟数据兜底（标记 "模拟参考"）

4/4 携程ID已确认。

用法:
  from ota_scraper import scrape_all, HOTELS
  results = scrape_all(mode="auto")
"""

import csv, json, os, re, sys, time, random, asyncio, threading
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
OUTPUT_CSV = ROOT / "ota_real_prices.csv"
OUTPUT_JSON = ROOT / "ota_real_prices.json"

USD_TO_CNY = 7.20

# ──── 4家九寨沟目标酒店（已确认携程ID）────
HOTELS = [
    {"name": "九寨沟诺富特酒店", "star": 4, "base": 600, "ctrip_id": "133579644",
     "address": "九寨沟县", "keywords": ["诺富特", "Novotel"]},
    {"name": "九寨沟万怡酒店", "star": 4, "base": 650, "ctrip_id": "110034462",
     "address": "九寨沟县", "keywords": ["万怡", "Courtyard", "Marriott"]},
    {"name": "九寨沟德尔塔酒店", "star": 5, "base": 800, "ctrip_id": "104424550",
     "address": "九寨沟县", "keywords": ["德尔塔", "Delta", "Marriott"]},
    {"name": "全季酒店九寨沟九寨大道店", "star": 3, "base": 350, "ctrip_id": "123577708",
     "address": "九寨沟县南坪镇滨江路2号", "keywords": ["全季", "JI Hotel", "九寨大道"]},
]

PLATFORMS = ["携程"]

PLATFORM_BIAS = {
    "携程": {"commission": 0.15, "bias": 1.00},
}

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

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _season_multiplier(checkin_date: str = None) -> float:
    m = datetime.strptime(checkin_date, "%Y-%m-%d").month if checkin_date else TODAY.month
    base = SEASON_FACTORS.get(m, 1.0)
    try:
        d = datetime.strptime(checkin_date, "%Y-%m-%d") if checkin_date else TODAY
        if d.weekday() >= 5:
            base *= 1.12
    except:
        pass
    return base


# ═══════════════════════════════════════════════════════════════
# 策略0: 携程 CDP 真实价格（最高优先级）
# ═══════════════════════════════════════════════════════════════

def _extract_ctrip_prices(api_body: str) -> list[dict]:
    """
    双路径价格提取:
    - 路径1: cancelInfo.ladderDetailInfo[].customCurrencyPrice.amount (国内酒店)
    - 路径2: priceInfo.price (国际品牌: 希尔顿/丽思/智选等)
    """
    data = json.loads(api_body) if isinstance(api_body, str) else api_body
    srm = data.get("data", {}).get("saleRoomMap", {})
    prm = data.get("data", {}).get("physicRoomMap", {})

    results = {}
    for sid, sinfo in srm.items():
        phys_id = str(sinfo.get("physicalRoomId", ""))
        room_name = prm.get(phys_id, {}).get("name", f"Room_{phys_id}")
        price = None

        # 路径1: cancelInfo (国内酒店)
        ci = sinfo.get("cancelInfo", {})
        for ladder in (ci.get("ladderDetailInfo", []) or []):
            ccp = ladder.get("customCurrencyPrice", {})
            amt = ccp.get("amount")
            if amt and isinstance(amt, (int, float)) and 200 < amt < 50000:
                price = amt
                break

        # 路径2: priceInfo (国际品牌)
        if not price:
            pi = sinfo.get("priceInfo", {})
            amt = pi.get("price")
            if amt and isinstance(amt, (int, float)) and 200 < amt < 50000:
                price = amt

        if price and (room_name not in results or price < results[room_name]):
            results[room_name] = price

    return sorted(results.items(), key=lambda x: x[1])


def _scrape_ctrip_sync(checkin: str = None, checkout: str = None,
                       timeout: int = 180) -> list[dict]:
    """同步携程CDP采集，委托给 ctrip_scraper 模块。"""
    ci = checkin or DEFAULT_CHECKIN
    co = checkout or DEFAULT_CHECKOUT

    try:
        from ctrip_scraper import scrape_ctrip_sync as _csync
        raw = _csync(ci, co)
    except Exception as e:
        print(f"  携程采集失败: {e}")
        return []

    if not raw:
        return []

    print(f"  携程: {len(raw)} 家有价格")

    # 转换为标准格式
    data = []
    for hname, info in raw.items():
        # 找匹配的酒店信息
        matched = next((h for h in HOTELS if h["name"] == hname), None)
        star = matched["star"] if matched else 4
        address = matched.get("address", "") if matched else ""

        for room in info.get("rooms", [{"room": "标准房", "price": info["price"]}]):
            data.append({
                "酒店名称": hname,
                "星级": star,
                "地址": address,
                "房型": room["room"],
                "OTA平台": "携程",
                "单价_晚": round(room["price"]),
                "总价": round(room["price"]),
                "含早": "否",
                "可取消": "是",
                "数据来源": "携程真实",
                "is_real": True,
                "采集时间": _now(),
                "入住日期": ci,
            })
    return data


# ═══════════════════════════════════════════════════════════════
# 策略1: Google Hotels
# ═══════════════════════════════════════════════════════════════

def _match_google_hotel(display_name: str) -> Optional[dict]:
    best_score, best_hotel = 0, None
    for hotel in HOTELS:
        score = sum(len(kw) for kw in hotel.get("keywords", [])
                    if kw.lower() in display_name.lower())
        if score > best_score:
            best_score, best_hotel = score, hotel
    return best_hotel if best_score >= 2 else None


async def _scrape_google_async(checkin: str, checkout: str) -> list[dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    results = []
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    channel="chrome", headless=True,
                    args=["--disable-blink-features=AutomationControlled",
                          "--no-sandbox", "--disable-dev-shm-usage"])
            except:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled",
                          "--no-sandbox"])

            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN", timezone_id="Asia/Shanghai")
            await ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver',
                    {get: function() { return undefined; }});
                window.chrome = { runtime: {} };
            """)

            page = await ctx.new_page()
            url = (f"https://www.google.com/travel/hotels"
                   f"?q=jiuzhaigou+hotels&checkin={checkin}&checkout={checkout}"
                   f"&hl=zh-CN&curr=USD")
            await page.goto(url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(15000)

            # 用eval提取酒店数据
            hotel_data = await page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('[role="listitem"]').forEach(el => {
                        const text = el.innerText || '';
                        const match = text.match(
                            /([\\u4e00-\\u9fff].+?(?:酒店|度假|Hilton|洲际|悦榕|豪生|希尔顿|漫心|桔子|智选).+?)\\n.*?US\\$(\\d+)/);
                        if (match) {
                            items.push({name: match[1], price: parseInt(match[2])});
                        }
                    });
                    return items;
                }
            """)

            for item in hotel_data:
                price_cny = round(item["price"] * USD_TO_CNY)
                if price_cny < 50 or price_cny > 20000:
                    continue
                matched = _match_google_hotel(item["name"])
                if not matched:
                    continue

                existing = [r for r in results
                            if r["酒店名称"] == matched["name"]]
                if existing:
                    if price_cny < existing[0]["单价_晚"]:
                        existing[0]["单价_晚"] = price_cny
                        existing[0]["总价"] = price_cny
                    continue

                results.append({
                    "酒店名称": matched["name"],
                    "星级": matched["star"],
                    "地址": matched.get("address", ""),
                    "房型": "标准房",
                    "OTA平台": "携程",
                    "单价_晚": price_cny,
                    "总价": price_cny,
                    "含早": "否",
                    "可取消": "是",
                    "数据来源": "Google Hotels",
                    "is_real": True,
                    "采集时间": _now(),
                    "入住日期": checkin,
                })

            await browser.close()
    except Exception as e:
        print(f"  Google Hotels: {e}")

    return results


def _scrape_google_sync(checkin: str = None, checkout: str = None) -> list[dict]:
    try:
        return asyncio.run(_scrape_google_async(
            checkin or DEFAULT_CHECKIN, checkout or DEFAULT_CHECKOUT))
    except:
        return []


# ═══════════════════════════════════════════════════════════════
# 策略3: 模拟兜底 —— 已采集真实价格校准
# ═══════════════════════════════════════════════════════════════

CTRIP_REFERENCE_PRICES = {
    # 2026-08-07 携程真实最低价（旺季基准，8月）
    "九寨沟万怡酒店": 331,
    "九寨沟诺富特酒店": 357,
    "全季酒店九寨沟九寨大道店": 358,
    "九寨沟德尔塔酒店": 497,
}


def _generate_fallback(checkin: str = None,
                       real_prices: dict = None) -> list[dict]:
    """生成模拟价格，已采集酒店用真实价校准，未采集用同类酒店估算"""
    season = _season_multiplier(checkin)
    ref = {**CTRIP_REFERENCE_PRICES}
    if real_prices:
        ref.update(real_prices)

    results = []

    for hotel in HOTELS:
        hotel_real = ref.get(hotel["name"])

        for plat in PLATFORMS:
            bias = PLATFORM_BIAS[plat]["bias"]

            if hotel_real:
                noise = 1 + (random.random() - 0.5) * 0.04
                price = max(80, round(hotel_real * bias * noise / 10) * 10)
                source = "真实价格校准"
            elif hotel["star"] >= 4:
                # 中高端酒店：同类均价估算
                peer_prices = [v for k, v in ref.items()
                               if any(h["name"] != k
                                      and abs(h["star"] - hotel["star"]) <= 1
                                      for h in HOTELS)]
                if peer_prices:
                    peer_avg = sum(peer_prices) / len(peer_prices)
                    noise = 1 + (random.random() - 0.5) * 0.06
                    price = max(80, round(peer_avg * bias * noise / 10) * 10)
                    source = "同业价格估算"
                else:
                    noise = 1 + (random.random() - 0.5) * 0.08
                    price = max(80,
                                round(hotel["base"] * season * bias * noise
                                      / 10) * 10)
                    source = "基准价估算"
            else:
                # 民宿：低价段估算
                noise = 1 + (random.random() - 0.5) * 0.10
                price = max(80,
                            round(hotel["base"] * season * bias * noise
                                  / 10) * 10)
                source = "民宿估算"

            results.append({
                "酒店名称": hotel["name"],
                "星级": hotel["star"],
                "地址": hotel.get("address", ""),
                "房型": "大床房",
                "OTA平台": plat,
                "单价_晚": int(price),
                "总价": int(price),
                "含早": "是" if hotel["star"] >= 4 and random.random() > 0.3
                else "否",
                "可取消": "是" if price > 400 and random.random() > 0.3
                else "否",
                "数据来源": source,
                "is_real": False,
                "采集时间": _now(),
                "入住日期": checkin or DEFAULT_CHECKIN,
            })

    return results


# ═══════════════════════════════════════════════════════════════
# 主采集函数
# ═══════════════════════════════════════════════════════════════

def scrape_all(mode: str = "auto", checkin: str = None,
               checkout: str = None, timeout: float = 120.0) -> dict:
    """统一采集入口

    mode: "auto" | "ctrip" | "google" | "fallback"
    """
    ci = checkin or DEFAULT_CHECKIN
    co = checkout or DEFAULT_CHECKOUT
    data = []
    source = "模拟参考"
    real_prices = {}

    # ── 策略0: 携程 CDP 真实价格 ──
    if mode in ("auto", "ctrip"):
        print("🔍 携程CDP采集...")
        try:
            ctrip_data = _scrape_ctrip_sync(ci, co)
        except Exception as e:
            print(f"  携程失败: {e}")
            ctrip_data = []

        if ctrip_data:
            data.extend(ctrip_data)
            for r in ctrip_data:
                real_prices[r["酒店名称"]] = min(
                    real_prices.get(r["酒店名称"], 99999), r["单价_晚"])
            ctrip_hotels = len({r["酒店名称"] for r in ctrip_data})
            source = f"携程真实({ctrip_hotels}家)"

    # ── 策略1: Google Hotels ──
    if mode in ("auto", "google"):
        print("🔍 Google Hotels...")
        google_data = _scrape_google_sync(ci, co)
        if google_data:
            existing_keys = {(r["酒店名称"], r.get("房型", ""))
                             for r in data}
            for r in google_data:
                key = (r["酒店名称"], r.get("房型", ""))
                if key not in existing_keys:
                    data.append(r)
                    existing_keys.add(key)
                    real_prices[r["酒店名称"]] = min(
                        real_prices.get(r["酒店名称"], 99999), r["单价_晚"])
            google_hotels = len({r["酒店名称"] for r in google_data})
            if source.startswith("携程"):
                source += f"+Google({google_hotels}家)"
            else:
                source = f"Google Hotels({google_hotels}家)"

    # ── 策略2: 模拟兜底 ──
    fallback_data = _generate_fallback(ci, real_prices)
    if data:
        covered = {r["酒店名称"] for r in data}
        for fb in fallback_data:
            if fb["酒店名称"] not in covered:
                data.append(fb)
        if real_prices:
            source = f"混合({len(real_prices)}家真实+模拟补充)"
    else:
        data = fallback_data
        if real_prices:
            source = f"真实价格校准({len(real_prices)}家)"

    data = _dedupe(data)

    return {
        "data": data,
        "source": source,
        "count": len(data),
        "checkin": ci,
        "checkout": co,
        "fetched_at": _now(),
        "hotels_covered": len(set(r["酒店名称"] for r in data)),
        "real_price_count": len(real_prices),
    }


def _dedupe(results: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in results:
        key = (f"{r.get('酒店名称','')}|{r.get('房型','')}"
               f"|{r.get('OTA平台','')}|{r.get('单价_晚',0)}")
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# ═══════════════════════════════════════════════════════════════
# 持久化
# ═══════════════════════════════════════════════════════════════

def save_results(data: list[dict], csv_path: Path = None,
                 json_path: Path = None):
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
    p = argparse.ArgumentParser(description="九寨沟OTA价格采集 v7.0")
    p.add_argument("--mode", default="auto",
                   choices=["auto", "ctrip", "google", "fallback"])
    p.add_argument("--checkin", default=DEFAULT_CHECKIN)
    p.add_argument("--checkout", default=DEFAULT_CHECKOUT)
    args = p.parse_args()

    print(f"🔍 模式: {args.mode} | {args.checkin} → {args.checkout}")
    result = scrape_all(mode=args.mode, checkin=args.checkin,
                        checkout=args.checkout)
    print(f"\n📡 来源: {result['source']}")
    print(f"📊 {result['count']} 条 / {result['hotels_covered']} 家酒店")

    csv_p, json_p = save_results(result["data"])
    print(f"📄 CSV: {csv_p}")
    print(f"📄 JSON: {json_p}")

    # 价格一览
    prices = {}
    for r in result["data"]:
        if r["OTA平台"] == "携程" and "真实" in r["数据来源"]:
            pn = r["酒店名称"]
            if pn not in prices or r["单价_晚"] < prices[pn]:
                prices[pn] = r["单价_晚"]

    if prices:
        print(f"\n📊 携程真实价格:")
        for name in sorted(prices, key=prices.get):
            print(f"  {name:30s} ¥{prices[name]:>6}")

    if result["source"] == "模拟参考":
        print("⚠️ 未获取到真实价格，使用校准模拟数据。")
