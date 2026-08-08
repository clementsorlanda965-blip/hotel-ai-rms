"""
decision_trees.py —— 酒店收益管理 10 棵决策树 v1.0

每棵决策树 = 一组 if/else 规则，输入指标，输出建议动作 + 置信度。
全部规则驱动，无需 LLM，可在 server.py API 中实时调用。

10 棵决策树（按业务场景）：
  1. 基础定价树          — 每日 BAR 价调整方向和幅度
  2. 旺季提价树          — 高需求期最大化利润
  3. 淡季降价树          — 低需求期保现金流
  4. 竞对跟进树          — 竞对大幅调价时的应对策略
  5. 超额预订树          — 房量紧张时的超订/暂停策略
  6. 长住客定价树        — 3晚+长住折扣 vs 短住溢价
  7. OTA vs 直销树       — 渠道价格平衡策略
  8. 提前预订激励树      — 提前预订折扣曲线
  9. 节假日定价树        — 节日/活动溢价系数
  10. 团客报价树         — 团队询价的底线和利润空间

用法：
  from decision_trees import TreeEngine
  engine = TreeEngine()
  result = engine.evaluate("pricing", context)

参考：
  - Cornell 酒店管理学院：收益管理决策框架
  - IDeaS / Duetto 等 RMS 系统的决策逻辑
  - 诺富特 2025 年历史运营数据
"""

from datetime import date, timedelta
from typing import Any

# ═══════════════════════════════════════════════════════════════
# 决策树引擎
# ═══════════════════════════════════════════════════════════════

class TreeEngine:
    """决策树引擎：注册 → 评估 → 收集结果"""

    def __init__(self):
        self._trees = {}
        for name in TREE_REGISTRY:
            self._trees[name] = TREE_REGISTRY[name]

    def evaluate(self, tree_name: str, ctx: dict) -> dict:
        """评估单棵决策树。"""
        tree = self._trees.get(tree_name)
        if not tree:
            return {"error": f"Unknown tree: {tree_name}"}
        return tree(ctx)

    def evaluate_all(self, ctx: dict) -> dict:
        """评估所有注册的决策树。"""
        results = {}
        for name in TREE_REGISTRY:
            results[name] = self.evaluate(name, ctx)
        return results

    def summary(self, ctx: dict) -> list[dict]:
        """按优先级输出所有决策树的关键动作。"""
        results = self.evaluate_all(ctx)
        actions = []
        for name, r in results.items():
            if r.get("action") and r["action"] != "hold":
                actions.append({
                    "tree": name,
                    "action": r["action"],
                    "detail": r.get("detail", ""),
                    "priority": r.get("priority", 3),
                    "confidence": r.get("confidence", 0.5),
                })
        return sorted(actions, key=lambda x: (-x["priority"], -x["confidence"]))


# ═══════════════════════════════════════════════════════════════
# 1. 基础定价树
# ═══════════════════════════════════════════════════════════════

