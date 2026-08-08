"""
usali_engine.py —— USALI 财务测算引擎 v1.0

USALI (Uniform System of Accounts for the Lodging Industry) 第 11 版标准：
酒店行业统一的财务报告体系，按部门核算收入/成本/利润。

核心输出：
  1. GOP (Gross Operating Profit)     — 经营毛利
  2. GOP率 (GOP / 总收入)            — 核心盈利效率指标
  3. Flow-Through                      — 增量收入 → GOP 转化率
  4. EBITDA                            — 息税折旧摊销前利润
  5. GOPPAR (GOP Per Available Room)   — 每间可卖房经营毛利
  6. 部门损益（客房/餐饮/其他/行政/销售/维护/能源）
  7. 保本点分析（运营保本 + 全成本保本）
  8. 现金流预测（30天滚动）

诺富特九寨沟财务参数（2025 审计值）：
  - 月固定成本：¥380,000（含人工/租金/折旧/保险）
  - 单房变动成本：¥45（布草/洗浴用品/水电/迷你吧）
  - 运营保本 OCC：31.3%
  - 全成本保本 OCC：67.2%
  - 目标 GOP率：38%

用法：
  from usali_engine import USALIEngine
  engine = USALIEngine()
  pnl = engine.daily_pnl(date.today(), occ=65, adr=450)
  print(f"GOP: ¥{pnl['gop']:.0f} | GOP率: {pnl['gop_rate']:.1f}%")

参考：
  - AHLA USALI 11th Edition
  - 诺富特 2025 年审计财务数据
  - Obsidian: 诺富特财务模型 (L4)
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "rms.db"

from config import (
    NOVOTEL_FINANCIALS, TOTAL_ROOMS, FLOOR_PRICE, SELF_HOTEL_NAME,
)

# ═══════════════════════════════════════════════════════════════
# 财务参数
# ═══════════════════════════════════════════════════════════════

FC = NOVOTEL_FINANCIALS
DAILY_FIXED_COST = FC["monthly_fixed_cost"] / 30  # ¥12,667/天
VARIABLE_COST_PER_ROOM = FC["avg_variable_cost_per_room"]  # ¥45
TARGET_GOP_RATE = FC["target_gop_rate"]  # 38%
BREAKEVEN_OCC_OPERATING = FC["breakeven_occ_operating"]  # 31.3%
BREAKEVEN_OCC_FULL = FC["breakeven_occ_full"]  # 67.2%

# 部门收入分配（行业基准 + 诺富特实际校准）
DEPT_REVENUE_SPLIT = {
    "rooms": 0.68,       # 客房收入占比 68%
    "fb": 0.22,           # 餐饮收入 22%
    "other": 0.10,        # 其他（洗衣/商务中心/停车/场租）10%
}

# 部门成本率（占各部门收入的 %）
DEPT_COST_RATIOS = {
    "rooms": 0.22,        # 客房成本率 22%（人工+布草+消耗品）
    "fb": 0.58,            # 餐饮成本率 58%（食材+人工）
    "other": 0.35,         # 其他成本率 35%
    "admin_general": 0.08, # 行政管理费占总收入 8%
    "sales_marketing": 0.06, # 销售营销费占总收入 6%
    "maintenance": 0.04,   # 维护费占总收入 4%
    "utilities": 0.05,     # 能源费占总收入 5%
}

# 折旧摊销（月度）
MONTHLY_DEPRECIATION = 85000  # ¥
DAILY_DEPRECIATION = MONTHLY_DEPRECIATION / 30


# ═══════════════════════════════════════════════════════════════
# USALI 损益计算引擎
# ═══════════════════════════════════════════════════════════════

class USALIEngine:
    """USALI 标准损益引擎"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)

    # ── 单日损益 ──

    def daily_pnl(self, target_date: date = None, occ: float = None,
                  adr: float = None, fb_revenue: float = None,
                  other_revenue: float = None, room_sold: int = None) -> dict:
        """计算单日 USALI 损益表。

        Args:
            target_date: 日期
            occ: 出租率 %
            adr: 平均房价 ¥
            fb_revenue: 餐饮收入（None=自动估算）
            other_revenue: 其他收入（None=自动估算）
            room_sold: 已售房间数（None=自动计算）

        Returns: 完整损益表 dict
        """
        if target_date is None:
            target_date = date.today()

        # 优先用传入值，否则从 DB 读取
        if occ is None or adr is None:
            db_metrics = self._get_db_metrics(target_date)
            if occ is None:
                occ = db_metrics.get("occ", 65)
            if adr is None:
                adr = db_metrics.get("adr", 450)

        if room_sold is None:
            room_sold = int(occ / 100 * TOTAL_ROOMS)

        # 客房收入
        room_revenue = adr * room_sold

        # 总收入（业务反转法：从客房收入反推总收入和餐饮收入）
        total_revenue = room_revenue / DEPT_REVENUE_SPLIT["rooms"]
        if fb_revenue is None:
            fb_revenue = total_revenue * DEPT_REVENUE_SPLIT["fb"]
        if other_revenue is None:
            other_revenue = total_revenue * DEPT_REVENUE_SPLIT["other"]

        # ── 部门损益 ──
        dept_pnl = {}

        # 客房部
        room_cost = room_revenue * DEPT_COST_RATIOS["rooms"] + room_sold * VARIABLE_COST_PER_ROOM
        room_gop = room_revenue - room_cost
        dept_pnl["rooms"] = {"revenue": room_revenue, "cost": room_cost, "gop": room_gop,
                             "gop_rate": room_gop / room_revenue * 100 if room_revenue > 0 else 0}

        # 餐饮部
        fb_cost = fb_revenue * DEPT_COST_RATIOS["fb"]
        fb_gop = fb_revenue - fb_cost
        dept_pnl["fb"] = {"revenue": fb_revenue, "cost": fb_cost, "gop": fb_gop,
                          "gop_rate": fb_gop / fb_revenue * 100 if fb_revenue > 0 else 0}

        # 其他运营部
        other_cost = other_revenue * DEPT_COST_RATIOS["other"]
        other_gop = other_revenue - other_cost
        dept_pnl["other"] = {"revenue": other_revenue, "cost": other_cost, "gop": other_gop,
                            "gop_rate": other_gop / other_revenue * 100 if other_revenue > 0 else 0}

        # ── 部门利润合计（Total Departmental Profit）──
        total_dept_revenue = room_revenue + fb_revenue + other_revenue
        total_dept_cost = room_cost + fb_cost + other_cost
        total_dept_profit = total_dept_revenue - total_dept_cost

        # ── 未分配费用 ──
        admin_cost = total_dept_revenue * DEPT_COST_RATIOS["admin_general"]
        sales_cost = total_dept_revenue * DEPT_COST_RATIOS["sales_marketing"]
        maint_cost = total_dept_revenue * DEPT_COST_RATIOS["maintenance"]
        util_cost = total_dept_revenue * DEPT_COST_RATIOS["utilities"]
        total_undistributed = admin_cost + sales_cost + maint_cost + util_cost + DAILY_FIXED_COST

        # ── GOP ──
        gop = total_dept_profit - total_undistributed
        gop_rate = gop / total_dept_revenue * 100 if total_dept_revenue > 0 else 0

        # ── EBITDA ──
        ebitda = gop - DAILY_DEPRECIATION

        # ── GOPPAR ──
        goppar = gop / TOTAL_ROOMS

        # ── 单房边际贡献 ──
        contribution_per_room = adr - VARIABLE_COST_PER_ROOM

        # ── 保本点 ──
        breakeven_rooms_operating = DAILY_FIXED_COST / contribution_per_room if contribution_per_room > 0 else float("inf")
        breakeven_occ_operating = breakeven_rooms_operating / TOTAL_ROOMS * 100

        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "occ": occ,
            "adr": adr,
            "room_sold": room_sold,
            "room_revenue": round(room_revenue, 0),
            "fb_revenue": round(fb_revenue, 0),
            "other_revenue": round(other_revenue, 0),
            "total_revenue": round(total_dept_revenue, 0),
            "total_dept_profit": round(total_dept_profit, 0),
            "total_undistributed": round(total_undistributed, 0),
            "gop": round(gop, 0),
            "gop_rate": round(gop_rate, 1),
            "ebitda": round(ebitda, 0),
            "goppar": round(goppar, 0),
            "contribution_per_room": round(contribution_per_room, 0),
            "breakeven_occ_operating": round(breakeven_occ_operating, 1),
            "breakeven_occ_full": BREAKEVEN_OCC_FULL * 100,
            "dept_pnl": dept_pnl,
        }

    # ── Flow-Through 分析 ──

    def flow_through(self, revenue_current: float, revenue_prior: float,
                     gop_current: float, gop_prior: float) -> dict:
        """Flow-Through = ΔGOP / ΔRevenue × 100

        理想 Flow-Through：
          旺季（Rev 增长）：> 55%（优秀）/ 40-55%（良好）/ < 40%（需改善）
          淡季（Rev 下降）：> 35%（优秀）/ 25-35%（良好）/ < 25%（需改善）

        即：每多挣 ¥100 收入，至少 ¥40 转化为 GOP。
        """
        delta_rev = revenue_current - revenue_prior
        delta_gop = gop_current - gop_prior

        if abs(delta_rev) < 1:
            return {"flow_through": None, "interpretation": "收入无明显变化", "delta_rev": 0, "delta_gop": 0}

        ft = delta_gop / delta_rev * 100

        if delta_rev > 0:
            if ft >= 55:
                interp = f"优秀（{ft:.0f}%）— 增量收入高效转化为利润"
            elif ft >= 40:
                interp = f"良好（{ft:.0f}%）— 增量收入合理转化"
            else:
                interp = f"需改善（{ft:.0f}%）— 增量收入转化不足，检查变动成本"
        else:
            if ft >= 35:
                interp = f"优秀（{ft:.0f}%）— 收入下降时有效控制成本"
            elif ft >= 25:
                interp = f"良好（{ft:.0f}%）— 成本控制可接受"
            else:
                interp = f"需关注（{ft:.0f}%）— 收入下降但成本未同比例缩减"

        return {
            "flow_through": round(ft, 1),
            "delta_revenue": round(delta_rev, 0),
            "delta_gop": round(delta_gop, 0),
            "interpretation": interp,
        }

    # ── GOP 滚动预测 ──

    def rolling_forecast(self, days: int = 30, base_occ: float = None,
                         base_adr: float = None) -> pd.DataFrame:
        """未来 N 天 GOP 滚动预测（基于当前 BAR 价 + 预测 OCC）。

        每天计算：客房收入 → 总收入 → GOP → GOPPAR → 累积 GOP
        """
        today = date.today()
        if base_occ is None or base_adr is None:
            db_m = self._get_db_metrics(today)
            base_occ = base_occ or db_m.get("occ", 65)
            base_adr = base_adr or db_m.get("adr", 450)

        from config import SEASON_FACTORS

        rows = []
        cum_gop = 0
        for i in range(days):
            d = today + timedelta(days=i)
            season = SEASON_FACTORS.get(d.month, 1.0)
            # 预测逻辑：ADR按季节调整（限制在基准价±30%），OCC也限制在合理范围
            forecast_adr = base_adr * max(0.80, min(1.20, season))
            # OCC 随季节浮动，淡季偏低旺季偏高，但都限制在 35-92% 合理范围
            occ_season_effect = (season - 1.0) * 25  # season 1.35 → +8.75pp OCC
            forecast_occ = min(92, max(35, base_occ + occ_season_effect))

            pnl = self.daily_pnl(d, occ=forecast_occ, adr=forecast_adr)
            cum_gop += pnl["gop"]

            dow = ["一","二","三","四","五","六","日"][d.weekday()]
            rows.append({
                "日期": d,
                "星期": dow,
                "预测OCC": round(forecast_occ, 1),
                "预测ADR": round(forecast_adr, 0),
                "客房收入": pnl["room_revenue"],
                "总收入": pnl["total_revenue"],
                "GOP": pnl["gop"],
                "GOP率": pnl["gop_rate"],
                "累积GOP": round(cum_gop, 0),
                "保本状态": "✅" if pnl["gop"] > 0 else "🔴",
            })

        return pd.DataFrame(rows)

    # ── 数据库读取辅助 ──

    def _get_db_metrics(self, target_date: date) -> dict:
        """从 daily_metrics 读取最新数据。"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT occ, adr, revpar, gop_rate, room_revenue,
                       total_revenue, total_cost, fb_revenue, room_sold
                FROM daily_metrics
                WHERE hotel_id = 1 AND date <= ?
                ORDER BY date DESC LIMIT 1
            """, (target_date.strftime("%Y-%m-%d"),)).fetchone()
            conn.close()
            return dict(row) if row else {}
        except Exception:
            return {}

    # ── 终端报告 ──

    def print_pnl(self, pnl: dict):
        """格式化打印单日损益表。"""
        print("=" * 55)
        print(f"  📊 USALI 损益表 — {pnl['date']}")
        print("=" * 55)
        print(f"  OCC: {pnl['occ']:.1f}%  |  ADR: ¥{pnl['adr']:.0f}  |  售房: {pnl['room_sold']} 间")
        print()
        print(f"  {'部门':<16s} {'收入':>10s} {'成本':>10s} {'利润':>10s} {'利润率':>8s}")
        print(f"  {'-'*55}")
        for dept_name, dept in pnl["dept_pnl"].items():
            label = {"rooms": "客房部", "fb": "餐饮部", "other": "其他运营部"}.get(dept_name, dept_name)
            print(f"  {label:<16s} ¥{dept['revenue']:>9,.0f} ¥{dept['cost']:>9,.0f} "
                  f"¥{dept['gop']:>9,.0f} {dept['gop_rate']:>7.1f}%")
        print(f"  {'-'*55}")
        print(f"  {'部门利润合计':<16s} {'':>10s} {'':>10s} ¥{pnl['total_dept_profit']:>9,.0f}")
        print(f"  {'未分配费用':<16s} {'':>10s} {'':>10s} ¥{pnl['total_undistributed']:>9,.0f}")
        print(f"  {'─'*55}")
        print(f"  GOP: ¥{pnl['gop']:>9,.0f}  |  GOP率: {pnl['gop_rate']:.1f}%  |  "
              f"GOPPAR: ¥{pnl['goppar']:.0f}")
        print(f"  EBITDA: ¥{pnl['ebitda']:>7,.0f}  |  单房边际贡献: ¥{pnl['contribution_per_room']:.0f}")
        print(f"  运营保本: {pnl['breakeven_occ_operating']:.1f}% OCC  |  "
              f"全成本保本: {pnl['breakeven_occ_full']:.1f}% OCC")


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def daily_pnl(occ: float = 65, adr: float = 450, **kwargs) -> dict:
    """快捷单日损益。"""
    engine = USALIEngine()
    return engine.daily_pnl(occ=occ, adr=adr, **kwargs)


