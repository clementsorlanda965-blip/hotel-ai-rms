"""
decision_card_builder.py —— 决策卡片生成器 v1.0

生成 GMA（总经理助理）风格的一页式决策卡片，包含：
  1. 今日核心数字（OCC/ADR/RevPAR/GOP率）
  2. BAR 价建议 + 进攻/防守信号
  3. 竞争指数（MPI/ARI/RGI）
  4. 红蓝对抗裁决
  5. 关键风险提示
  6. 24h 内执行行动项

输出格式：
  - Markdown 文本（飞书消息/日报）
  - Dict（API JSON 响应）
  - HTML 卡片片段（仪表盘嵌入）

用法：
  from decision_card_builder import CardBuilder
  builder = CardBuilder()
  card = builder.build(date.today())
  print(builder.to_markdown(card))

参考：
  - Duetto GameChanger 决策卡片 UX
  - IDeaS G3 RMS Daily Pickup Report
  - Cornell 酒店管理学院：收益管理沟通最佳实践
"""

import json
from datetime import date, datetime
from typing import Any

# 延迟导入避免循环依赖
def _import_modules():
    from bar_price_engine import calculate_daily_bar, generate_bar_calendar
    from ota_radar import CompetitorRadar
    from red_blue_adversarial import validate_pricing
    from usali_engine import USALIEngine
    return calculate_daily_bar, generate_bar_calendar, CompetitorRadar, validate_pricing, USALIEngine


# ═══════════════════════════════════════════════════════════════
# 决策卡片生成器
# ═══════════════════════════════════════════════════════════════

