"""
segment_engine.py — 客源细分核心逻辑层（纯 pandas/sqlite，无 UI 依赖）
════════════════════════════════════════════════════════════════
客源细分 = 收益管理"知客"第一步：
  客源类型 → 渠道 → 入住时长 → 价值分级(A/B/C) → 销售打法 → GEO 结构化数据

供调用方：
  - app.py                渲染「🎯 客源结构」Tab
  - segment_scheduler.py  每日飞书早报
  - tests/test_core.py    单元测试
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent

# ═══════════════════════════════════════════════════════════════
# 客源类型定义（一级→二级分层）
# ═══════════════════════════════════════════════════════════════

# 客源类型元数据：level1 一级分类 / 默认LOS / 默认佣金率
SEGMENT_TYPES = {
    "品牌散客": {"level1": "散客", "channel": "直销", "default_los": 1.9, "commission": 0.00},
    "企业商务客": {"level1": "散客", "channel": "协议", "default_los": 2.6, "commission": 0.00},
    "OTA线上客": {"level1": "散客", "channel": "OTA", "default_los": 1.7, "commission": 0.12},
    "旅行社团": {"level1": "团队", "channel": "团队", "default_los": 2.2, "commission": 0.15},
    "长住客": {"level1": "其他", "channel": "长住", "default_los": 7.5, "commission": 0.00},
    "上门客": {"level1": "其他", "channel": "上门", "default_los": 1.4, "commission": 0.00},
}

# 渠道 → 客源类型
CHANNEL_SEGMENT_MAP = {
    "携程": "OTA线上客", "美团": "OTA线上客", "飞猪": "OTA线上客",
    "Booking.com": "OTA线上客", "抖音团购": "OTA线上客",
    "官方小程序": "品牌散客", "官网": "品牌散客", "公众号": "品牌散客",
    "企业协议": "企业商务客", "协议公司": "企业商务客",
    "旅行社": "旅行社团", "旅行团": "旅行社团",
    "前台散客": "上门客", "上门散客": "上门客",
    "长住": "长住客", "长包房": "长住客",
}

# 渠道佣金率（倒扣佣金，无佣金渠道为 0）
CHANNEL_COMMISSION = {
    "携程": 0.12, "美团": 0.10, "飞猪": 0.10,
    "Booking.com": 0.18, "抖音团购": 0.05,
    "官方小程序": 0.00, "官网": 0.00, "公众号": 0.00,
    "企业协议": 0.00, "旅行社": 0.15, "旅行团": 0.15,
    "前台散客": 0.00, "长住": 0.00,
}

# 健康度诊断规则（默认采用九寨沟度假型酒店经验阈值；可覆写）
DEFAULT_HEALTH_RULES = [
    {"key": "ota_share", "label": "OTA渠道占比", "target_max": 0.55,
     "message": "OTA 是流量入口但佣金高，占比>55%渠道被绑定、利润被摊薄"},
    {"key": "direct_share", "label": "直销占比", "target_min": 0.30,
     "message": "直销(官网/小程序/会员)利润最高，占比应逐步提高到30%以上"},
    {"key": "team_share", "label": "团队占比", "target_max": 0.35,
     "message": "旅行团/团队占比>35%将拉低 ADR，旺季应限制低价团"},
    {"key": "corp_share", "label": "协议公司占比", "target_max": 0.25,
     "message": "协议公司占比>25%议价权偏弱，需提升直销比例"},
    {"key": "leisure_share", "label": "休闲散客占比", "target_min": 0.15,
     "message": "休闲散客<15% 过度依赖单一大客户，客源结构失衡"},
]

GEO_SCHEMA_KEYS = [
    "name", "type", "rating", "address", "city", "district",
    "star_level", "total_rooms", "price_range", "room_types",
    "facilities", "nearby", "checkin_out", "ota", "scenes",
]


# ═══════════════════════════════════════════════════════════════
# 一、客户明细 → 细分字段（兼容 app.py generate_customer_data 列名）
# ═══════════════════════════════════════════════════════════════

def generate_sample_customers(n: int = 220, seed: int = 42) -> pd.DataFrame:
    """生成一份模拟客源客户明细（供调度器/测试/独立演示使用，不依赖 Streamlit）。

    列名与 app.py generate_customer_data 对齐：客户ID/姓名/会员等级/
    总消费金额/预订渠道/平均间隔天数/流失风险/价格敏感/高价值/偏好房型。
    """
    rng = np.random.default_rng(seed)
    surnames = ["王","李","张","刘","陈","杨","黄","赵","周","吴",
                "徐","孙","马","朱","胡","郭","何","林","罗","高"]
    givens = ["伟","强","磊","军","勇","涛","明","辉","鹏","浩",
              "芳","敏","静","丽","婷","雪","琳","玲","颖","娜"]
    channels = ["携程","美团","飞猪","官方小程序","抖音团购","Booking.com",
                "前台散客","企业协议","旅行社","长住"]
    cw = np.array([0.25, 0.15, 0.10, 0.12, 0.05, 0.03, 0.05, 0.12, 0.10, 0.03])
    tiers = ["普通","银卡","金卡","钻石"]
    tw = np.array([0.55, 0.27, 0.13, 0.05])

    rows = []
    for i in range(1, n + 1):
        name = rng.choice(surnames) + rng.choice(givens)
        tier = rng.choice(tiers, p=tw)
        channel = rng.choice(channels, p=cw)
        spend_range = {"钻石": (50000, 200000), "金卡": (20000, 80000),
                       "银卡": (8000, 30000), "普通": (500, 12000)}[tier]
        total_spend = round(rng.uniform(*spend_range), 2)
        avg_int = int(rng.normal(68, 25))
        avg_int = max(15, min(200, avg_int))
        rows.append({
            "客户ID": f"CUST{i:04d}", "姓名": name, "会员等级": tier,
            "总消费金额": total_spend, "预订渠道": channel,
            "平均间隔天数": avg_int, "偏好房型": "标准大床房",
        })
    df = pd.DataFrame(rows)
    return build_customers_df(df)


def build_customers_df(df: pd.DataFrame) -> pd.DataFrame:
    """为现有客户 DataFrame 补客源类型 / 平均入住时长 / 佣金率 / 综合贡献。

    输入需含列：预订渠道、总消费金额、会员等级、客户ID、名称。
    输入无客源相关数据时自动兜底（按渠道映射，缺失渠道按 品牌散客）。
    """
    out = df.copy()
    n = len(out)
    if n == 0:
        for c in ("segment_type", "avg_stay_length", "commission_rate", "综合贡献"):
            out[c] = pd.Series(dtype="float64" if c != "segment_type" else "object")
        return out

    # 1) 客源类型：按预订渠道映射；缺失渠道 → 按会员等级兜底
    if "预订渠道" in out.columns:
        seg_by_ch = out["预订渠道"].fillna("").map(lambda c: CHANNEL_SEGMENT_MAP.get(c))
    else:
        seg_by_ch = pd.Series([None] * n, index=out.index)
    if "会员等级" in out.columns:
        is_high_tier = out["会员等级"].isin(["钻石", "金卡"])
        fallback = np.where(is_high_tier, "品牌散客", "OTA线上客")
    else:
        fallback = ["OTA线上客"] * n
    out["segment_type"] = seg_by_ch.fillna(pd.Series(fallback, index=out.index))

    # 2) 平均入住时长（未显式提供时按客源类型默认 + 轻微振荡）
    if "avg_stay_length" in out.columns and out["avg_stay_length"].fillna(0).gt(0).any():
        pass
    else:
        rng = np.random.default_rng(42)
        base = out["segment_type"].map(lambda s: SEGMENT_TYPES.get(s, {}).get("default_los", 2.0))
        out["avg_stay_length"] = np.clip(base + rng.normal(0, 0.6, n), 1.0, 15.0).round(1)
        los_mask = out["segment_type"].eq("长住客")
        if los_mask.any():
            out.loc[los_mask, "avg_stay_length"] = np.clip(
                rng.normal(7.5, 1.5, los_mask.sum()), 3.0, 15.0
            ).round(1)

    # 3) 佣金率 + 综合贡献（≈ 房费 + 附加消费 - 获客/佣金成本）
    out["commission_rate"] = out["segment_type"].map(
        lambda s: SEGMENT_TYPES.get(s, {}).get("commission", 0.0)
    )
    spend = out["总消费金额"].astype(float) if "总消费金额" in out.columns else pd.Series(
        np.zeros(n), index=out.index
    )
    extra_rate = np.where(out["segment_type"].eq("长住客"), 0.05, 0.02)
    commission_cost = out["commission_rate"] * spend
    out["综合贡献"] = (spend + spend * extra_rate - commission_cost).round(2)
    return out


def segment_mix_from_customers(df: pd.DataFrame,
                               snapshot_date: Optional[str] = None) -> pd.DataFrame:
    """由客户明细聚合为客源细分汇总（segment_type × 渠道维度）。"""
    if df is None or df.empty:
        return pd.DataFrame()

    snap = snapshot_date or date.today().isoformat()
    rows = []
    for (seg, ch), grp in df.groupby(["segment_type", "预订渠道"], dropna=False):
        rows.append({
            "date": snap,
            "segment_type": seg,
            "channel": ch or "未绑定",
            "customer_count": len(grp),
            "room_nights": round(grp["avg_stay_length"].sum(), 1),
            "revenue": round(grp["总消费金额"].sum(), 2),
            "commission": round(grp["commission_rate"].mul(grp["总消费金额"]).sum(), 2),
            "avg_stay_length": round(grp["avg_stay_length"].mean(), 2),
            "source": "simulated",
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════
# 二、CSV 导入（真实数据 —— 列名容错映射）
# ═══════════════════════════════════════════════════════════════

CSV_COLUMN_ALIASES = {
    "客户ID": ["客户ID", "客户编号", "guest_id", "id"],
    "姓名": ["姓名", "客人姓名", "guest_name"],
    "会员等级": ["会员等级", "会员级别", "tier"],
    "总消费金额": ["总消费金额", "消费金额", "total_spend", "sum"],
    "预订渠道": ["预订渠道", "渠道", "channel"],
    "入住时长": ["入住时长", "平均入住时长", "停留", "los", "avg_stay_length"],
}


def normalize_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把用户上传 CSV 的列名映射为内部标准列名（容错）。"""
    out = df.copy()
    rename_map = {}
    for std, aliases in CSV_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in out.columns:
                rename_map[alias] = std
                break
    out.rename(columns=rename_map, inplace=True)
    return out


