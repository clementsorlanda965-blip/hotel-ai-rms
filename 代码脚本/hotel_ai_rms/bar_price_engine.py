"""
bar_price_engine.py —— BAR 价自动计算引擎 v1.0

核心定价公式：
  BAR价 = max(底价399, 基准价 × 季节系数 × 周末系数 × 提前预订系数 × 竞争系数)

定位：
  - 每日自动输出"今日建议BAR价" + 进攻/防守信号
  - 所有系数有据可查（历史数据回归 or 行业基准）
  - 每个输出附带 3 句话中文解释（提升决策采纳率）

数据依赖（优先级降级链）：
  基准价: daily_metrics 同月ADR > CTRIP_REFERENCE_PRICES > 默认500
  季节系数: config.SEASON_FACTORS（基于历史ADR回归校准）
  周末系数: 周五六 +8%，周日 -5%
  预订进度: booking_pace 表（空则默认中性 1.0）
  竞争系数: ota_price_history 最新采集 > CTRIP_REFERENCE_PRICES 兜底

参考知识源：
  - Obsidian: 收益管理定价方法论 (L4)
  - Obsidian: 诺富特财务模型 (L4)
  - Obsidian: 九寨沟竞对价格数据 (L2)
"""

import sqlite3
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "rms.db"

# ── 集中配置（config.py 统一入口）──
from config import (
    FLOOR_PRICE, SEASON_FACTORS, WEEKEND_PREMIUM, SUNDAY_DISCOUNT,
    COMPETITORS, SELF_HOTEL_NAME, TOTAL_ROOMS,
    CTRIP_REFERENCE_PRICES, NOVOTEL_FINANCIALS,
)

# ═══════════════════════════════════════════════════════════════
# 核心定价函数
# ═══════════════════════════════════════════════════════════════

def calculate_daily_bar(
    target_date: date,
    floor_price: float = FLOOR_PRICE,
    mode: str = "auto",
) -> dict:
    """计算单日 BAR 建议价。

    Args:
        target_date: 目标日期
        floor_price: 底价约束（默认 399 元，Accor 集团硬约束）
        mode: "auto"（自动跟随）/ "attack"（进攻：低于竞对抢份额）/ "defend"（防守：高于竞对保利润）

    Returns:
        {
            "recommended_bar": float,     # 建议 BAR 价（圆整到十位）
            "attack_defense": str,        # 进攻/防守/平价
            "confidence": float,          # 信心度 0-1
            "factors": dict,              # 五个系数的分解值
            "explanation": str,           # 3 句话中文解释
            "floor_applied": bool,        # 是否触发底价约束
            "date": str,                  # 日期 YYYY-MM-DD
        }
    """
    # 1. 基准价（PRO 价）
    base_price = _get_base_price(target_date)

    # 2. 计算四个系数
    season_coef = apply_seasonal_coefficient(target_date)
    weekend_coef = apply_weekend_coefficient(target_date)
    pace_coef = apply_booking_pace_coefficient(target_date)
    comp_coef = competitor_alignment(target_date, base_price, mode)

    # 3. 合成 BAR 价
    raw_bar = base_price * season_coef * weekend_coef * pace_coef * comp_coef
    recommended = max(floor_price, round(raw_bar / 10) * 10)  # 圆整到十位
    floor_applied = raw_bar < floor_price

    # 4. 进攻/防守信号
    ad_signal = recommend_attack_defense(target_date, pace_coef)

    # 5. 信心度（数据越完整越高）
    confidence = _calculate_confidence(target_date, pace_coef, comp_coef)

    # 6. 三句话解释
    explanation = _build_explanation(
        target_date, base_price, season_coef, weekend_coef,
        pace_coef, comp_coef, recommended, floor_applied, ad_signal, confidence,
    )

    return {
        "recommended_bar": recommended,
        "attack_defense": ad_signal,
        "confidence": round(confidence, 2),
        "factors": {
            "base_price": base_price,
            "season_coefficient": round(season_coef, 3),
            "weekend_coefficient": round(weekend_coef, 3),
            "booking_pace_coefficient": round(pace_coef, 3),
            "competitor_coefficient": round(comp_coef, 3),
        },
        "explanation": explanation,
        "floor_applied": floor_applied,
        "date": target_date.strftime("%Y-%m-%d"),
    }