def compare_scenarios(scenario_a: dict, scenario_b: dict) -> dict:
    """比较两个定价场景的财务结果。

    Args:
        scenario_a/b: {"label": "涨价10%", "occ": 75, "adr": 770}
    Returns: 对比表
    """
    engine = USALIEngine()
    pnl_a = engine.daily_pnl(occ=scenario_a["occ"], adr=scenario_a["adr"])
    pnl_b = engine.daily_pnl(occ=scenario_b["occ"], adr=scenario_b["adr"])

    gop_delta = pnl_b["gop"] - pnl_a["gop"]
    rev_delta = pnl_b["total_revenue"] - pnl_a["total_revenue"]

    winner = scenario_b["label"] if gop_delta > 0 else scenario_a["label"]

    return {
        "scenario_a": {"label": scenario_a["label"], "gop": pnl_a["gop"], "rev": pnl_a["total_revenue"],
                       "gop_rate": pnl_a["gop_rate"]},
        "scenario_b": {"label": scenario_b["label"], "gop": pnl_b["gop"], "rev": pnl_b["total_revenue"],
                       "gop_rate": pnl_b["gop_rate"]},
        "gop_delta": round(gop_delta, 0),
        "rev_delta": round(rev_delta, 0),
        "winner": winner,
        "recommendation": f"选择「{winner}」— GOP 高出 ¥{abs(gop_delta):,.0f}",
    }


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = USALIEngine()

    print()
    # 场景 1: 当前 OCC=82.3%, ADR=633（最近一天数据）
    pnl1 = engine.daily_pnl(occ=82.3, adr=633)
    engine.print_pnl(pnl1)

    # 场景 2: 降价 10% → OCC 预估提升到 88%
    print(f"\n  ── 场景对比：降价 10% vs 维持现价 ──")
    comparison = compare_scenarios(
        {"label": "维持现价 ¥633", "occ": 82.3, "adr": 633},
        {"label": "降价10% ¥570", "occ": 88, "adr": 570},
    )
    print(f"  {comparison['scenario_a']['label']}: GOP=¥{comparison['scenario_a']['gop']:,.0f} "
          f"({comparison['scenario_a']['gop_rate']:.1f}%)")
    print(f"  {comparison['scenario_b']['label']}: GOP=¥{comparison['scenario_b']['gop']:,.0f} "
          f"({comparison['scenario_b']['gop_rate']:.1f}%)")
    print(f"  ΔGOP: ¥{comparison['gop_delta']:,.0f}  |  ΔRev: ¥{comparison['rev_delta']:,.0f}")
    print(f"  🏆 {comparison['recommendation']}")

    # Flow-Through
    print(f"\n  ── Flow-Through ──")
    ft = engine.flow_through(
        comparison["scenario_b"]["rev"], comparison["scenario_a"]["rev"],
        comparison["scenario_b"]["gop"], comparison["scenario_a"]["gop"],
    )
    print(f"  {ft['interpretation']}")

    # GOP 滚动预测
    print(f"\n  ── 30天 GOP 滚动预测（前 7 天）──")
    forecast = engine.rolling_forecast(days=30, base_occ=82, base_adr=633)
    print(forecast.head(7)[["日期", "星期", "预测OCC", "预测ADR", "GOP", "累积GOP", "保本状态"]].to_string(index=False))
