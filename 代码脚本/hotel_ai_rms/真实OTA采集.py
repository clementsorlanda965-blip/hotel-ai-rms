"""
═══════════════════════════════════════════════════════════════
九寨沟 OTA 真实价格采集系统 v3.0
═══════════════════════════════════════════════════════════════
四合一采集方案：
  模式1: Playwright 全自动抓取（Windows，需安装 playwright）
  模式2: 半自动浏览器辅助（打开Chrome，人工解一次验证码，自动提价）
  模式3: OCR 截图识别（手机截图OTA App → OCR提取价格）
  模式4: 快速文本录入（一行一个价格，批量录入）

输出: CSV → 直接导入 Streamlit 驾驶舱
═══════════════════════════════════════════════════════════════

安装依赖（Windows PowerShell 管理员）:
  pip install playwright beautifulsoup4 pillow pytesseract requests --break-system-packages
  playwright install chromium

运行:
  python 真实OTA采集.py
═══════════════════════════════════════════════════════════════
"""

import csv
import json
import os
import re
import sys
import time
import random
import io
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════
OUTPUT_DIR = Path(__file__).parent
OUTPUT_CSV = OUTPUT_DIR / "ota_real_prices.csv"

JIUZHAIGOU_HOTELS = [
    "九寨沟悦榕庄",
    "九寨沟希尔顿度假酒店",
    "九寨沟天堂洲际大饭店",
    "九寨沟喜来登国际大酒店",
    "九寨沟天源豪生度假酒店",
    "九寨沟金龙国际度假酒店",
    "九寨沟亚朵酒店",
    "星程酒店(九寨沟风景区店)",
    "全季酒店(九寨沟景区店)",
    "九寨度假村酒店",
    "汉庭酒店(九寨沟景区店)",
    "如家精选酒店(九寨沟店)",
    "九寨沟眼境民宿",
    "九寨沟云居客栈",
    "九寨沟喇嘛岭寺客栈",
]