def parse_segment_csv(df: pd.DataFrame) -> pd.DataFrame:
    """解析并规范化导入的客源 CSV → 标准客户明细（经 build_customers_df）。"""
    df = normalize_csv_columns(df)
    if df.empty:
        raise ValueError("导入文件为空")

    if "总消费金额" not in df.columns:
        raise ValueError("缺少必要列：[总消费金额]，请参考 CSV 模板")

    df = df.copy()
    df["会员等级"] = df["会员等级"] if "会员等级" in df.columns else "普通"
    df["预订渠道"] = df["预订渠道"] if "预订渠道" in df.columns else "前台散客"
    df["入住时长"] = pd.to_numeric(df["入住时长"], errors="coerce").fillna(2.0) \
        if "入住时长" in df.columns else 2.0
    df["总消费金额"] = pd.to_numeric(df["总消费金额"], errors="coerce").fillna(0)
    if "客户ID" not in df.columns:
        df["客户ID"] = ["CUST%04d" % (i + 1) for i in range(len(df))]

    df["avg_stay_length"] = df["入住时长"].astype(float)
    return build_customers_df(df)


# ═══════════════════════════════════════════════════════════════
# 三、健康度诊断（渠道结构健康卡）
# ═══════════════════════════════════════════════════════════════

def _segment_revenue_share(mix: pd.DataFrame) -> dict:
    """按客源类型汇总收入占收供健康计算。返回 {segment_key_lower: 占比}。"""
    seg_rev = mix.groupby("segment_type").agg(revenue=("revenue", "sum")).reset_index()
    total = seg_rev["revenue"].sum()
    if total <= 0:
        return {}
    return {r["segment_type"]: r["revenue"] / total for _, r in seg_rev.iterrows()}