def tree_base_pricing(ctx: dict) -> dict:
    """每日 BAR 价调整方向和幅度。

    输入: occ, adr, forecast_occ, pace_deviation (当前 Pace vs 历史同期偏差 %)
    输出: {action, magnitude_pct, detail, confidence}
    """
    occ = ctx.get("occ", 65)
    forecast_occ = ctx.get("forecast_occ", 65)
    pace_dev = ctx.get("pace_deviation", 0)  # 正数=快于同期，负数=慢于同期
    days_ahead = ctx.get("days_ahead", 30)

    if occ > 90 and pace_dev > 15:
        return {"action": "raise", "magnitude_pct": 10, "priority": 1,
                "detail": f"OCC {occ}% + Pace +{pace_dev}% → 强势提价 10%",
                "confidence": 0.92}
    elif occ > 85 and pace_dev > 5:
        return {"action": "raise", "magnitude_pct": 5, "priority": 1,
                "detail": f"OCC {occ}% + Pace +{pace_dev}% → 适度提价 5%",
                "confidence": 0.85}
    elif occ < 50 and pace_dev < -10:
        return {"action": "lower", "magnitude_pct": 15, "priority": 1,
                "detail": f"OCC {occ}% + Pace {pace_dev}% → 紧急降价 15% 抢量",
                "confidence": 0.90}
    elif occ < 65 and pace_dev < -5:
        return {"action": "lower", "magnitude_pct": 8, "priority": 2,
                "detail": f"OCC {occ}% + Pace {pace_dev}% → 降价 8% 刺激需求",
                "confidence": 0.82}
    elif days_ahead < 7 and occ < 70:
        return {"action": "lower", "magnitude_pct": 10, "priority": 1,
                "detail": f"距入住 {days_ahead} 天 + OCC {occ}% → 短期降价填房",
                "confidence": 0.88}
    elif days_ahead < 3 and occ < 80:
        return {"action": "lower", "magnitude_pct": 15, "priority": 1,
                "detail": f"距入住 {days_ahead} 天 + OCC {occ}% → 最后时刻甩卖",
                "confidence": 0.85}
    elif pace_dev > 20:
        return {"action": "raise", "magnitude_pct": 8, "priority": 2,
                "detail": f"Pace 远超同期 +{pace_dev}% → 激进提价收割",
                "confidence": 0.78}
    else:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "各指标在正常范围，维持现价",
                "confidence": 0.70}


# ═══════════════════════════════════════════════════════════════
# 2. 旺季提价树
# ═══════════════════════════════════════════════════════════════

def tree_peak_season(ctx: dict) -> dict:
    """旺季溢价策略。季节系数 >1.2 时触发。"""
    season_coef = ctx.get("season_coefficient", 1.0)
    occ = ctx.get("occ", 65)
    comp_premium = ctx.get("comp_price_premium", 0)  # 自家比竞对均价高/低 %

    if season_coef < 1.15:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "非旺季，跳过旺季溢价",
                "confidence": 1.0}

    if occ > 85:
        return {"action": "raise", "magnitude_pct": 15, "priority": 1,
                "detail": f"旺季 + OCC {occ}% → 最高溢价 15%",
                "confidence": 0.95}
    elif occ > 70:
        return {"action": "raise", "magnitude_pct": 10, "priority": 1,
                "detail": f"旺季 + OCC {occ}% → 标准旺季溢价 10%",
                "confidence": 0.90}
    elif comp_premium > 20:
        return {"action": "lower", "magnitude_pct": 5, "priority": 2,
                "detail": f"旺季但自家溢价 {comp_premium}% 高于竞对 → 回调 5% 防流失",
                "confidence": 0.75}
    else:
        return {"action": "raise", "magnitude_pct": 5, "priority": 2,
                "detail": "旺季弱需求 → 保守溢价 5%",
                "confidence": 0.70}


# ═══════════════════════════════════════════════════════════════
# 3. 淡季降价树
# ═══════════════════════════════════════════════════════════════

def tree_off_season(ctx: dict) -> dict:
    """淡季保量策略。季节系数 <0.9 时触发。"""
    season_coef = ctx.get("season_coefficient", 1.0)
    occ = ctx.get("occ", 65)
    gop_rate = ctx.get("gop_rate", 35)
    floor_price = ctx.get("floor_price", 399)

    if season_coef > 0.90:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "非淡季，跳过淡季策略",
                "confidence": 1.0}

    current_bar = ctx.get("bar_price", 500)

    if occ < 31.3:  # 低于运营保本 OCC
        return {"action": "lower", "magnitude_pct": 25, "priority": 1,
                "detail": f"OCC {occ}% 低于运营保本 31.3% → 大幅降价抢现金流（不破 ¥{floor_price}）",
                "confidence": 0.95}
    elif occ < 50 and gop_rate < 25:
        return {"action": "lower", "magnitude_pct": 15, "priority": 1,
                "detail": f"OCC {occ}% + GOP {gop_rate}% → 双低压倒性降价",
                "confidence": 0.90}
    elif occ < 65:
        return {"action": "lower", "magnitude_pct": 8, "priority": 2,
                "detail": f"淡季 OCC {occ}% → 促销降价 8%",
                "confidence": 0.82}
    elif current_bar <= floor_price + 50:
        return {"action": "hold", "magnitude_pct": 0, "priority": 1,
                "detail": f"已接近底价（¥{current_bar} vs ¥{floor_price}），不再降",
                "confidence": 0.95}
    else:
        return {"action": "lower", "magnitude_pct": 5, "priority": 3,
                "detail": "淡季微调降价 5% 保持竞争力",
                "confidence": 0.70}