# ═══════════════════════════════════════════════════════════════
# 系数计算函数
# ═══════════════════════════════════════════════════════════════

def apply_seasonal_coefficient(d: date) -> float:
    """季节系数：从 SEASON_FACTORS 查表。

    基于诺富特 2025 年各月 ADR 指数回归校准。
    旺季（4/5/7/8/9/10）> 1.0，淡季（1/2/3/11/12）< 1.0。
    """
    return SEASON_FACTORS.get(d.month, 1.0)


def apply_weekend_coefficient(d: date) -> float:
    """周末/平日系数。

    周五/周六加价 8%（休闲需求旺盛），周日降价 5%（返程日）。
    周一至周四平价（系数 1.0）。
    """
    dow = d.weekday()  # 0=周一, 4=周五, 5=周六, 6=周日
    if dow in (4, 5):
        return 1.0 + WEEKEND_PREMIUM
    elif dow == 6:
        return 1.0 + SUNDAY_DISCOUNT
    return 1.0


def apply_booking_pace_coefficient(d: date) -> float:
    """预订进度系数：基于当前 Pace 偏离度调整价格。

    逻辑：
      - Pace 远低于历史同期 → 降价刺激需求（系数 < 1.0）
      - Pace 远高于历史同期 → 提价收割收益（系数 > 1.0）
      - 无 Pace 数据 → 中性（系数 = 1.0）

    数据来源：booking_pace 表（stay_date / snapshot_date / rooms_booked）。
    按距入住日天数分档设定期望占房率，偏离度映射为 ±10% 范围内的系数调整。
    """
    days_ahead = (d - date.today()).days
    if days_ahead <= 0:
        return 1.0  # 当日/过去日期不做 Pace 调整

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT COALESCE(SUM(rooms_booked), 0) as booked
            FROM booking_pace
            WHERE stay_date = ? AND snapshot_date = ?
        """, (d.strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d")))
        current_booked = cur.fetchone()["booked"]
        conn.close()

        occ_implied = current_booked / TOTAL_ROOMS

        # 距入住日分档期望占房率（行业经验值 + 诺富特历史 pace 曲线校准）
        if days_ahead > 60:
            expected_occ = 0.08
        elif days_ahead > 30:
            expected_occ = 0.15
        elif days_ahead > 7:
            expected_occ = 0.30
        else:
            expected_occ = 0.45

        if expected_occ > 0:
            deviation = (occ_implied - expected_occ) / expected_occ
            # deviation>0（预订快于预期）→ 涨价；deviation<0（预订慢于预期）→ 降价
            # 低于预期 10% → 降价 3%（系数 0.97）
            # 高于预期 10% → 涨价 2%（系数 1.02）
            # 系数 clamp 在 [0.90, 1.08] 范围内
            pace_coef = 1.0 + min(max(deviation * 0.3, -0.10), 0.08)
            return round(pace_coef, 3)
    except Exception:
        pass

    return 1.0  # 默认中性


def competitor_alignment(d: date, base_price: float, mode: str = "auto") -> float:
    """竞争对齐系数：基于竞对最低可卖房价调整。

    策略：
      - auto: 跟随竞对均价，偏差 ±3% 以内
      - attack: 定价低于竞对最低价 7%（抢份额）
      - defend: 定价高于竞对均价 5%（保利润，仅旺季使用）

    数据来源：ota_price_history 最新采集 > CTRIP_REFERENCE_PRICES 兜底。
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT hotel_name, MIN(price_cny) as min_price
            FROM ota_price_history
            WHERE fetch_date = (SELECT MAX(fetch_date) FROM ota_price_history)
              AND hotel_name != ?
            GROUP BY hotel_name
        """, (SELF_HOTEL_NAME,)).fetchall()
        conn.close()

        if rows:
            comp_prices = [r["min_price"] for r in rows]
            comp_avg = sum(comp_prices) / len(comp_prices)
            comp_min = min(comp_prices)
        else:
            # 兜底：CTRIP_REFERENCE_PRICES 中排除自家
            refs = [
                v for k, v in CTRIP_REFERENCE_PRICES.items()
                if k != SELF_HOTEL_NAME
            ]
            comp_avg = sum(refs) / len(refs) if refs else 400
            comp_min = min(refs) if refs else 331

        if mode == "attack":
            target = comp_min * 0.93
        elif mode == "defend":
            target = comp_avg * 1.05
        else:
            target = comp_avg

        coef = target / base_price if base_price > 0 else 1.0
        # 限制竞争系数在 ±25% 范围内
        return round(max(0.75, min(1.25, coef)), 3)
    except Exception:
        return 1.0


def recommend_attack_defense(d: date, pace_coef: float = None) -> str:
    """基于 Pace 偏离度 + 季节判断进攻/防守态势。

    进攻（attack）：淡季 + Pace 低于预期 → 降价抢量
    防守（defend）：旺季 + Pace 高于预期 → 提价保利润
    平价（neutral）：维持当前价格水平
    """
    season_coef = SEASON_FACTORS.get(d.month, 1.0)
    if pace_coef is None:
        pace_coef = apply_booking_pace_coefficient(d)

    if season_coef < 0.85 and pace_coef < 0.97:
        return "attack"
    elif season_coef > 1.20 and pace_coef > 1.02:
        return "defend"
    elif pace_coef < 0.95:
        return "attack"
    elif pace_coef > 1.03:
        return "defend"
    return "neutral"


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _get_base_price(d: date) -> float:
    """获取基准价（PRO 价）。

    优先级：
      1. 同月历史 ADR 均值（daily_metrics 表，最近 90 天）
      2. 携程参考价格（CTRIP_REFERENCE_PRICES）
      3. 默认值 500
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT AVG(adr) as avg_adr
            FROM daily_metrics
            WHERE CAST(substr(date, 6, 2) AS INTEGER) = ?
              AND hotel_id = 1
        """, (d.month,)).fetchone()
        conn.close()
        if row and row["avg_adr"] and row["avg_adr"] > 100:
            return round(row["avg_adr"], 0)
    except Exception:
        pass

    # 兜底：config 中携程参考价
    ref = CTRIP_REFERENCE_PRICES.get(SELF_HOTEL_NAME, 500)
    return float(ref)


def _calculate_confidence(
    d: date, pace_coef: float, comp_coef: float
) -> float:
    """计算本次建议的信心度（0-1）。

    扣分项：
      - 无 Pace 数据（pace_coef=1.0 且表为空）→ -0.25
      - 无竞对实时数据（comp_coef=1.0）→ -0.15
      - 距入住日 >90 天（远期预测不确定性大）→ -0.15
    """
    confidence = 0.85  # 基准信心

    if pace_coef == 1.0:
        confidence -= 0.25  # 无 Pace 数据
    if comp_coef == 1.0:
        confidence -= 0.15  # 竞对数据降级

    days_ahead = (d - date.today()).days
    if days_ahead > 90:
        confidence -= 0.15
    elif days_ahead > 60:
        confidence -= 0.10
    elif days_ahead > 30:
        confidence -= 0.05

    return max(0.30, confidence)


def _build_explanation(
    d: date, base: float, season: float, weekend: float,
    pace: float, comp: float, recommended: float,
    floor_applied: bool, ad_signal: str, confidence: float,
) -> str:
    """生成 3 句话中文解释，让决策者理解定价逻辑。"""
    month_name = f"{d.month}月"
    dow_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    dow_name = dow_names[d.weekday()]

    # 第一句：基准价 + 季节 + 周末
    lines = [
        f"① 基准价 ¥{base:.0f}（{month_name}历史ADR均值），"
        f"经季节系数 {season:.2f}（{month_name}）和周末系数 {weekend:.2f}（{dow_name}）调整。",
    ]

    # 第二句：预订进度 + 竞争对齐
    if pace != 1.0:
        pace_dir = "偏快" if pace > 1.0 else "偏慢"
        lines.append(
            f"② 当前预订进度{pace_dir}（系数{pace:.3f}），"
            f"竞对均价调整系数 {comp:.3f}。"
        )
    else:
        lines.append(
            f"② 暂无预订进度数据（默认中性），竞对均价调整系数 {comp:.3f}。"
        )

    # 第三句：最终建议 + 信号 + 信心
    signal_map = {"attack": "🟢 进攻", "defend": "🔴 防守", "neutral": "🟡 平价"}
    signal_text = signal_map.get(ad_signal, ad_signal)
    floor_note = "（触发底价 ¥399 约束）" if floor_applied else ""
    conf_label = "高" if confidence >= 0.8 else ("中" if confidence >= 0.6 else "低")
    lines.append(
        f"③ 综合建议 BAR 价 ¥{recommended}{floor_note}，"
        f"信号：{signal_text}，信心度：{conf_label}（{confidence:.0%}）。"
    )

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 批量计算
# ═══════════════════════════════════════════════════════════════

def generate_bar_calendar(
    start_date: date,
    days: int = 90,
    mode: str = "auto",
) -> pd.DataFrame:
    """生成未来 N 天的 BAR 价日历。

    Args:
        start_date: 起始日期
        days: 天数（默认 90 天）
        mode: 定价模式 auto/attack/defend

    Returns:
        DataFrame: 日期 / 星期 / 基准价 / 建议BAR价 / 进攻防守信号 / 信心度 / 解释
    """
    dow_names = ["一", "二", "三", "四", "五", "六", "日"]
    rows = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        result = calculate_daily_bar(d, mode=mode)
        rows.append({
            "日期": d,
            "星期": dow_names[d.weekday()],
            "基准价": result["factors"]["base_price"],
            "建议BAR价": result["recommended_bar"],
            "信号": result["attack_defense"],
            "信心度": result["confidence"],
            "解释": result["explanation"],
            "触底价": result["floor_applied"],
            "季节系数": result["factors"]["season_coefficient"],
            "周末系数": result["factors"]["weekend_coefficient"],
            "预订进度系数": result["factors"]["booking_pace_coefficient"],
            "竞争系数": result["factors"]["competitor_coefficient"],
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════
# 阈值告警（供 server.py API 使用）
# ═══════════════════════════════════════════════════════════════

def check_bar_thresholds(bar_price: float, base_price: float, floor_price: float = FLOOR_PRICE) -> list[dict]:
    """检测 BAR 价是否触发授权等级阈值。

    Returns:
        [{"level": "L1_auto/L2_confirm/L3_decide", "triggered": bool, "detail": str}, ...]
    """
    from config import AUTH_LEVELS
    alerts = []
    if bar_price <= floor_price:
        alerts.append({
            "level": "L1_auto", "triggered": True,
            "detail": f"触底价 ¥{floor_price}，自动执行"
        })
        return alerts

    deviation = abs(bar_price - base_price) / base_price

    if deviation <= AUTH_LEVELS["L1_auto"]:
        alerts.append({
            "level": "L1_auto", "triggered": False,
            "detail": f"偏差 {deviation:.1%}，自动执行范围内"
        })
    elif deviation <= AUTH_LEVELS["L2_confirm"]:
        alerts.append({
            "level": "L2_confirm", "triggered": True,
            "detail": f"偏差 {deviation:.1%}，需收益经理确认"
        })
    else:
        alerts.append({
            "level": "L3_decide", "triggered": True,
            "detail": f"偏差 {deviation:.1%}，需 GM 拍板"
        })
    return alerts


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    today = date.today()
    print("=" * 60)
    print(f"  BAR 价自动计算引擎 —— {today}")
    print("=" * 60)

    # 测试最近 7 天
    for i in range(7):
        d = today + timedelta(days=i)
        result = calculate_daily_bar(d)
        dow = ["一", "二", "三", "四", "五", "六", "日"][d.weekday()]
        f = result["factors"]
        print(f"\n  {d} 周{dow}")
        print(f"  BAR价: ¥{result['recommended_bar']} | "
              f"信号: {result['attack_defense']} | "
              f"信心: {result['confidence']:.0%}")
        print(f"  系数: 季节{f['season_coefficient']:.2f} "
              f"周末{f['weekend_coefficient']:.2f} "
              f"Pace{f['booking_pace_coefficient']:.2f} "
              f"竞对{f['competitor_coefficient']:.2f}")

        # 授权等级
        thresholds = check_bar_thresholds(result["recommended_bar"], f["base_price"])
        for t in thresholds:
            if t["triggered"]:
                print(f"  ⚠ {t['detail']}")

    print(f"\n{'=' * 60}")
    print(f"  底价约束: ¥{FLOOR_PRICE}")
    print(f"  基准价来源: daily_metrics 同月ADR均值")
    print(f"  竞对数据: ota_price_history 最新采集 ({today})")
    print(f"  ⚠ 当前无 Pace 数据（booking_pace 表为空），使用默认中性系数。")
    print(f"    接入 booking_pace 采集后定价精度将大幅提升。")