class CardBuilder:
    """一站式决策卡片生成器"""

    def __init__(self):
        self._modules = None

    def _ensure_modules(self):
        if self._modules is None:
            self._modules = _import_modules()
        return self._modules

    def build(self, target_date: date = None) -> dict:
        """构建完整决策卡片。

        Returns: 包含所有决策维度数据的 dict
        """
        if target_date is None:
            target_date = date.today()

        calc_bar, _, CompetitorRadar, validate_pricing, USALIEngine = self._ensure_modules()

        # 1. BAR 价建议
        bar_result = calc_bar(target_date)

        # 2. 竞争指数
        radar = CompetitorRadar()
        comp_indices = radar.calculate(target_date)
        health = radar.health_dashboard()

        # 3. 财务测算
        engine = USALIEngine()
        pnl = engine.daily_pnl(target_date)

        # 4. 红蓝对抗
        comp_avg = comp_indices["comp_set"]["adr"]
        adversarial = validate_pricing(
            bar_price=bar_result["recommended_bar"],
            base_price=bar_result["factors"]["base_price"],
            current_occ=pnl["occ"],
            current_gop_rate=pnl["gop_rate"],
            competitor_avg_price=comp_avg,
            strategy=bar_result["attack_defense"],
        )

        # 5. 信号灯
        signals = []
        # RGI
        rgi = comp_indices["rgi"]
        if rgi >= 110:
            signals.append("🟢 RGI 优秀")
        elif rgi >= 95:
            signals.append("🟢 RGI 健康")
        elif rgi >= 85:
            signals.append("🟡 RGI 需关注")
        else:
            signals.append("🔴 RGI 预警")

        # GOP
        gop_rate = pnl["gop_rate"]
        if gop_rate >= 38:
            signals.append("🟢 GOP率达标")
        elif gop_rate >= 30:
            signals.append("🟡 GOP率偏低")
        else:
            signals.append("🔴 GOP率预警")

        # 保本
        if pnl["occ"] < 31.3:
            signals.append("🔴 低于运营保本点")
        elif pnl["occ"] < 67.2:
            signals.append("🟡 介于运营/全成本保本之间")
        else:
            signals.append("🟢 超过全成本保本")

        # 倒挂
        if comp_indices.get("price_inversions"):
            signals.append("🔴 价格倒挂")
        else:
            signals.append("🟢 渠道价格一致")

        # 组装卡片
        card = {
            "meta": {
                "date": target_date.strftime("%Y-%m-%d"),
                "day_of_week": ["周一","周二","周三","周四","周五","周六","周日"][target_date.weekday()],
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "version": "1.0",
            },
            "bar_pricing": bar_result,
            "competition": {
                "mpi": comp_indices["mpi"],
                "ari": comp_indices["ari"],
                "rgi": comp_indices["rgi"],
                "verdict": comp_indices["verdict"],
                "comp_prices": comp_indices["comp_set"].get("hotels_priced", []),
            },
            "financials": {
                "occ": pnl["occ"],
                "adr": pnl["adr"],
                "revpar": round(pnl["adr"] * pnl["occ"] / 100, 0),
                "gop": pnl["gop"],
                "gop_rate": pnl["gop_rate"],
                "goppar": pnl["goppar"],
                "breakeven_status": (
                    "超全成本保本" if pnl["occ"] >= 67.2
                    else ("超运营保本" if pnl["occ"] >= 31.3 else "低于保本点")
                ),
            },
            "adversarial": {
                "verdict": adversarial["verdict"],
                "score": adversarial["score"],
                "brake_conditions": adversarial["brake_conditions"],
            },
            "signals": signals,
            "actions": self._build_actions(bar_result, comp_indices, pnl, adversarial),
        }

        return card

    def _build_actions(self, bar: dict, comp: dict, pnl: dict, adv: dict) -> list[dict]:
        """生成 24h 内执行行动项。"""
        actions = []

        # 定价行动
        if bar["attack_defense"] == "attack":
            actions.append({
                "priority": 1, "owner": "收益经理",
                "action": f"执行进攻定价：BAR ¥{bar['recommended_bar']}，"
                          f"在携程/美团同步调价，关闭早鸟折扣",
                "deadline": "今天 10:00",
            })
        elif bar["attack_defense"] == "defend":
            actions.append({
                "priority": 1, "owner": "收益经理",
                "action": f"执行防守定价：BAR ¥{bar['recommended_bar']}，"
                          f"监控竞对反应，如有竞对降价 >10% 立即汇报",
                "deadline": "今天 10:00",
            })
        else:
            actions.append({
                "priority": 2, "owner": "收益经理",
                "action": f"维持现价 BAR ¥{bar['recommended_bar']}，"
                          f"下午 15:00 二次检查 Pace 变化",
                "deadline": "今天 15:00",
            })

        # 渠道行动
        if comp.get("price_inversions"):
            actions.append({
                "priority": 1, "owner": "市场营销",
                "action": f"价格倒挂修复：{comp['price_inversions']}，"
                          f"联系对应 OTA 业务经理调整",
                "deadline": "今天 12:00",
            })

        # 财务行动
        if pnl["occ"] < 31.3:
            actions.append({
                "priority": 1, "owner": "GM",
                "action": "OCC 低于运营保本点，冻结非必要支出，启动全员营销",
                "deadline": "今天",
            })

        # 刹车条件（红蓝对抗产出）
        for i, brake in enumerate(adv.get("brake_conditions", [])[:3]):
            actions.append({
                "priority": 3, "owner": "收益经理",
                "action": f"刹车条件 #{i+1}：{brake}",
                "deadline": "持续监控",
            })

        return sorted(actions, key=lambda x: (x["priority"], x["deadline"]))

    # ── 格式化输出 ──

    def to_markdown(self, card: dict) -> str:
        """输出 Markdown 格式（飞书消息/日报）。"""
        m = card["meta"]
        bar = card["bar_pricing"]
        comp = card["competition"]
        fin = card["financials"]
        adv = card["adversarial"]

        verdict_emoji = {"by": "🟢", "condition": "🟡", "block": "🔴"}
        ad_emoji = {"attack": "🟢 进攻", "defend": "🔴 防守", "neutral": "🟡 平价"}

        lines = [
            f"## 📊 九寨沟诺富特 · 收益决策日报",
            f"**{m['date']} {m['day_of_week']}** | 生成时间 {m['generated_at']}",
            "",
            "### 🎯 今日建议 BAR 价",
            f"| 项目 | 数值 |",
            f"|------|------|",
            f"| **建议 BAR 价** | **¥{bar['recommended_bar']}** |",
            f"| 定价信号 | {ad_emoji.get(bar['attack_defense'], bar['attack_defense'])} |",
            f"| 信心度 | {bar['confidence']:.0%} |",
            f"| 基准价 | ¥{bar['factors']['base_price']:.0f} |",
            f"| 季节系数 | {bar['factors']['season_coefficient']:.3f} |",
            f"| 竞对系数 | {bar['factors']['competitor_coefficient']:.3f} |",
            "",
            "### 📡 竞争雷达",
            f"| 指数 | 数值 | 判定 |",
            f"|------|------|------|",
            f"| MPI | {comp['mpi']} | {'🟢' if comp['mpi']>=100 else '🟡'} |",
            f"| ARI | {comp['ari']} | {'🟢' if 95<=comp['ari']<=110 else '🟡'} |",
            f"| RGI | {comp['rgi']} | {'🟢' if comp['rgi']>=100 else '🔴'} |",
            f"| 综合 | {comp['verdict']} | — |",
            "",
            "### 💰 财务快照",
            f"| 指标 | 数值 | 状态 |",
            f"|------|------|------|",
            f"| OCC | {fin['occ']:.1f}% | {fin['breakeven_status']} |",
            f"| ADR | ¥{fin['adr']:.0f} | — |",
            f"| GOP | ¥{fin['gop']:,.0f} | — |",
            f"| GOP率 | {fin['gop_rate']:.1f}% | {'✅ ≥38%' if fin['gop_rate']>=38 else '⚠️ <38%'} |",
            f"| GOPPAR | ¥{fin['goppar']:.0f} | — |",
            "",
            "### ⚔️ 红蓝对抗",
            f"| 裁决 | 防御分 | 刹车条件 |",
            f"|------|--------|----------|",
            f"| {verdict_emoji.get(adv['verdict'], '?')} {adv['verdict']} | {adv['score']}/100 | {len(adv.get('brake_conditions', []))} 项 |",
            "",
            "### 📋 今日行动项",
        ]

        for a in card.get("actions", [])[:6]:
            prio = "🔴" if a["priority"] == 1 else ("🟡" if a["priority"] == 2 else "⚪")
            lines.append(f"- {prio} **{a['owner']}**：{a['action']}（{a['deadline']}）")

        # 解释
        lines.append("")
        lines.append("### 💬 定价逻辑")
        lines.append(bar.get("explanation", "—"))

        # 信号汇总
        lines.append("")
        lines.append("### 🚦 信号灯")
        for sig in card.get("signals", []):
            lines.append(f"- {sig}")

        return "\n".join(lines)

    def to_html_card(self, card: dict) -> str:
        """输出 HTML 卡片片段（仪表盘嵌入）。"""
        m = card["meta"]
        bar = card["bar_pricing"]
        comp = card["competition"]
        fin = card["financials"]
        adv = card["adversarial"]

        verdict_colors = {"by": "#22c55e", "condition": "#eab308", "block": "#ef4444"}
        ad_colors = {"attack": "#22c55e", "defend": "#ef4444", "neutral": "#eab308"}
        ad_labels = {"attack": "进攻", "defend": "防守", "neutral": "平价"}

        return f"""<div class="decision-card" style="border:1px solid #e5e7eb;border-radius:12px;padding:24px;max-width:480px;font-family:system-ui">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h2 style="margin:0;font-size:18px">📊 收益决策日报</h2>
    <span style="color:#6b7280;font-size:13px">{m['date']} {m['day_of_week']}</span>
  </div>

  <div style="background:{ad_colors.get(bar['attack_defense'], '#eab308')}15;border-left:4px solid {ad_colors.get(bar['attack_defense'], '#eab308')};padding:12px 16px;border-radius:8px;margin-bottom:16px">
    <div style="font-size:12px;color:#6b7280">建议 BAR 价</div>
    <div style="font-size:32px;font-weight:700">¥{bar['recommended_bar']}</div>
    <div style="font-size:13px;color:#6b7280">{ad_labels.get(bar['attack_defense'], '?')} · 信心度 {bar['confidence']:.0%}</div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:16px">
    <div style="background:#f3f4f6;padding:8px;border-radius:6px;text-align:center">
      <div style="font-size:11px;color:#6b7280">MPI</div>
      <div style="font-size:18px;font-weight:600">{comp['mpi']}</div>
    </div>
    <div style="background:#f3f4f6;padding:8px;border-radius:6px;text-align:center">
      <div style="font-size:11px;color:#6b7280">ARI</div>
      <div style="font-size:18px;font-weight:600">{comp['ari']}</div>
    </div>
    <div style="background:#f3f4f6;padding:8px;border-radius:6px;text-align:center">
      <div style="font-size:11px;color:#6b7280">RGI</div>
      <div style="font-size:18px;font-weight:600">{comp['rgi']}</div>
    </div>
  </div>

  <div style="background:#f9fafb;padding:12px;border-radius:8px;margin-bottom:16px">
    <div style="display:flex;justify-content:space-between">
      <span>OCC {fin['occ']:.1f}%</span>
      <span>ADR ¥{fin['adr']:.0f}</span>
      <span>GOP率 {fin['gop_rate']:.1f}%</span>
    </div>
  </div>

  <div style="border-top:1px solid #e5e7eb;padding-top:12px">
    <div style="font-size:13px;font-weight:600;margin-bottom:4px">
      <span style="color:{verdict_colors.get(adv['verdict'], '#6b7280')}">{{
        '🟢 通过' if adv['verdict']=='by' else ('🟡 条件通过' if adv['verdict']=='condition' else '🔴 否决')
      }}</span>
      <span style="color:#6b7280;font-size:12px"> · 红蓝对抗 {adv['score']}分</span>
    </div>
    <div style="font-size:12px;color:#6b7280;line-height:1.6">{bar.get('explanation', '')}</div>
  </div>
</div>"""

    def to_json(self, card: dict) -> str:
        """输出 JSON 格式（API 响应）。"""
        return json.dumps(card, ensure_ascii=False, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    builder = CardBuilder()
    card = builder.build()

    print("═" * 60)
    print("  决策卡片生成器")
    print("═" * 60)

    # Markdown
    md = builder.to_markdown(card)
    print(md)

    print("\n" + "═" * 60)
    print("  JSON (摘要)")
    print("═" * 60)
    summary = {
        "date": card["meta"]["date"],
        "bar": card["bar_pricing"]["recommended_bar"],
        "rgi": card["competition"]["rgi"],
        "gop_rate": card["financials"]["gop_rate"],
        "adversarial_verdict": card["adversarial"]["verdict"],
        "signals": card["signals"],
        "actions_count": len(card["actions"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