# ═══════════════════════════════════════════════════════════════
# 4. 竞对跟进树
# ═══════════════════════════════════════════════════════════════

def tree_competitor_response(ctx: dict) -> dict:
    """竞对大幅调价时的应对策略。"""
    comp_change_pct = ctx.get("comp_largest_drop_pct", 0)  # 竞对最大降幅 %
    comp_avg = ctx.get("competitor_avg_price", 400)
    self_bar = ctx.get("bar_price", 500)

    if comp_change_pct < 5:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "竞对价格稳定，无需跟进",
                "confidence": 0.90}

    premium = (self_bar - comp_avg) / comp_avg if comp_avg > 0 else 0

    if comp_change_pct > 20:
        if premium > 30:
            return {"action": "lower", "magnitude_pct": 10, "priority": 1,
                    "detail": f"竞对集体大跌 {comp_change_pct}%+，自家溢价 {premium:.0%}→ 跟降 10% 防份额流失",
                    "confidence": 0.90}
        else:
            return {"action": "lower", "magnitude_pct": 5, "priority": 2,
                    "detail": f"竞对跌幅大但自家溢价不高 → 保守跟降 5%",
                    "confidence": 0.75}
    elif comp_change_pct > 10:
        if premium > 20:
            return {"action": "lower", "magnitude_pct": 7, "priority": 2,
                    "detail": f"竞对降 {comp_change_pct}% + 自家溢价 {premium:.0%} → 跟降 7%",
                    "confidence": 0.80}
        else:
            return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                    "detail": "竞对适度降价，自家溢价可接受 → 维持",
                    "confidence": 0.75}
    elif comp_change_pct > 5 and premium > 25:
        return {"action": "lower", "magnitude_pct": 5, "priority": 2,
                "detail": f"竞对微降 {comp_change_pct}% 但自家溢价过高 {premium:.0%} → 微调 5%",
                "confidence": 0.72}
    else:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "竞对降幅在可接受范围",
                "confidence": 0.80}


# ═══════════════════════════════════════════════════════════════
# 5. 超额预订树
# ═══════════════════════════════════════════════════════════════

def tree_overbooking(ctx: dict) -> dict:
    """房量紧张时的超订/暂停决策。"""
    occ = ctx.get("occ", 65)
    rooms_available = ctx.get("rooms_available", 170)
    rooms_sold = ctx.get("room_sold", int(occ / 100 * rooms_available))
    cancel_rate = ctx.get("cancel_rate", 0.12)  # 历史取消率
    no_show_rate = ctx.get("no_show_rate", 0.05)
    rooms_left = rooms_available - rooms_sold
    occupancy_pct = rooms_sold / rooms_available if rooms_available > 0 else 0

    # 基于净取消率计算合理超订上限
    net_loss_rate = cancel_rate + no_show_rate
    safe_overbook = int(rooms_available * net_loss_rate * 0.7)

    if rooms_left <= 3 and occupancy_pct > 0.95:
        return {"action": "stop_selling", "magnitude_pct": 0, "priority": 1,
                "detail": f"仅剩 {rooms_left} 间 + OCC {occupancy_pct:.0%} → 停止所有折扣渠道，仅售 BAR+/Walk-in",
                "confidence": 0.95,
                "walk_in_price_multiplier": 1.20}
    elif rooms_left <= 10 and occupancy_pct > 0.85:
        return {"action": "overbook", "magnitude_pct": safe_overbook, "priority": 1,
                "detail": f"超订 {safe_overbook} 间（净损失率 {net_loss_rate:.0%} × 0.7）→ "
                          f"关闭 OTA 促销、只接受 BAR 价预订",
                "confidence": 0.85,
                "max_overbook": safe_overbook}
    elif rooms_left <= 20:
        return {"action": "tighten", "magnitude_pct": 0, "priority": 2,
                "detail": f"剩余 {rooms_left} 间 → 关闭早鸟折扣，维持当前 BAR",
                "confidence": 0.80}
    elif occupancy_pct < 0.50:
        return {"action": "open_all", "magnitude_pct": 0, "priority": 2,
                "detail": f"OCC {occupancy_pct:.0%} → 开放所有渠道和折扣",
                "confidence": 0.90}
    else:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "房态正常，维持标准超订策略",
                "confidence": 0.80}


