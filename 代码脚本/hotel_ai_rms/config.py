"""
config.py — Hotel AI-RMS 集中配置管理
替代散落在各模块的硬编码常量，统一入口。
"""

import os
from datetime import date, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# 路径
# ═══════════════════════════════════════════════════════════════

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "rms.db"
OUTPUT_DIR = Path(r"E:\工作AI\酒店管理\数据分析")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# 酒店主数据
# ═══════════════════════════════════════════════════════════════

SELF_HOTEL_ID = 1
SELF_HOTEL_NAME = "九寨沟诺富特酒店"
FLOOR_PRICE = 399         # 集团底价硬约束（Accor Group）
TOTAL_ROOMS = 170         # 诺富特实际可卖房数
STAR_LEVEL = 4

# 竞对酒店（携程CDP采集目标 + 竞争指数计算基准）
COMPETITORS = [
    {"name": "九寨沟诺富特酒店", "star": 4, "base": 600, "ctrip_id": "133579644",
     "property_type": "self", "total_rooms": 170,
     "address": "九寨沟县", "keywords": ["诺富特", "Novotel"]},
    {"name": "九寨沟万怡酒店", "star": 4, "base": 650, "ctrip_id": "110034462",
     "property_type": "competitor", "total_rooms": 150,
     "address": "九寨沟县", "keywords": ["万怡", "Courtyard", "Marriott"]},
    {"name": "九寨沟德尔塔酒店", "star": 5, "base": 800, "ctrip_id": "104424550",
     "property_type": "competitor", "total_rooms": 200,
     "address": "九寨沟县", "keywords": ["德尔塔", "Delta", "Marriott"]},
    {"name": "全季酒店九寨沟九寨大道店", "star": 3, "base": 350, "ctrip_id": "123577708",
     "property_type": "competitor", "total_rooms": 100,
     "address": "九寨沟县南坪镇滨江路2号", "keywords": ["全季", "JI Hotel", "九寨大道"]},
]

# 仅竞对（不含自家）
COMPETITOR_HOTELS = [h for h in COMPETITORS if h["property_type"] != "self"]

# 携程参考价格（2026-08-07 真实价格校准）
CTRIP_REFERENCE_PRICES = {
    "九寨沟诺富特酒店": 357,
    "九寨沟万怡酒店": 331,
    "九寨沟德尔塔酒店": 497,
    "全季酒店九寨沟九寨大道店": 358,
}

# ═══════════════════════════════════════════════════════════════
# OTA 平台配置
# ═══════════════════════════════════════════════════════════════

PLATFORMS = ["携程"]
PLATFORM_BIAS = {
    "携程": {"commission": 0.15, "bias": 1.00},
}

# ═══════════════════════════════════════════════════════════════
# 季节系数（基于诺富特历史 ADR 回归校准）
# ═══════════════════════════════════════════════════════════════

SEASON_FACTORS = {
    1: 0.65, 2: 0.70, 3: 0.80, 4: 1.30, 5: 1.40,
    6: 1.10, 7: 1.35, 8: 1.35, 9: 1.30, 10: 1.50,
    11: 0.90, 12: 0.75,
}

# 周末系数
WEEKEND_PREMIUM = 0.08       # 周五/六加价 8%
SUNDAY_DISCOUNT = -0.05      # 周日降价 5%

# ═══════════════════════════════════════════════════════════════
# 采集配置
# ═══════════════════════════════════════════════════════════════

TODAY = date.today()
DEFAULT_CHECKIN = (TODAY + timedelta(days=3)).strftime("%Y-%m-%d")
DEFAULT_CHECKOUT = (TODAY + timedelta(days=4)).strftime("%Y-%m-%d")

SCRAPE_SCHEDULE_HOURS = [9, 15, 21]   # 每日采集时间点
SCRAPE_TIMEOUT = 50.0                  # 采集超时（秒）
CACHE_TTL = 300                        # 缓存有效期（秒）

# ═══════════════════════════════════════════════════════════════
# 告警阈值
# ═══════════════════════════════════════════════════════════════

PRICE_DROP_THRESHOLD = 0.15       # 竞对降幅 ≥15% 触发告警
PRICE_INVERSION_THRESHOLD = 0.05  # 渠道价格倒挂 ≥5% 触发告警
OCC_ANOMALY_THRESHOLD = 0.20      # 出租率偏离 ≥20% 触发告警
GOP_DROP_THRESHOLD = 0.10         # GOP率下降 ≥10% 触发告警

# ═══════════════════════════════════════════════════════════════
# 价格校验 — 历史价格区间（动态更新）
# ═══════════════════════════════════════════════════════════════

PRICE_BANDS = {
    "九寨沟诺富特酒店": (300, 1200),
    "九寨沟万怡酒店": (280, 1500),
    "九寨沟德尔塔酒店": (350, 2500),
    "全季酒店九寨沟九寨大道店": (180, 800),
}

# ═══════════════════════════════════════════════════════════════
# 飞书配置
# ═══════════════════════════════════════════════════════════════

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_RMS_ALERT_WEBHOOK", "")
FEISHU_USER_ID = os.environ.get("FEISHU_RMS_USER_ID", "")

# ═══════════════════════════════════════════════════════════════
# KPI 基准（诺富特 2025 实际 + 2026 预算）
# ═══════════════════════════════════════════════════════════════

KPI_BASELINES = {
    "OCC":       {"优秀": 80, "达标": 65, "需改善": 50},
    "RevPAR":    {"优秀": 500, "达标": 350, "需改善": 200},
    "GOP率":     {"优秀": 40, "达标": 32, "需改善": 20},
    "人房比":     {"优秀": 0.35, "达标": 0.30, "需改善": 0.25},  # 41人/120房≈0.34
}

# 诺富特财务参数（2025 审计值）
NOVOTEL_FINANCIALS = {
    "breakeven_occ_operating": 0.313,   # 运营保本 OCC
    "breakeven_occ_full": 0.672,        # 全成本保本 OCC
    "target_gop_rate": 0.38,            # GOP率目标
    "avg_variable_cost_per_room": 45,    # 单房变动成本（¥）
    "avg_fb_revenue_per_guest": 120,    # 人均餐饮消费（¥）
    "total_staff": 41,                  # 员工总数
    "monthly_fixed_cost": 380000,       # 月固定成本（¥）
}

# ═══════════════════════════════════════════════════════════════
# 定价授权等级
# ═══════════════════════════════════════════════════════════════

AUTH_LEVELS = {
    "L1_auto":     0.05,   # ±5% 以内 → 自动执行
    "L2_confirm":   0.15,   # 5-15% → 收益经理确认
    "L3_decide":    0.30,   # >15% → GM 拍板
}
