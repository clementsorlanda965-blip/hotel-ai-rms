"""
guest_segment_pricing.py —— 客群差异化定价引擎 v1.0

4 类客群的独立定价策略：
  1. 品牌散客 (Brand Transient)    — BAR 价基准，价格接受度最高
  2. 企业商务 (Corporate)           — 协议价，量价挂钩
  3. OTA 渠道 (OTA Online)          — 佣金后净价，渠道成本敏感
  4. 旅行社团 (Tour Group)          — 批量低价，量换利

定价逻辑：
  - 品牌散客 = BAR 价（无折扣，全价销售）
  - 企业商务 = BAR × (1 - 协议折扣)，最低保证月产 50 间夜
  - OTA 渠道 = BAR / (1 - 佣金率)（或 BAR × (1+佣金率) 覆盖佣金成本）
  - 旅行社团 = 变动成本 + 边际贡献底线，随行就市

用法：
  from guest_segment_pricing import SegmentPricingEngine
  engine = SegmentPricingEngine()
  prices = engine.calculate_all(bar_price=700, occ=65, season="peak")
  # → {"brand_transient": 700, "corporate": 630, "ota": 700, "tour_group": 280}

参考：
  - IDeaS G3 RMS 客群管理模块
  - 万豪/希尔顿协议客户定价模型
  - 诺富特 2025 客源结构
"""

from datetime import date


# ═══════════════════════════════════════════════════════════════
# 客群定价引擎
# ═══════════════════════════════════════════════════════════════