# ═══════════════════════════════════════════════════════════════
# 6. 长住客定价树
# ═══════════════════════════════════════════════════════════════

def tree_long_stay(ctx: dict) -> dict:
    """长住客折扣 vs 短住溢价。"""
    occ = ctx.get("occ", 65)
    bar_price = ctx.get("bar_price", 500)
    season_coef = ctx.get("season_coefficient", 1.0)

    if occ > 80 and season_coef > 1.2:
        # 旺季 + 高入住 → 不给长住折扣
        return {"action": "hold", "magnitude_pct": 0, "priority": 1,
                "detail": "旺季高入住，不提供长住折扣 — 短住即可填满",
                "confidence": 0.95,
                "discount_3night": 0, "discount_5night": 0, "discount_7night": 0}
    elif occ < 55:
        # 淡季 + 低入住 → 给长住折扣吸引需求
        return {"action": "lower", "magnitude_pct": 0, "priority": 2,
                "detail": "淡季低入住 — 长住折扣吸引需求：3晚-8%、5晚-12%、7晚-15%",
                "confidence": 0.85,
                "discount_3night": 8, "discount_5night": 12, "discount_7night": 15}
    elif occ < 70:
        return {"action": "lower", "magnitude_pct": 0, "priority": 3,
                "detail": "温和长住折扣：3晚-5%、5晚-8%、7晚-10%",
                "confidence": 0.80,
                "discount_3night": 5, "discount_5night": 8, "discount_7night": 10}
    else:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "标准长住折扣：3晚-3%、5晚-5%、7晚-8%",
                "confidence": 0.75,
                "discount_3night": 3, "discount_5night": 5, "discount_7night": 8}


# ═══════════════════════════════════════════════════════════════
# 7. OTA vs 直销树
# ═══════════════════════════════════════════════════════════════

def tree_channel_pricing(ctx: dict) -> dict:
    """渠道价格平衡：直销 vs OTA 价差策略。"""
    direct_ratio = ctx.get("direct_booking_ratio", 25)
    ota_commission = ctx.get("ota_commission_rate", 0.15)
    bar_price = ctx.get("bar_price", 500)

    # 直销价应低于 OTA 价（因为没有佣金），但 OTA 上不做价格战
    if direct_ratio < 20:
        return {"action": "direct_discount", "magnitude_pct": 0, "priority": 1,
                "detail": f"直销占比仅 {direct_ratio}% → 微信小程序下单立减 ¥30 + 会员价 BAR×0.92",
                "confidence": 0.90,
                "direct_price": round(bar_price * 0.92),
                "ota_price": bar_price,
                "wechat_coupon": 30}
    elif direct_ratio < 35:
        return {"action": "direct_discount", "magnitude_pct": 0, "priority": 2,
                "detail": f"直销占比 {direct_ratio}% → 会员价 BAR×0.95（含早），OTA 维持 BAR",
                "confidence": 0.82,
                "direct_price": round(bar_price * 0.95),
                "ota_price": bar_price}
    else:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": f"直销占比 {direct_ratio}% 健康 → 维持当前渠道定价策略",
                "confidence": 0.85}


# ═══════════════════════════════════════════════════════════════
# 8. 提前预订激励树
# ═══════════════════════════════════════════════════════════════

