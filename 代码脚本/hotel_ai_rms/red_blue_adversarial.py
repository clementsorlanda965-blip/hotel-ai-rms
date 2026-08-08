"""
red_blue_adversarial.py —— 红蓝对抗价格决策验证引擎 v1.0

设计理念（军事演习 × 收益管理）：
  🔵 蓝队（Blue Team）= 收益管理团队 —— 提出定价方案，目标是最大化 RevPAR
  🔴 红队（Red Team）= 攻击性验证 —— 用最坏情况假设攻击蓝队方案，找漏洞
  ⚪ 裁判（Referee）= 合成双方论点，给出最终通过/否决/条件通过判定

流程：
  1. 蓝队提交方案 → "建议 BAR 价 ¥700"
  2. 红队攻击 → "竞对同时降价 15% 怎么办？Pace 不到预期怎么办？"
  3. 独立裁判 → "方案通过，但在以下条件下需触发紧急审查：..."
  4. 输出裁决卡 → by/condition/block + 风险列表 + 建议的刹车条件

5 种攻击维度：
  A. 竞对攻击   — 竞对集体降价 15-25% 的冲击
  B. 需求冲击   — 突发事件（天气/政策/交通中断）导致需求骤降
  C. Pace 幻象 — 预订进度虚高（集中取消/假预订）
  D. 渠道反噬   — OTA 渠道突然提佣/屏蔽/差评爆发
  E. 成本突增   — 人工/能源/食材成本突发上涨

用法：
  from red_blue_adversarial import AdversarialEngine
  engine = AdversarialEngine()
  verdict = engine.validate(proposal)
  if verdict["verdict"] == "block":
      print("定价方案被否决，原因：", verdict["reasons"])

参考：
  - 以色列 IDF 红队方法论（军事决策审查）
  - BlackRock Aladdin 压力测试框架
  - 酒店行业最坏情况场景库（COVID-19 后积累）
"""

from datetime import date
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 攻击载荷定义
# ═══════════════════════════════════════════════════════════════

ATTACK_VECTORS = [
    {
        "id": "A_competitor",
        "name": "竞对集体反击",
        "attack": "假设竞对在未来 7 天内全部降价 {drop_pct}%，你的方案仍成立吗？",
        "severity": 4,  # 1-5
        "drop_pct_range": (15, 30),
        "check": "competitor_response",
    },
    {
        "id": "B_demand_shock",
        "name": "需求冲击",
        "attack": "假设突发 {event} 导致需求骤降 {drop_pct}%，OCC 跌至 {min_occ}%",
        "severity": 4,
        "event_examples": ["暴雨导致九寨沟景区关闭3天", "地震预警导致团队取消",
                           "突发疫情封控", "高速塌方交通中断"],
        "drop_pct_range": (20, 40),
        "check": "demand_shock",
    },
    {
        "id": "C_pace_mirage",
        "name": "Pace 虚高幻象",
        "attack": "当前 Pace 快于同期 {pace_dev}%，但假设其中 {cancel_rate}% 在入住前 7 天集中取消",
        "severity": 3,
        "cancel_rate_range": (15, 35),
        "check": "pace_mirage",
    },
    {
        "id": "D_channel_backfire",
        "name": "渠道反噬",
        "attack": "假设携程将佣金率从 15% 提升至 {comm}%，或美团下线你的酒店 3 天",
        "severity": 3,
        "comm_range": (18, 22),
        "check": "channel_backfire",
    },
    {
        "id": "E_cost_spike",
        "name": "成本突增",
        "attack": "假设水电/人工/食材成本突发上涨 {cost_rise}%，单房变动成本从 ¥45 涨至 ¥{new_vc}",
        "severity": 2,
        "cost_rise_range": (20, 60),
        "check": "cost_spike",
    },
]


# ═══════════════════════════════════════════════════════════════
# 红蓝对抗引擎
# ═══════════════════════════════════════════════════════════════