def diagnose_health(mix: pd.DataFrame,
                    rules: Optional[list] = None) -> list[dict]:
    """基于细分汇总计算健康诊断卡。

    规则里的 key 会在下列指标中匹配：
      ota_share       = OTA线上客占比
      direct_share    = 品牌散客 + 长住客（直销渠道）
      team_share      = 旅行社团
      corp_share      = 企业商务客
      leisure_share   = 品牌散客 + 上门客 + OTA线上客（个人休闲客源）
    """
    if mix is None or mix.empty:
        return []

    share = _segment_revenue_share(mix)
    def sum_share(*keys):
        return sum(share.get(k, 0.0) for k in keys)

    metrics = {
        "ota_share": sum_share("OTA线上客"),
        "direct_share": sum_share("品牌散客", "长住客"),
        "team_share": sum_share("旅行社团"),
        "corp_share": sum_share("企业商务客"),
        "leisure_share": sum_share("品牌散客", "上门客", "OTA线上客"),
    }

    result = []
    for rule in rules or DEFAULT_HEALTH_RULES:
        actual = metrics.get(rule["key"], 0.0)
        status = "OK"
        if "target_max" in rule and actual > rule["target_max"]:
            status = "WARN"
        elif "target_min" in rule and actual < rule["target_min"]:
            status = "WARN"
        target = (f"≤{rule['target_max']*100:.0f}%"
                  if "target_max" in rule else f"≥{rule['target_min']*100:.0f}%")
        result.append({
            "key": rule["key"],
            "label": rule["label"],
            "actual": round(actual * 100),
            "target": target,
            "status": status,
            "message": rule.get("message", ""),
        })
    return result