def tree_advance_booking(ctx: dict) -> dict:
    """提前预订折扣曲线：不同提前天数的折扣力度。"""
    occ = ctx.get("occ", 65)
    season_coef = ctx.get("season_coefficient", 1.0)
    forecast_occ = ctx.get("forecast_occ", 65)

    if season_coef > 1.2 and forecast_occ > 75:
        # 旺季不鼓励提前折扣
        return {"action": "hold", "magnitude_pct": 0, "priority": 1,
                "detail": "旺季高预期 → 关闭所有提前预订折扣",
                "confidence": 0.95,
                "discount_60d": 0, "discount_30d": 0, "discount_14d": 0}
    elif forecast_occ < 50:
        return {"action": "discount", "magnitude_pct": 0, "priority": 2,
                "detail": "低预期 → 提前预订折扣：60天-15%、30天-10%、14天-5%",
                "confidence": 0.85,
                "discount_60d": 15, "discount_30d": 10, "discount_14d": 5}
    else:
        return {"action": "discount", "magnitude_pct": 0, "priority": 3,
                "detail": "标准提前预订折扣：60天-10%、30天-7%、14天-3%",
                "confidence": 0.78,
                "discount_60d": 10, "discount_30d": 7, "discount_14d": 3}


# ═══════════════════════════════════════════════════════════════
# 9. 节假日定价树
# ═══════════════════════════════════════════════════════════════

def tree_holiday_pricing(ctx: dict) -> dict:
    """节假日/活动日的溢价策略。"""
    event_type = ctx.get("event_type", "none")
    event_occ_lift = ctx.get("event_occ_lift", 0)  # 历史上该事件对 OCC 的提升 %
    occ = ctx.get("occ", 65)

    holiday_table = {
        "国庆":  {"premium": 0.40, "min_stay": 3, "release_days": 60},
        "五一":  {"premium": 0.30, "min_stay": 2, "release_days": 45},
        "春节":  {"premium": 0.35, "min_stay": 2, "release_days": 60},
        "端午":  {"premium": 0.15, "min_stay": 1, "release_days": 21},
        "中秋":  {"premium": 0.20, "min_stay": 1, "release_days": 30},
        "暑假":  {"premium": 0.25, "min_stay": 1, "release_days": 0},
        "淡季":  {"premium": -0.10, "min_stay": 1, "release_days": 0},
    }

    # 模糊匹配（事件名含有关键词即可）
    matched = None
    for keyword, config in holiday_table.items():
        if keyword in str(event_type):
            matched = (keyword, config)
            break

    if not matched and event_occ_lift < 10:
        return {"action": "hold", "magnitude_pct": 0, "priority": 3,
                "detail": "无特殊节假日事件 → 常规定价",
                "confidence": 0.90}

    if matched:
        name, cfg = matched
        return {"action": "raise" if cfg["premium"] > 0 else "lower",
                "magnitude_pct": abs(cfg["premium"] * 100),
                "priority": 1,
                "detail": f"{name}定价：溢价 {cfg['premium']:.0%}、最少 {cfg['min_stay']} 晚、"
                          f"提前 {cfg['release_days']} 天开放预订",
                "confidence": 0.88,
                "min_stay": cfg["min_stay"],
                "release_days_before": cfg["release_days"]}

    # 基于历史 OCC lift 的通用事件定价
    if event_occ_lift > 30:
        premium = 0.25
    elif event_occ_lift > 20:
        premium = 0.15
    elif event_occ_lift > 10:
        premium = 0.08
    else:
        premium = 0

    return {"action": "raise" if premium > 0 else "hold",
            "magnitude_pct": premium * 100,
            "priority": 2,
            "detail": f"事件日 OCC 历史提升 {event_occ_lift}% → 溢价 {premium:.0%}",
            "confidence": 0.75}


# ═══════════════════════════════════════════════════════════════
# 10. 团客报价树
# ═══════════════════════════════════════════════════════════════