TODAY = date.today().strftime("%Y-%m-%d")
CHECKIN = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
CHECKOUT = (date.today() + timedelta(days=4)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════
# 模式1: Qunar HTML 直抓（纯 requests，无需浏览器）
# 原理: 去哪儿PC端部分页面是服务端渲染，HTML中含价格
# ═══════════════════════════════════════════════════════

def scrape_qunar_html(hotel_name: str, checkin: str = None, checkout: str = None) -> list[dict]:
    """
    纯 requests + BeautifulSoup 直抓去哪儿搜索结果。
    去哪儿有反爬但PC搜索结果页部分价格是SSR的。
    返回: [{"酒店名称":..., "房型":..., "OTA平台":"去哪儿", "单价_晚":...}, ...]
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("  ⚠️ 缺少 requests/bs4，跳过 HTML 直抓")
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
        "Connection": "keep-alive",
    }

    ci = checkin or CHECKIN
    co = checkout or CHECKOUT

    try:
        # 去哪儿酒店搜索URL
        url = (
            f"https://hotel.qunar.com/city/jiuzhaigou/"
            f"?q={hotel_name}&fromDate={ci}&toDate={co}"
        )
        session = requests.Session()
        session.headers.update(headers)

        # 先访问首页获取cookie
        session.get("https://hotel.qunar.com/", timeout=10)

        time.sleep(random.uniform(1.5, 3))
        resp = session.get(url, timeout=15)
        resp.encoding = "utf-8"

        if resp.status_code != 200:
            print(f"    去哪儿HTTP {resp.status_code}")
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # 策略1: 找 script 标签中的 JSON 数据（常见于React/Vue SSR）
        for script in soup.find_all("script"):
            text = script.string or ""
            if "price" in text.lower() and len(text) > 100:
                # 尝试提取 price: 数字 模式
                price_matches = re.findall(
                    r'"price"\s*:\s*(\d{2,5}(?:\.\d+)?)', text
                )
                for pm in price_matches[:10]:
                    price = int(float(pm))
                    if 80 < price < 10000:
                        results.append({
                            "酒店名称": hotel_name,
                            "房型": "标准房",
                            "OTA平台": "去哪儿",
                            "单价_晚": price,
                            "总价": price,
                            "含早": "",
                            "可取消": "",
                            "数据来源": "HTML直抓",
                            "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })

        # 策略2: 查找价格元素（class含price的span/div）
        price_selectors = [
            "[class*='price']", "[class*='Price']",
            ".js_price", "[data-price]",
            ".real-price", ".price-num",
        ]
        for selector in price_selectors:
            for elem in soup.select(selector):
                text = elem.get_text(strip=True)
                price = _extract_price(text)
                if price:
                    results.append({
                        "酒店名称": hotel_name,
                        "房型": "标准房",
                        "OTA平台": "去哪儿",
                        "单价_晚": price,
                        "总价": price,
                        "含早": "",
                        "可取消": "",
                        "数据来源": "HTML直抓",
                        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

        # 策略3: 文本正则兜底 —— 找页面中所有看起来像价格的东西
        if not results:
            all_text = soup.get_text()
            prices = re.findall(r"[¥￥]\s*(\d{2,5})", all_text)
            for p in prices[:20]:
                price = int(p)
                if 80 < price < 10000:
                    results.append({
                        "酒店名称": hotel_name,
                        "房型": "标准房",
                        "OTA平台": "去哪儿",
                        "单价_晚": price,
                        "总价": price,
                        "含早": "",
                        "可取消": "",
                        "数据来源": "HTML直抓(文本)",
                        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

    except requests.exceptions.Timeout:
        print(f"    去哪儿请求超时")
    except requests.exceptions.ConnectionError:
        print(f"    去哪儿连接失败（可能被墙/需要代理）")
    except Exception as e:
        print(f"    去哪儿异常: {e}")

    return results


def _extract_price(text: str) -> Optional[int]:
    """从文本提价格数字。"""
    m = re.search(r"[¥￥]?\s*(\d{2,5})", text.replace(",", ""))
    if m:
        p = int(m.group(1))
        if 80 < p < 10000:
            return p
    return None


# ═══════════════════════════════════════════════════════
# 模式2: Playwright 全自动抓取（Windows）
# ═══════════════════════════════════════════════════════

async def scrape_qunar_playwright(hotel_name: str, checkin: str = None, checkout: str = None) -> list[dict]:
    """
    Playwright 无头浏览器抓取去哪儿。
    需要: pip install playwright && playwright install chromium
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("  ❌ Playwright 未安装。请运行: pip install playwright && playwright install chromium")
        return []

    results = []
    ci = checkin or CHECKIN
    co = checkout or CHECKOUT

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            # 注入反检测
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                window.chrome = { runtime: {} };
            """)

            page = await context.new_page()
            url = (
                f"https://hotel.qunar.com/city/jiuzhaigou/"
                f"?q={hotel_name}&fromDate={ci}&toDate={co}"
            )

            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)  # 等JS渲染

            # 提取价格 —— 多种选择器策略
            selectors = [
                ".price", ".js_price", "[data-price]",
                "[class*='price']", "[class*='Price']",
                ".item_price", ".real-price",
                "span:has-text('¥')",
                "[class*='total']",
            ]

            for sel in selectors:
                elements = await page.query_selector_all(sel)
                for elem in elements[:10]:
                    try:
                        text = await elem.inner_text()
                        price = _extract_price(text)
                        if price:
                            results.append({
                                "酒店名称": hotel_name,
                                "房型": "标准房",
                                "OTA平台": "去哪儿",
                                "单价_晚": price,
                                "总价": price,
                                "含早": "",
                                "可取消": "",
                                "数据来源": "Playwright自动",
                                "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            })
                    except:
                        continue

            # 也尝试提取页面全文中的价格
            if not results:
                full_text = await page.inner_text("body")
                prices = re.findall(r"[¥￥]\s*(\d{2,5})", full_text)
                for p in prices[:30]:
                    price = int(p)
                    if 80 < price < 10000:
                        results.append({
                            "酒店名称": hotel_name,
                            "房型": "标准房",
                            "OTA平台": "去哪儿",
                            "单价_晚": price,
                            "总价": price,
                            "含早": "",
                            "可取消": "",
                            "数据来源": "Playwright全文",
                            "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })

            await browser.close()

    except Exception as e:
        print(f"  ❌ Playwright 异常: {e}")

    return results


# ═══════════════════════════════════════════════════════
# 模式3: OCR 截图识别
# ═══════════════════════════════════════════════════════

def ocr_screenshots(image_paths: list[str], hotel_name: str = "") -> list[dict]:
    """
    OCR识别OTA App截图中的价格。
    依赖: pip install pytesseract pillow + 安装 tesseract-ocr
    """
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        print("  ❌ 缺少 pytesseract 或 Pillow")
        return []

    results = []
    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"  ⚠️ 图片不存在: {img_path}")
            continue
        try:
            img = Image.open(img_path)
            # 预处理：转灰度 + 增强对比度
            img = img.convert("L")
            # OCR
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")

            # 提取价格
            prices = re.findall(r"[¥￥]\s*(\d{2,5})", text)
            room_types = re.findall(r"(大床房|双床房|套房|标准间|亲子房|行政房|豪华房|别墅)", text)

            for price_str in prices[:10]:
                price = int(price_str)
                if 80 < price < 10000:
                    room = room_types[0] if room_types else "标准房"
                    results.append({
                        "酒店名称": hotel_name or "(从截图识别)",
                        "房型": room,
                        "OTA平台": "(截图识别)",
                        "单价_晚": price,
                        "总价": price,
                        "含早": "",
                        "可取消": "",
                        "数据来源": "OCR截图",
                        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
        except Exception as e:
            print(f"  ❌ OCR失败 {img_path}: {e}")

    return results


# ═══════════════════════════════════════════════════════
# 模式4: 快速文本录入
# ═══════════════════════════════════════════════════════

def parse_quick_input(text: str, hotel_name: str = "") -> list[dict]:
    """
    快速录入格式:
      每行一个价格，格式: 酒店名 房型 OTA平台 价格
      或简单格式: 价格（自动填充酒店名）
      例: 悦榕庄 大床房 携程 1890
          希尔顿 双床房 美团 1360

    也支持从Excel/记事本粘贴的表格文本:
      携程	1890	含早
      美团	1790	不含早
    """
    results = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 尝试匹配 "酒店 房型 平台 价格" 格式
        parts = line.split()
        if len(parts) >= 2:
            price = None
            for part in parts:
                p = re.search(r"(\d{2,5})", part)
                if p:
                    price = int(p.group(1))
                    break

            if price and 50 < price < 20000:
                hotel = parts[0] if len(parts) >= 1 else hotel_name
                room = parts[1] if len(parts) >= 2 else "标准房"
                plat = parts[2] if len(parts) >= 3 else "携程"
                results.append({
                    "酒店名称": hotel,
                    "房型": room,
                    "OTA平台": plat,
                    "单价_晚": price,
                    "总价": price,
                    "含早": "",
                    "可取消": "",
                    "数据来源": "手动录入",
                    "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

    return results


# ═══════════════════════════════════════════════════════
# 主采集流程
# ═══════════════════════════════════════════════════════

def collect_all(mode: str = "auto") -> list[dict]:
    """
    mode:
      "auto"   — 先HTML直抓，失败则兜底到模拟
      "browser"— 用 Playwright（Windows）
      "all"    — 所有模式全跑，合并去重
    """
    all_results = []

    if mode in ("auto", "all"):
        print("═" * 55)
        print("🔍 模式1: Qunar HTML 直抓（纯 requests，无需浏览器）")
        print("═" * 55)
        for i, hotel in enumerate(JIUZHAIGOU_HOTELS, 1):
            print(f"  [{i}/{len(JIUZHAIGOU_HOTELS)}] {hotel}...")
            results = scrape_qunar_html(hotel, CHECKIN, CHECKOUT)
            if results:
                # 去重：只保留每个酒店最合理的价格区间
                prices = [r["单价_晚"] for r in results]
                if prices:
                    median_price = sorted(prices)[len(prices)//2]
                    # 过滤掉明显的噪音价格（距中位数超3倍的）
                    filtered = [r for r in results if abs(r["单价_晚"] - median_price) < median_price * 2]
                    if filtered:
                        results = filtered
                print(f"    ✅ 抓到 {len(results)} 条")
                all_results.extend(results)
            else:
                print(f"    ⚠️ 未抓到")
            time.sleep(random.uniform(1, 2.5))

    if mode in ("browser", "all"):
        print("\n" + "═" * 55)
        print("🔍 模式2: Playwright 浏览器抓取")
        print("═" * 55)
        try:
            import asyncio
        except ImportError:
            print("  ❌ asyncio 不可用")
            return all_results

        async def run_playwright():
            pw_results = []
            for i, hotel in enumerate(JIUZHAIGOU_HOTELS[:5], 1):  # 先抓5家测试
                print(f"  [{i}/5] {hotel}...")
                results = await scrape_qunar_playwright(hotel, CHECKIN, CHECKOUT)
                if results:
                    print(f"    ✅ 抓到 {len(results)} 条")
                    pw_results.extend(results)
                else:
                    print(f"    ⚠️ 未抓到")
                await asyncio.sleep(random.uniform(2, 5))
            return pw_results

        try:
            pw = asyncio.run(run_playwright())
            all_results.extend(pw)
        except Exception as e:
            print(f"  ❌ Playwright 运行失败: {e}")
            print("  💡 请确保已安装: pip install playwright && playwright install chromium")

    return all_results


def save_results(results: list[dict], output_path: Path = None):
    """保存结果到CSV，同时输出JSON备份。"""
    path = output_path or OUTPUT_CSV

    if not results:
        print("\n⚠️ 无数据可保存")
        return None

    # 按酒店+房型+平台去重
    seen = set()
    unique = []
    for r in results:
        key = f"{r.get('酒店名称','')}|{r.get('房型','')}|{r.get('OTA平台','')}|{r.get('单价_晚',0)}"
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # CSV
    fieldnames = ["酒店名称","房型","OTA平台","单价_晚","总价","含早","可取消","数据来源","采集时间"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique)

    # JSON 备份
    json_path = path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"\n📄 CSV: {path} ({len(unique)} 条)")
    print(f"📄 JSON: {json_path} ({len(unique)} 条)")

    # 统计
    hotels = set(r["酒店名称"] for r in unique)
    sources = set(r["数据来源"] for r in unique)
    prices = [r["单价_晚"] for r in unique if r.get("单价_晚")]
    if prices:
        print(f"🏨 覆盖酒店: {len(hotels)} 家")
        print(f"📡 数据来源: {', '.join(sources)}")
        print(f"💰 价格区间: ¥{min(prices)} - ¥{max(prices)}")

    return path


# ═══════════════════════════════════════════════════════
# 交互式菜单
# ═══════════════════════════════════════════════════════

def interactive_menu():
    """交互式采集菜单。"""
    print("\n" + "═" * 55)
    print("🏔️  九寨沟 OTA 真实价格采集系统 v3.0")
    print("═" * 55)
    print(f"📅 采集日期: {CHECKIN} → {CHECKOUT}")
    print(f"🎯 目标酒店: {len(JIUZHAIGOU_HOTELS)} 家")
    print()
    print("请选择采集模式:")
    print("  1. 🔍 HTML直抓（纯requests，无需浏览器，快速尝试）")
    print("  2. 🌐 Playwright全自动（需Windows + playwright已安装）")
    print("  3. 📸 OCR截图识别（提供截图文件夹路径）")
    print("  4. ✏️  快速文本录入（粘贴价格文本）")
    print("  5. 🚀 全自动（HTML + Playwright 全跑）")
    print("  q. 退出")
    print()

    choice = input("> ").strip()

    if choice == "1":
        results = collect_all(mode="auto")
        save_results(results)

    elif choice == "2":
        results = collect_all(mode="browser")
        save_results(results)

    elif choice == "3":
        folder = input("📁 截图文件夹路径: ").strip()
        hotel = input("🏨 酒店名（可选，留空自动识别）: ").strip()
        if os.path.isdir(folder):
            images = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
            ]
            results = ocr_screenshots(images, hotel)
            save_results(results)
        elif os.path.isfile(folder):
            results = ocr_screenshots([folder], hotel)
            save_results(results)
        else:
            print("❌ 路径不存在")

    elif choice == "4":
        print("📝 粘贴价格文本（每行一个，格式：酒店名 房型 OTA 价格）：")
        print("   输入空行结束:")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        hotel = input("🏨 默认酒店名（可选）: ").strip()
        results = parse_quick_input("\n".join(lines), hotel)
        save_results(results)

    elif choice == "5":
        results = collect_all(mode="all")
        save_results(results)

    elif choice.lower() == "q":
        print("👋 退出")
    else:
        print("❌ 无效选择")


# ═══════════════════════════════════════════════════════
# CLI 入口（支持命令行参数，供 Streamlit 调用）
# ═══════════════════════════════════════════════════════

def cli_auto_collect():
    """命令行自动采集——供 Streamlit 按钮调用。"""
    print(f"🚀 开始自动采集九寨沟OTA价格...")
    results = collect_all(mode="auto")

    # 如果HTML直抓没结果，生成一份模拟数据兜底（标记清楚）
    if not results:
        print("\n⚠️ HTML直抓未获取到数据。生成模拟参考价兜底（会在CSV中标记'模拟参考'）...")
        results = _generate_fallback()

    path = save_results(results)
    if path:
        print(f"\n✅ 采集完成！数据已保存至: {path}")
        print(f"📥 可在 Streamlit 驾驶舱 → OTA监控 → 导入此CSV文件")
    return path


def _generate_fallback() -> list[dict]:
    """兜底方案：基于网络公开信息校准的模拟价格。"""
    base_prices = {
        "九寨沟悦榕庄": 1600,
        "九寨沟希尔顿度假酒店": 1100,
        "九寨沟天堂洲际大饭店": 1350,
        "九寨沟喜来登国际大酒店": 950,
        "九寨沟天源豪生度假酒店": 850,
        "九寨沟金龙国际度假酒店": 750,
        "九寨沟亚朵酒店": 500,
        "星程酒店(九寨沟风景区店)": 430,
        "全季酒店(九寨沟景区店)": 380,
        "九寨度假村酒店": 550,
        "汉庭酒店(九寨沟景区店)": 240,
        "如家精选酒店(九寨沟店)": 220,
        "九寨沟眼境民宿": 170,
        "九寨沟云居客栈": 200,
        "九寨沟喇嘛岭寺客栈": 150,
    }
    platforms = ["携程","美团","飞猪","去哪儿","同程","艺龙"]
    bias = {"携程":1.0,"美团":0.97,"飞猪":0.95,"去哪儿":0.93,"同程":0.96,"艺龙":0.98}

    m = date.today().month
    season = 1.6 if m in (4,5,9,10) else (1.35 if m in (7,8) else (0.7 if m in (1,2,12) else 0.9))

    results = []
    for hotel, base in base_prices.items():
        for plat, b in bias.items():
            noise = 1 + (random.random() - 0.5) * 0.08
            price = round(base * season * b * noise / 10) * 10
            results.append({
                "酒店名称": hotel,
                "房型": "大床房",
                "OTA平台": plat,
                "单价_晚": max(80, price),
                "总价": max(80, price),
                "含早": "",
                "可取消": "",
                "数据来源": "模拟参考(兜底)",
                "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="九寨沟OTA真实价格采集")
    parser.add_argument("--auto", action="store_true", help="自动模式（HTML直抓，供Streamlit调用）")
    parser.add_argument("--output", type=str, default=None, help="输出CSV路径")
    args = parser.parse_args()

    if args.auto:
        # 非交互模式：自动采集 → 输出CSV → 退出
        cli_auto_collect()
    else:
        # 交互模式
        interactive_menu()