# ═══════════════════════════════════════════════════════════════
# 四、价值排序（A/B/C）与销售打法
# ═══════════════════════════════════════════════════════════════

def rank_segments(mix: pd.DataFrame) -> pd.DataFrame:
    """按综合贡献（收入-佣金）对客源类型做 A/B/C 分级。

    累计贡献占比：≤60%→A，≤85%→B，其余→C。
    """
    if mix is None or mix.empty:
        return pd.DataFrame()

    by_seg = mix.groupby("segment_type").agg(
        revenue=("revenue", "sum"),
        commission=("commission", "sum"),
        customer_count=("customer_count", "sum"),
        avg_los=("avg_stay_length", "mean"),
    ).reset_index()
    by_seg["净贡献"] = (by_seg["revenue"] - by_seg["commission"]).round(2)
    total = by_seg["净贡献"].sum()
    by_seg["贡献占比"] = (by_seg["净贡献"] / total * 100).round(1) if total else 0.0
    by_seg.sort_values("净贡献", ascending=False, inplace=True)

    cum = by_seg["贡献占比"].cumsum()
    tier = []
    for c in cum:
        tier.append("A" if c <= 60 else ("B" if c <= 85 else "C"))
    by_seg["价值等级"] = tier
    return by_seg.reset_index(drop=True)


TACTICS_MAP = {
    "A": {"策略": "保量保价", "动作": "优先分配库存+稳价，投放主力营销资源",
          "责任人": "市场销售总监", "时限": "每周复盘"},
    "B": {"策略": "适度增长", "动作": "动态调节价格，客群精准触达",
          "责任人": "OTA运营/PMS收益", "时限": "按日调节"},
    "C": {"策略": "严控限额", "动作": "限量限时/限渠道，控低价团与尾部需求",
          "责任人": "收益经理", "时限": "淡旺切换"},
}


def build_tactics_table(ranked: pd.DataFrame) -> pd.DataFrame:
    """价值分级 → 打法/责任人表格。"""
    if ranked is None or ranked.empty:
        return pd.DataFrame()
    out = ranked.copy()
    out["策略"] = out["价值等级"].map(lambda t: TACTICS_MAP[t]["策略"])
    out["打法"] = out["价值等级"].map(lambda t: TACTICS_MAP[t]["动作"])
    out["责任人"] = out["价值等级"].map(lambda t: TACTICS_MAP[t]["责任人"])
    out["节奏"] = out["价值等级"].map(lambda t: TACTICS_MAP[t]["时限"])
    return out[["segment_type", "revenue", "commission", "净贡献",
                "贡献占比", "avg_los", "价值等级", "策略", "打法", "责任人", "节奏"]]


# ═══════════════════════════════════════════════════════════════
# 五、GEO 结构化数据块 + 策略清单
# ═══════════════════════════════════════════════════════════════