def tree_group_quote(ctx: dict) -> dict:
    """团体预订报价：最低可接受价 + 利润空间。"""
    occ = ctx.get("occ", 65)
    bar_price = ctx.get("bar_price", 500)
    variable_cost = ctx.get("avg_variable_cost_per_room", 45)
    group_size = ctx.get("group_size", 10)
    group_stay_nights = ctx.get("group_stay_nights", 1)
    season_coef = ctx.get("season_coefficient", 1.0)

    # 基础底线 = 变动成本 + 最低边际贡献 ¥100
    floor = variable_cost + 100

    if occ > 85 and season_coef > 1.2:
        return {"action": "reject_or_premium", "magnitude_pct": 0, "priority": 1,
                "detail": f"旺季高入住 → 不接受团客折扣，报价 BAR×1.10 （¥{round(bar_price*1.10)}）",
                "confidence": 0.95,
                "quote_price": round(bar_price * 1.10),
                "negotiable_floor": bar_price}
    elif occ > 70:
        discount = 0.10 if group_size >= 20 else 0.05
        return {"action": "quote", "magnitude_pct": 0, "priority": 2,
                "detail": f"团客 {group_size} 人/{group_stay_nights} 晚 → "
                          f"报价 BAR×{1-discount:.0%}（¥{round(bar_price*(1-discount))}），底线 ¥{floor}",
                "confidence": 0.85,
                "quote_price": round(bar_price * (1 - discount)),
                "negotiable_floor": floor}
    else:
        # 淡季/低入住 → 团客是好生意
        discount = 0.20 if group_size >= 20 else 0.12
        return {"action": "quote_aggressive", "magnitude_pct": 0, "priority": 2,
                "detail": f"淡季低入住 + 团客 {group_size} 人 → "
                          f"报价 BAR×{1-discount:.0%}（¥{round(bar_price*(1-discount))}），底线 ¥{floor}",
                "confidence": 0.88,
                "quote_price": round(bar_price * (1 - discount)),
                "negotiable_floor": floor,
                "include_meals": True,  # 淡季可含餐增加吸引力
                "meal_price_per_person": 120}


# ═══════════════════════════════════════════════════════════════
# 注册表
# ═══════════════════════════════════════════════════════════════

TREE_REGISTRY = {
    "base_pricing":      tree_base_pricing,
    "peak_season":       tree_peak_season,
    "off_season":        tree_off_season,
    "competitor_response": tree_competitor_response,
    "overbooking":       tree_overbooking,
    "long_stay":         tree_long_stay,
    "channel_pricing":   tree_channel_pricing,
    "advance_booking":   tree_advance_booking,
    "holiday_pricing":   tree_holiday_pricing,
    "group_quote":       tree_group_quote,
}


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  10 棵决策树自测")
    print("=" * 60)

    engine = TreeEngine()

    test_contexts = [
        {"name": "旺季高入住", "occ": 88, "forecast_occ": 90, "pace_deviation": 20,
         "season_coefficient": 1.35, "bar_price": 700, "gop_rate": 42,
         "competitor_avg_price": 395, "comp_largest_drop_pct": 3},
        {"name": "淡季低入住", "occ": 42, "forecast_occ": 45, "pace_deviation": -15,
         "season_coefficient": 0.75, "bar_price": 400, "gop_rate": 22,
         "competitor_avg_price": 350, "comp_largest_drop_pct": 20},
        {"name": "竞对大跌", "occ": 65, "forecast_occ": 68, "pace_deviation": -3,
         "season_coefficient": 1.10, "bar_price": 600, "gop_rate": 35,
         "competitor_avg_price": 380, "comp_largest_drop_pct": 25, "comp_price_premium": 35},
    ]

    for tc in test_contexts:
        print(f"\n  ── 场景: {tc['name']} ──")
        actions = engine.summary(tc)
        for a in actions[:5]:
            flag = "🔴" if a["priority"] == 1 else ("🟡" if a["priority"] == 2 else "⚪")
            print(f"  {flag} [{a['tree']}] {a['detail']} (置信 {a['confidence']:.0%})")
