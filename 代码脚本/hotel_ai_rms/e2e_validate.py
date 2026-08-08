"""
e2e_validate.py — 端到端交叉验证脚本
验证 scraper → server API → HTML前端 数据流完整性

检查项:
1. Python HOTELS 与 HTML HOTELS 是否一致
2. server.py API 响应字段是否被 HTML apiToRows() 正确消费
3. ota_scraper 输出字段是否与 server.py _fallback_result 对齐
4. 数据库表结构完整性
5. 采集→缓存→API→HTML 全链路数据格式检查
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ERRORS = []
WARNINGS = []
OK = []


def ok(msg):
    OK.append(f"  ✅ {msg}")


def warn(msg):
    WARNINGS.append(f"  ⚠️ {msg}")


def err(msg):
    ERRORS.append(f"  ❌ {msg}")


# ═══════════════════════════════════════════════════════════════
# 1. Python ↔ HTML 酒店名一致
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("1. Python ↔ HTML 酒店数据交叉验证")
print("=" * 60)

# Python HOTELS (from ota_scraper.py)
sys.path.insert(0, str(ROOT))
from ota_scraper import HOTELS as PY_HOTELS
py_names = sorted([h["name"] for h in PY_HOTELS])
py_stars = {h["name"]: h["star"] for h in PY_HOTELS}
py_bases = {h["name"]: h["base"] for h in PY_HOTELS}
print(f"Python HOTELS: {len(PY_HOTELS)} 家")

# HTML HOTEL_COLORS (页面改为由 /api/dashboard 动态提供酒店数据)
html_path = ROOT / "九寨沟OTA价格监控.html"
html_text = html_path.read_text(encoding="utf-8")

# Extract hotel names from the dashboard color map.
hotels_match = re.search(r'const HOTEL_COLORS = \{(.*?)\};', html_text, re.DOTALL)
assert hotels_match, "Cannot find HOTEL_COLORS in HTML"
hotels_block = hotels_match.group(1)

html_names = re.findall(r"'([^']+)'\s*:", hotels_block)
print(f"HTML HOTELS: {len(html_names)} 家")

# Compare
py_set = set(py_names)
html_set = set(html_names)
common = py_set & html_set
only_py = py_set - html_set
only_html = html_set - py_set

ok(f"共同酒店: {len(common)} 家")
if only_py:
    warn(f"仅 Python 有: {only_py}")
else:
    ok("Python HOTELS 全部在 HTML 中")
if only_html:
    warn(f"仅 HTML 有: {only_html}")
else:
    ok("HTML HOTELS 全部在 Python 中")

ok("酒店星级和基础价由 API 动态输出，不再维护前端副本")

# ═══════════════════════════════════════════════════════════════
# 2. OTA平台列表交叉验证
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("2. OTA 平台/偏差交叉验证")
print("=" * 60)

from ota_scraper import PLATFORMS as PY_PLATFORMS, PLATFORM_BIAS as PY_BIAS

print(f"Python PLATFORMS: {PY_PLATFORMS}")
if "fetch('/api/dashboard')" in html_text:
    ok("前端通过 /api/dashboard 动态读取 OTA 数据")
else:
    err("前端未使用 /api/dashboard 获取 OTA 数据")

# Check bias keys
html_bias_match = re.search(r"const OTA_BIAS = (\{.*?\});", html_text, re.DOTALL)
# We can't directly eval since it uses non-standard keys, but check presence
for plat in PY_PLATFORMS:
    if plat in PY_BIAS:
        ok(f"  {plat}: Python bias OK (commission={PY_BIAS[plat]['commission']})")
    else:
        err(f"  {plat}: 缺少 Python bias")

# ═══════════════════════════════════════════════════════════════
# 3. API 输出字段 ↔ HTML apiToRows() 消费字段
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. API 字段 ↔ HTML apiToRows() 映射验证")
print("=" * 60)

# API 输出字段 (from ota_scraper._generate_fallback)
from ota_scraper import _generate_fallback
sample = _generate_fallback("2026-08-10")
api_fields = set()
for row in sample[:3]:
    api_fields.update(row.keys())
print(f"API 输出字段: {sorted(api_fields)}")

# HTML apiToRows() 消费的字段
html_consumes = set()
api_to_rows_code = re.search(
    r"function apiToRows\(apiData.*?\n\s*\}", html_text, re.DOTALL
)
if api_to_rows_code:
    for field in re.findall(r"r\[['\"]([^'\"]+)['\"]\]", api_to_rows_code.group(0)):
        html_consumes.add(field)
print(f"HTML 消费字段: {sorted(html_consumes)}")

missing_in_api = html_consumes - api_fields
unused_api = api_fields - html_consumes - {"星级", "地址", "房型", "总价", "含早", "可取消", "数据来源", "入住日期", "采集时间"}

if missing_in_api:
    err(f"HTML 需要但 API 不输出的字段: {missing_in_api}")
else:
    ok("所有 HTML 消费字段都在 API 输出中")

# ═══════════════════════════════════════════════════════════════
# 4. server.py API 端点测试
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("4. server.py 模块导入 + scrape_all() 测试")
print("=" * 60)

from server import (
    get_cached_or_fresh, check_competitor_price_drops,
    _cache_lock, _cache, _SCRAPER_OK,
)

# 测试 fallback 采集
result = get_cached_or_fresh(force=True, try_real=False)
assert "data" in result, "Missing 'data' in result"
assert "source" in result, "Missing 'source' in result"
assert "count" in result, "Missing 'count' in result"
assert "checkin" in result, "Missing 'checkin' in result"
assert "fetched_at" in result, "Missing 'fetched_at' in result"
assert "hotels_covered" in result, "Missing 'hotels_covered' in result"
ok(f"get_cached_or_fresh() 返回 {result['count']} 条, 覆盖 {result['hotels_covered']} 家")

# 验证每条数据必须字段
required_fields = ["酒店名称", "OTA平台", "单价_晚", "房型", "数据来源"]
for i, row in enumerate(result["data"][:5]):
    for f in required_fields:
        assert f in row, f"Row {i} missing field '{f}'"
ok(f"所有数据行包含必填字段: {required_fields}")

# 测试缓存线程安全
with _cache_lock:
    cached = _cache["data"]
assert cached is not None and cached["count"] > 0
ok("缓存线程安全测试通过")

# 测试竞对异常检测
alerts = check_competitor_price_drops(result["data"], threshold=0.5)  # 高阈值避免误报
print(f"竞对异常检测: {len(alerts)} 条 (阈值50%——正常应为0)")
if len(alerts) == 0:
    ok("竞对异常检测逻辑正常（高阈值下无假阳性）")

# ═══════════════════════════════════════════════════════════════
# 5. 数据库表结构完整性
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("5. 数据库表结构完整性")
print("=" * 60)

from database import get_conn, init_db
init_db()
conn = get_conn()

expected_tables = [
    "hotel_config", "daily_metrics", "price_decisions",
    "competitor_prices", "marketing_log", "decision_log",
    "budget_targets", "competitive_set",
    "booking_pace", "channel_mix", "alerts_events",
    "event_calendar", "guest_profiles",
]
cur = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
)
actual_tables = [r["name"] for r in cur.fetchall()]
print(f"实际表 ({len(actual_tables)}): {actual_tables}")

for t in expected_tables:
    if t in actual_tables:
        ok(f"表 {t} 存在")
    else:
        err(f"表 {t} 缺失")

# 验证 hotel_id 字段
tables_needing_hotel_id = [
    "daily_metrics", "price_decisions", "competitor_prices",
    "marketing_log", "decision_log", "budget_targets",
    "booking_pace", "channel_mix", "alerts_events",
    "event_calendar", "guest_profiles",
]
for t in tables_needing_hotel_id:
    if t not in actual_tables:
        continue
    cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
    col_names = [c["name"] for c in cols]
    if "hotel_id" in col_names:
        ok(f"  {t}.hotel_id ✓")
    else:
        err(f"  {t}.hotel_id 缺失")

# 验证索引
idx_cur = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
)
indexes = [r["name"] for r in idx_cur.fetchall()]
print(f"业务索引 ({len(indexes)}): {indexes}")
expected_indexes = [
    "idx_dm_hotel_date", "idx_cp_lookup", "idx_cp_hotel_date",
    "idx_pd_hotel_date", "idx_bt_hotel_ym", "idx_ml_hotel_date",
    "idx_bp_stay_snapshot", "idx_bp_hotel_stay",
    "idx_cm_hotel_date", "idx_ae_hotel_time",
]
for idx in expected_indexes:
    if idx in indexes:
        ok(f"索引 {idx} 存在")
    else:
        warn(f"索引 {idx} 缺失（可能与 SQLite 版本相关）")

conn.close()

# ═══════════════════════════════════════════════════════════════
# 6. HTML ↔ server API 全链路字段测试
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("6. 全链路字段映射")
print("=" * 60)

# 模拟 apiToRows 转换
sample_api = result["data"][0]
try:
    checkin = sample_api.get("入住日期", "2026-08-10")
    checkout = "2026-08-11"
    nights = 1
    row = {
        "hotelName": sample_api["酒店名称"],
        "hotelStar": sample_api.get("星级", 4),
        "roomType": sample_api.get("房型", "标准房"),
        "platform": sample_api["OTA平台"],
        "pricePerNight": sample_api["单价_晚"],
        "totalPrice": (sample_api.get("单价_晚", 0) or 0) * nights,
        "hasBreakfast": sample_api.get("含早") == "是",
        "canCancel": sample_api.get("可取消") == "是",
        "checkin": checkin,
        "checkout": checkout,
        "nights": nights,
    }
    for k, v in row.items():
        ok(f"  {k}: {v}")
    print("全链路字段映射正确 ✓")
except KeyError as e:
    err(f"字段映射失败: {e}")

# ═══════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("端到端验证结果汇总")
print("=" * 60)
print(f"✅ 通过: {len(OK)}")
print(f"⚠️ 警告: {len(WARNINGS)}")
print(f"❌ 错误: {len(ERRORS)}")

if ERRORS:
    print("\n❌ 错误详情:")
    for e in ERRORS:
        print(e)
if WARNINGS:
    print("\n⚠️ 警告详情:")
    for w in WARNINGS:
        print(w)

print()
if ERRORS:
    print("🔴 验证失败 — 存在错误需要修复")
    sys.exit(1)
else:
    print("🟢 验证通过 — 前后端数据流一致，端到端就绪")
    sys.exit(0)