def build_geo_block(hotel: dict) -> dict:
    """输出酒店 GEO 结构化数据块（AI 可抽取语义单元）。

    hotel 字段：name/address/city/district/star_level/total_rooms/
    price_range/room_types/facilities/nearby/tags/scenes/checkin_out/
    ota/booking/description
    缺省字段自动兜底。
    """
    h = hotel or {}
    block = {
        "name": h.get("name", "九寨沟度假酒店"),
        "type": "Hotel",
        "rating": h.get("rating", 4.5),
        "address": h.get("address", ""),
        "city": h.get("city", "九寨沟"),
        "district": h.get("district", ""),
        "star_level": h.get("star_level", 4),
        "total_rooms": h.get("total_rooms", 120),
        "price_range": h.get("price_range", "¥400-¥900"),
        "room_types": h.get("room_types", []),
        "facilities": h.get("facilities", []),
        "nearby": h.get("nearby", []),
        "tags": h.get("tags", []),
        "checkin_out": h.get("checkin_out", "14:00-12:00"),
        "booking": h.get("booking", {"官网/小程序": ""}),
        "ota": h.get("ota", ["携程", "美团", "飞猪", "抖音"]),
        "scenes": h.get("scenes", ["亲子", "度假", "商务"]),
    }
    return block


def query_for_segment(segment: str) -> str:
    """为每个客源类型预置 AI 提问词模板。"""
    qs = {
        "品牌散客": "「九寨沟环境好、服务周到、性价比高、会员订房有优惠的酒店」",
        "企业商务客": "「九寨沟适合出差/开会的星级酒店，含延迟退房」",
        "OTA线上客": "「九寨沟携程高分酒店」及「亲子/度假型酒店对比」",
        "旅行社团": "「九寨沟可对接旅行团的酒店报价与房态」",
        "长住客": "「九寨沟适合长住/淡季包月的酒店」",
        "上门客": "「九寨沟现房/即时可订房间」",
    }
    return qs.get(segment, "「九寨沟{}」酒店推荐".format(segment))


def geo_strategy_blocks(block: dict, segments: list[dict]) -> str:
    """生成 AI 可复用语义块 + 客源指令库（Markdown 文本）。"""
    lines = ["## 三、AI 可抽取语义块（直接复用）\n"]
    lines.append("```json")
    lines.append(json.dumps(block, ensure_ascii=False, indent=2))
    lines.append("```\n")
    lines.append("## 四、客源类型 × AI 提问词库\n")
    if segments:
        for s in segments:
            lines.append(f"- **{s['segment']}**（营收占比 {s['pct']:.1f}%）：")
            lines.append(f"  → {query_for_segment(s['segment'])}")
        lines.append("")
    else:
        lines.append("- 导入真实数据后自动生成客群画像关键词。\n")
    return "\n".join(lines)


def segment_shares(mix: pd.DataFrame) -> list[dict]:
    """返回客源类型营收占比列表（供 GEO 清单 / 简报用）。"""
    if mix is None or mix.empty:
        return []
    share = _segment_revenue_share(mix)
    ranked = rank_segments(mix)
    out = []
    for _, r in ranked.iterrows():
        out.append({
            "segment": r["segment_type"],
            "pct": share.get(r["segment_type"], 0.0) * 100,
            "tier": r["价值等级"],
        })
    return out


# ═══════════════════════════════════════════════════════════════
# 六、简报 / 早报摘要（供飞书定时调度）
# ═══════════════════════════════════════════════════════════════

def build_daily_summary(mix: pd.DataFrame = None,
                        customers: pd.DataFrame = None) -> dict:
    """生成飞书客源日报摘要。

    优先用 mix（segment_mix 表数据）；为空时用 customers 实时聚合。
    返回 {"ok":True, "date", "lines", "health", "alerts"}。
    """
    if mix is None or mix.empty:
        if customers is not None:
            mix = segment_mix_from_customers(customers)
    if mix is None or mix.empty:
        return {"ok": False, "lines": [], "health": [], "alerts": []}

    health = diagnose_health(mix)
    top = rank_segments(mix)
    lines = []
    for _, r in top.head(6).iterrows():
        lines.append(
            f"• **{r['segment_type']}** [等级{r['价值等级']}] 贡献¥{r['净贡献']:,.0f}"
            f"（{r['贡献占比']}%）· 平均入住 {r['avg_los']:.1f}晚"
        )
    alerts = [
        {"severity": "WARN", "title": h_["label"], "detail": h_["message"]}
        for h_ in health if h_["status"] == "WARN"
    ]
    return {
        "ok": True,
        "date": date.today().isoformat(),
        "lines": lines,
        "health": health,
        "alerts": alerts,
    }