class SegmentPricingEngine:
    """4 类客群差异化定价"""

    def __init__(self):
        # 基础参数
        self.variable_cost = 45          # 单房变动成本 ¥
        self.min_contribution = 100      # 最低边际贡献 ¥
        self.ota_commission = 0.15       # OTA 佣金率 15%

        # 协议客户折扣（按产量分档）
        self.corporate_tiers = {
            "tier1": {"min_rn_per_month": 200, "discount": 0.18},  # 月产≥200间夜 → -18%
            "tier2": {"min_rn_per_month": 100, "discount": 0.13},  # 月产≥100 → -13%
            "tier3": {"min_rn_per_month": 50,  "discount": 0.08},  # 月产≥50 → -8%
        }

        # 旅行社折扣（按季节 + OCC 浮动）
        self.tour_group_base_discount = 0.60  # 基础折扣 40% off BAR

    def calculate_all(self, bar_price: float, occ: float = 65,
                      season: str = "mid", corp_tier: str = "tier3",
                      ota_parity: bool = True) -> dict:
        """一次计算全部 4 类客群的建议价格。

        Args:
            bar_price: 当日 BAR 价
            occ: 当前出租率 %
            season: peak/mid/low
            corp_tier: 协议客户等级 tier1/tier2/tier3
            ota_parity: 是否维持 OTA 价格一致性（大多数酒店合同要求）

        Returns:
            {"brand_transient": float, "corporate": float, "ota": float, "tour_group": dict}
        """
        return {
            "brand_transient": self.brand_transient_price(bar_price),
            "corporate": self.corporate_price(bar_price, corp_tier, occ),
            "ota": self.ota_price(bar_price, occ, season, ota_parity),
            "tour_group": self.tour_group_price(bar_price, occ, season),
        }

    # ── 品牌散客 ──

    def brand_transient_price(self, bar_price: float) -> dict:
        """品牌散客 = BAR 价。无折扣，但可搭配套餐。"""
        return {
            "room_only": bar_price,
            "with_breakfast": bar_price + 50,       # 含早 +¥50
            "half_board": bar_price + 180,          # 含早+晚餐 +¥180
            "full_board": bar_price + 280,          # 含三餐 +¥280
        }

    # ── 企业商务 ──

    def corporate_price(self, bar_price: float, tier: str = "tier3",
                        occ: float = 65) -> dict:
        """协议客户定价。按产量分档，旺季可暂停低档协议。

        底线：协议价不得低于变动成本 + 最低边际贡献（¥145）。
        """
        tier_config = self.corporate_tiers.get(tier, self.corporate_tiers["tier3"])
        discount = tier_config["discount"]
        min_rn = tier_config["min_rn_per_month"]

        # 旺季 OCC>85% 时暂停 tier3 协议
        if occ > 85 and tier == "tier3":
            return {
                "price": round(bar_price),  # 不给折扣
                "discount_pct": 0,
                "min_rn_per_month": min_rn,
                "status": "暂停 — 旺季高入住，暂停低档协议",
                "tier": tier,
            }

        # OCC<50% 时加大折扣
        if occ < 50:
            discount = min(0.22, discount + 0.05)

        corp_price = bar_price * (1 - discount)
        floor = self.variable_cost + self.min_contribution  # ¥145
        corp_price = max(floor, round(corp_price / 10) * 10)

        return {
            "price": round(corp_price),
            "discount_pct": round(discount * 100, 1),
            "min_rn_per_month": min_rn,
            "status": "活跃",
            "tier": tier,
            "savings_vs_bar": round(bar_price - corp_price, 0),
        }

    # ── OTA 渠道 ──

    def ota_price(self, bar_price: float, occ: float = 65,
                  season: str = "mid", parity: bool = True) -> dict:
        """OTA 渠道定价。

        多数酒店与携程签有"价格一致性"条款：
          OTA 挂牌价 ≥ 官网 BAR 价（不能更低）

        净收入 = OTA挂牌价 × (1 - 佣金率) = BAR × (1 - 佣金率)
        所以实际到手：
          OTA 净价 = BAR − BAR × 15% = 0.85 × BAR

        策略：
          - 直销占比低时，OTA 价 = BAR（不涨价，避免赶客去直销）
          - 直销占比合理时，可考虑 OTA 价 = BAR × 1.05（覆盖佣金成本）
        """
        net_revenue = bar_price * (1 - self.ota_commission)

        if parity:
            # 价格一致性：OTA 挂牌 = BAR
            ota_list_price = bar_price
        else:
            # 隐蔽涨价：OTA 挂牌略高于 BAR（覆盖佣金）
            ota_list_price = round(bar_price * 1.05 / 10) * 10

        return {
            "list_price": ota_list_price,              # OTA 挂牌价
            "net_revenue": round(net_revenue, 0),      # 到手净价
            "commission_cost": round(bar_price * self.ota_commission, 0),  # 佣金成本
            "commission_rate": self.ota_commission * 100,
            "parity_maintained": parity,
            "status": "标准",
        }

    # ── 旅行社团 ──

    def tour_group_price(self, bar_price: float, occ: float = 65,
                         season: str = "mid", group_size: int = 20) -> dict:
        """旅行社团客报价。

        公式：团价 = max(变动成本 + 边际贡献, BAR × 淡季折扣)

        淡季 OCC<50%：团客是好生意，折扣大到 55% off BAR
        旺季 OCC>80%：团客不划算，报高价拒客或接受少量利润团
        """
        floor = self.variable_cost + self.min_contribution  # ¥145

        if occ > 85 and season == "peak":
            # 旺季高入住：不接受低价团
            price = bar_price * 0.85
            rationale = "旺季高入住，团客优惠有限"
            include_meal = False
        elif occ > 70:
            price = bar_price * 0.55
            rationale = "标准团价，需 ≥15 间保底"
            include_meal = False
        elif occ > 50:
            price = bar_price * 0.45
            rationale = "淡季促销团价，含早"
            include_meal = True
        else:
            price = bar_price * 0.40
            rationale = "谷底团价，含早+接送，抢现金流"
            include_meal = True

        # 大团额外优惠
        if group_size >= 50:
            price *= 0.90
            rationale += "（50+大团额外 10% 优惠）"
        elif group_size >= 30:
            price *= 0.95
            rationale += "（30+团额外 5% 优惠）"

        price = max(floor, round(price / 10) * 10)

        return {
            "per_room_price": round(price),
            "discount_vs_bar": round((1 - price / bar_price) * 100, 1),
            "group_size": group_size,
            "minimum_rooms": max(10, group_size),
            "include_meals": include_meal,
            "floor_price": floor,
            "rationale": rationale,
        }

    # ── 客群组合优化 ──

    def optimal_mix(self, bar_price: float, occ: float = 65,
                    season: str = "mid") -> dict:
        """推荐最优客群组合（按当前入住率 + 季节）。

        目标：
          OCC<50%：团客 20% + OTA 50% + 散客 25% + 协议 5%
          OCC 50-70%：OTA 40% + 散客 40% + 协议 15% + 团客 5%
          OCC>70%：散客 50% + 协议 25% + OTA 20% + 团客 5%
        """
        prices = self.calculate_all(bar_price, occ, season)

        if occ < 50:
            mix = {"brand_transient": 25, "corporate": 5, "ota": 50, "tour_group": 20}
        elif occ < 70:
            mix = {"brand_transient": 40, "corporate": 15, "ota": 40, "tour_group": 5}
        else:
            mix = {"brand_transient": 50, "corporate": 25, "ota": 20, "tour_group": 5}

        # 加权平均净价
        avg_net = 0
        for seg, ratio in mix.items():
            seg_price = prices[seg]
            if isinstance(seg_price, dict):
                net = seg_price.get("price", seg_price.get("net_revenue",
                        seg_price.get("per_room_price", bar_price)))
            else:
                net = seg_price
            avg_net += net * ratio / 100

        return {
            "recommended_mix": mix,
            "weighted_avg_net_price": round(avg_net, 0),
            "segment_prices": {
                "brand_transient": bar_price,
                "corporate": prices["corporate"]["price"],
                "ota_net": prices["ota"]["net_revenue"],
                "tour_group": prices["tour_group"]["per_room_price"],
            },
        }


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = SegmentPricingEngine()

    print("=" * 55)
    print("  客群差异化定价引擎")
    print("=" * 55)

    for scenario in [
        ("旺季高入住", 800, 88, "peak"),
        ("平季中入住", 610, 65, "mid"),
        ("淡季低入住", 420, 42, "low"),
    ]:
        label, bar, occ, season = scenario
        print(f"\n  ── {label}: BAR=¥{bar} OCC={occ}% ──")
        prices = engine.calculate_all(bar_price=bar, occ=occ, season=season)

        bt = prices["brand_transient"]
        print(f"  品牌散客: ¥{bt['room_only']} (含早 ¥{bt['with_breakfast']})")

        corp = prices["corporate"]
        print(f"  企业商务: ¥{corp['price']} ({corp['discount_pct']}% off) {corp['status']}")

        ota = prices["ota"]
        print(f"  OTA渠道: 挂牌 ¥{ota['list_price']} → 净价 ¥{ota['net_revenue']} "
              f"(佣金 ¥{ota['commission_cost']})")

        tg = prices["tour_group"]
        print(f"  旅行社团: ¥{tg['per_room_price']} ({tg['discount_vs_bar']}% off BAR) "
              f"{tg['rationale']}")

    # 最优组合
    print(f"\n  ── 最优客群组合（BAR ¥610, OCC=65%）──")
    mix = engine.optimal_mix(610, 65, "mid")
    print(f"  推荐比例: {mix['recommended_mix']}")
    print(f"  加权均价: ¥{mix['weighted_avg_net_price']}")