class AdversarialEngine:
    """红蓝对抗价格决策验证引擎"""

    def __init__(self):
        self.attack_history = []

    def validate(self, proposal: dict, context: dict = None) -> dict:
        """对蓝队定价方案执行全维度红队攻击。

        Args:
          proposal: {
            "bar_price": float,         # 建议 BAR 价
            "base_price": float,        # 基准价
            "strategy": str,            # attack/defend/neutral
            "current_occ": float,       # 当前 OCC
            "current_gop_rate": float,  # 当前 GOP率
            "floor_price": float,       # 底价
            "competitor_avg_price": float,
          }
          context: 额外上下文（可选）

        Returns: {
          "verdict": "by" | "condition" | "block",
          "score": 0-100,               # 防御分
          "survived_attacks": int,
          "failed_attacks": list,
          "attack_results": list,
          "brake_conditions": list,     # 刹车条件
          "recommendation": str,
        }
        """
        if context is None:
            context = {}

        results = []
        for vector in ATTACK_VECTORS:
            result = self._execute_attack(vector, proposal, context)
            results.append(result)

        # 汇总
        survived = [r for r in results if r["survived"]]
        failed = [r for r in results if not r["survived"]]
        score = int((sum(r["score"] for r in results) / len(results)))

        # 判决
        if len(failed) >= 3:
            verdict = "block"
            rec = "定价方案在多维度攻击下失效（≥3项），需重新设计。降低 BAR 价至少 15% 或等待需求恢复。"
        elif len(failed) >= 1:
            verdict = "condition"
            brake = [f["brake_condition"] for f in failed]
            rec = f"方案条件通过，但需设置 {len(failed)} 项刹车条件。" + "；".join(brake)
        else:
            verdict = "by"
            rec = "方案通过红队验证，在所有攻击维度下均存活。"

        return {
            "verdict": verdict,
            "score": score,
            "survived_attacks": len(survived),
            "failed_attacks": len(failed),
            "failed_details": [f["attack_name"] for f in failed],
            "attack_results": results,
            "brake_conditions": [f["brake_condition"] for f in failed],
            "recommendation": rec,
            "verdict_card": self._build_verdict_card(verdict, results, proposal),
        }

    def _execute_attack(self, vector: dict, proposal: dict, context: dict) -> dict:
        """执行单个攻击向量。"""
        attack_id = vector["id"]

        if attack_id == "A_competitor":
            return self._attack_competitor(proposal, vector)
        elif attack_id == "B_demand_shock":
            return self._attack_demand_shock(proposal, vector)
        elif attack_id == "C_pace_mirage":
            return self._attack_pace_mirage(proposal, vector)
        elif attack_id == "D_channel_backfire":
            return self._attack_channel_backfire(proposal, vector)
        elif attack_id == "E_cost_spike":
            return self._attack_cost_spike(proposal, vector)
        else:
            return {"attack_id": attack_id, "survived": True, "score": 100,
                    "detail": "未知攻击向量", "attack_name": vector["name"],
                    "brake_condition": ""}

    # ── A: 竞对集体降价 ──

    def _attack_competitor(self, p: dict, v: dict) -> dict:
        bar = p.get("bar_price", 500)
        comp_avg = p.get("competitor_avg_price", 400)
        drop_pct = 20  # 取攻击范围中值

        # 攻击后竞对均价
        attacked_comp_avg = comp_avg * (1 - drop_pct / 100)
        premium_after = (bar - attacked_comp_avg) / attacked_comp_avg * 100

        if premium_after > 40:
            survived = False
            detail = (f"竞对集体降价 {drop_pct}% 后，自家溢价 {premium_after:.0f}%，"
                      f"预计 OCC 将跌至 45% 以下")
            brake = f"若竞对均价跌至 ¥{attacked_comp_avg:.0f}（-{drop_pct}%），48h 内启动紧急跟降 15%"
            score = 20
        elif premium_after > 25:
            survived = True
            detail = (f"竞对降价 {drop_pct}% 后溢价 {premium_after:.0f}%，偏高但品牌力可支撑")
            brake = f"若竞对再降 >5%，立即跟进"
            score = 60
        elif premium_after > 10:
            survived = True
            detail = f"竞对降价后溢价 {premium_after:.0f}%，在安全区间"
            brake = ""
            score = 85
        else:
            survived = True
            detail = f"竞对降价后溢价仅 {premium_after:.0f}%，竞争力充足"
            brake = ""
            score = 95

        return {
            "attack_id": v["id"],
            "attack_name": v["name"],
            "survived": survived,
            "score": score,
            "detail": detail,
            "brake_condition": brake,
            "attacked_comp_avg": round(attacked_comp_avg, 0),
            "premium_after_attack": round(premium_after, 1),
        }

    # ── B: 需求冲击 ──

    def _attack_demand_shock(self, p: dict, v: dict) -> dict:
        occ = p.get("current_occ", 65)
        gop_rate = p.get("current_gop_rate", 35)
        floor_price = p.get("floor_price", 399)
        bar = p.get("bar_price", 500)
        drop_pct = 30  # 需求降 30%

        shocked_occ = max(10, occ - drop_pct)

        if shocked_occ < 31.3:  # 运营保本点
            survived = False
            detail = (f"需求冲击 -{drop_pct}% 后 OCC={shocked_occ:.0f}%，"
                      f"低于运营保本 31.3%，日均亏损 ¥12,667")
            brake = (f"若 OCC 连续 3 天 <31%，触发紧急降价：BAR → max(¥{floor_price}, "
                     f"竞对最低价 × 0.9)")
            score = 15
        elif shocked_occ < 50:
            survived = False
            detail = (f"需求冲击 -{drop_pct}% 后 OCC={shocked_occ:.0f}%，"
                      f"GOP率将转负")
            brake = f"若 OCC <50% 持续 48h，自动降价 15%+ 启动 flash sale"
            score = 35
        elif shocked_occ < 67.2:  # 全成本保本
            survived = True
            detail = f"需求冲击后 OCC={shocked_occ:.0f}%，高于运营保本但低于全成本保本"
            brake = f"若 OCC 跌破 67.2%，暂停非必要支出，重新评估价格"
            score = 60
        else:
            survived = True
            detail = f"需求冲击后 OCC={shocked_occ:.0f}%，仍在全成本保本之上"
            brake = ""
            score = 90

        shock_events = ["暴雨/地震/景区关闭", "团队大规模取消", "OTA 负面舆情爆发"]
        return {
            "attack_id": v["id"],
            "attack_name": v["name"],
            "survived": survived,
            "score": score,
            "detail": detail,
            "brake_condition": brake,
            "shocked_occ": round(shocked_occ, 1),
            "example_shocks": shock_events,
        }

    # ── C: Pace 幻象 ──

    def _attack_pace_mirage(self, p: dict, v: dict) -> dict:
        occ = p.get("current_occ", 65)
        pace_dev = p.get("pace_deviation", 0)
        cancel_rate = 25  # 假设 25% 取消率

        # 虚高 Pace → 实际入住远低于预期
        true_occ = occ * (1 - cancel_rate / 100)

        if pace_dev > 20 and true_occ < 55:
            survived = False
            detail = (f"Pace +{pace_dev}% 虚高，{cancel_rate}% 集中取消后真实 OCC 仅 {true_occ:.0f}%")
            brake = "Pace > 同期 20% 时，按实际入住率（×70%）估算保守 OCC，据此定价"
            score = 25
        elif pace_dev > 10 and true_occ < 65:
            survived = True
            detail = f"Pace 偏高但取消后 OCC={true_occ:.0f}% 仍可接受"
            brake = "若取消率 >30%，下调 BAR 价 8%"
            score = 65
        elif true_occ < 50:
            survived = False
            detail = f"取消后真实 OCC 仅 {true_occ:.0f}%，跌破保本线"
            brake = "设置 14 天取消政策（不可免费取消），降低取消率"
            score = 30
        else:
            survived = True
            detail = f"取消后 OCC={true_occ:.0f}%，方案稳健"
            brake = ""
            score = 85

        return {
            "attack_id": v["id"],
            "attack_name": v["name"],
            "survived": survived,
            "score": score,
            "detail": detail,
            "brake_condition": brake,
            "true_occ_after_cancel": round(true_occ, 1),
        }

    # ── D: 渠道反噬 ──

    def _attack_channel_backfire(self, p: dict, v: dict) -> dict:
        ota_ratio = p.get("ota_ratio", 55)
        bar = p.get("bar_price", 500)
        new_commission = 20  # 佣金从 15% → 20%

        # 佣金涨 5pp 的净收入损失
        revenue_loss_per_ota_room = bar * (new_commission / 100 - 0.15)
        ota_rooms = 170 * (p.get("current_occ", 65) / 100) * (ota_ratio / 100)
        total_loss = ota_rooms * revenue_loss_per_ota_room

        if total_loss > 5000:  # 损失 >¥5000/天
            survived = False
            detail = (f"携程佣金涨至 {new_commission}% 后，OTA 渠道每日净损失 ¥{total_loss:,.0f}")
            brake = "启动直销补贴计划（微信小程序立减 ¥30），目标 14 天内直销占比 +10pp"
            score = 30
        elif total_loss > 2000:
            survived = True
            detail = f"佣金涨至 {new_commission}%，日损失 ¥{total_loss:,.0f}，可接受"
            brake = "若直销占比未在 30 天内提升 5pp，需重新评估 OTA 依赖度"
            score = 65
        else:
            survived = True
            detail = f"佣金上涨影响可控（日损失 ¥{total_loss:,.0f}）"
            brake = ""
            score = 85

        return {
            "attack_id": v["id"],
            "attack_name": v["name"],
            "survived": survived,
            "score": score,
            "detail": detail,
            "brake_condition": brake,
            "daily_loss": round(total_loss, 0),
        }

    # ── E: 成本突增 ──

    def _attack_cost_spike(self, p: dict, v: dict) -> dict:
        gop_rate = p.get("current_gop_rate", 35)
        bar = p.get("bar_price", 500)
        cost_rise = 40  # 成本涨 40%

        variable_cost_new = 45 * (1 + cost_rise / 100)  # ¥63
        daily_fixed_new = 12667 * (1 + cost_rise / 100 * 0.5)  # 人工涨 20%

        # 新 GOP 估算（简化）
        contribution_new = bar - variable_cost_new
        occ = p.get("current_occ", 65)
        rooms = 170 * occ / 100
        gop_new = rooms * contribution_new - daily_fixed_new

        if gop_new < 0:
            survived = False
            detail = (f"成本涨 {cost_rise}%，单房变动成本 ¥{variable_cost_new:.0f}，"
                      f"当前 OCC 下 GOP 转负")
            brake = "启动成本紧缩：冻结非必要支出、审查能耗、交叉培训减少外包"
            score = 15
        elif gop_new < 5000:
            survived = False
            detail = f"成本涨 {cost_rise}% 后 GOP 仅 ¥{gop_new:,.0f}，利润侵蚀严重"
            brake = "连续 3 天 GOP<¥5,000 触发全面成本审查"
            score = 35
        else:
            survived = True
            detail = f"成本涨 {cost_rise}% 后 GOP=¥{gop_new:,.0f}，方案仍有利润空间"
            brake = ""
            score = 75

        return {
            "attack_id": v["id"],
            "attack_name": v["name"],
            "survived": survived,
            "score": score,
            "detail": detail,
            "brake_condition": brake,
            "new_variable_cost": round(variable_cost_new, 0),
            "gop_after_shock": round(gop_new, 0),
        }

    # ── 裁决卡 ──

    def _build_verdict_card(self, verdict: str, results: list,
                            proposal: dict) -> str:
        """生成中文裁决卡文本。"""
        bar = proposal.get("bar_price", "?")
        strat = proposal.get("strategy", "auto")
        failed = [r for r in results if not r["survived"]]

        card = [
            "═" * 55,
            f"  {'🟢 通过' if verdict == 'by' else ('🟡 条件通过' if verdict == 'condition' else '🔴 否决')}"
            f"  |  BAR ¥{bar}  |  策略: {strat}",
            "═" * 55,
        ]

        for r in results:
            icon = "✅" if r["survived"] else "❌"
            card.append(f"  {icon} {r['attack_name']}: {r['detail']}")

        if failed:
            card.append("")
            card.append(f"  ⚠ 刹车条件（{len(failed)} 项）：")
            for i, f in enumerate(failed, 1):
                card.append(f"  {i}. {f['brake_condition']}")

        card.append("═" * 55)
        return "\n".join(card)


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def validate_pricing(bar_price: float, base_price: float = 600,
                     current_occ: float = 65, current_gop_rate: float = 35,
                     competitor_avg_price: float = 400,
                     strategy: str = "auto",
                     floor_price: float = 399,
                     **kwargs) -> dict:
    """快速验证一个定价方案。"""
    engine = AdversarialEngine()
    proposal = {
        "bar_price": bar_price,
        "base_price": base_price,
        "strategy": strategy,
        "current_occ": current_occ,
        "current_gop_rate": current_gop_rate,
        "floor_price": floor_price,
        "competitor_avg_price": competitor_avg_price,
    }
    proposal.update(kwargs)
    return engine.validate(proposal)


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = AdversarialEngine()

    print("=" * 60)
    print("  红蓝对抗验证引擎")
    print("=" * 60)

    # 场景 1: 激进提价
    print("\n  ── 场景 1: 激进提价 BAR ¥800（OCC 82%）──")
    r1 = validate_pricing(
        bar_price=800, base_price=670,
        current_occ=82, current_gop_rate=42,
        competitor_avg_price=395, strategy="defend",
    )
    print(r1["verdict_card"])
    print(f"  裁决: {r1['verdict']} | 防御分: {r1['score']}/100 | "
          f"存活: {r1['survived_attacks']}/{len(ATTACK_VECTORS)}")

    # 场景 2: 降价抢量
    print("\n  ── 场景 2: 淡季降价 BAR ¥420（OCC 45%）──")
    r2 = validate_pricing(
        bar_price=420, base_price=500,
        current_occ=45, current_gop_rate=18,
        competitor_avg_price=350, strategy="attack",
    )
    print(r2["verdict_card"])
    print(f"  裁决: {r2['verdict']} | 防御分: {r2['score']}/100 | "
          f"存活: {r2['survived_attacks']}/{len(ATTACK_VECTORS)}")

    # 场景 3: 适中定价
    print("\n  ── 场景 3: 适中 BAR ¥610（OCC 65%）──")
    r3 = validate_pricing(
        bar_price=610, base_price=580,
        current_occ=65, current_gop_rate=32,
        competitor_avg_price=395, strategy="auto",
    )
    print(r3["verdict_card"])
    print(f"  裁决: {r3['verdict']} | 防御分: {r3['score']}/100 | "
          f"存活: {r3['survived_attacks']}/{len(ATTACK_VECTORS)}")
