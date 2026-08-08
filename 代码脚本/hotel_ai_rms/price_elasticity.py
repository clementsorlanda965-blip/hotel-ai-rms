"""
price_elasticity.py —— 酒店价格弹性 OLS 回归引擎 v1.0

估算需求量（OCC）对价格（ADR）变化的敏感度：
  价格弹性 = ΔOCC% / ΔADR%

典型值：
  - 商务酒店（平日）：-0.3 ~ -0.7（缺乏弹性）
  - 度假酒店（旺季）：-0.1 ~ -0.3（高度缺乏弹性）
  - 度假酒店（淡季）：-1.0 ~ -2.0（弹性充足）
  - 经济型酒店：-1.5 ~ -2.5（高度弹性）

诺富特九寨沟是度假酒店，预期弹性：
  旺季（5/7/8/10月）：-0.2 ~ -0.4（涨价 10% 只损失 2-4% OCC）
  淡季（1/2/3/11/12月）：-1.0 ~ -1.5（降价 10% 可提升 10-15% OCC）

用法：
  from price_elasticity import ElasticityEstimator
  est = ElasticityEstimator()
  result = est.estimate()
  print(f"当前弹性: {result['elasticity']:.2f}")
  print(f"建议: {result['recommendation']}")

数据来源：daily_metrics 表（date, adr, occ → log-log OLS 回归）
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "rms.db"


class ElasticityEstimator:
    """价格弹性估算器（OLS log-log 回归 + 季节性分层）"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)

    def estimate(self, target_month: int = None) -> dict:
        """估计当前月份的价格弹性。

        方法：log(OCC) = α + β × log(ADR) + ε
        弹性 = β（log-log 模型中 β 直接就是弹性）

        注意：原始 OLS 可能因季节性混杂（旺季 ADR 和 OCC 同时高）返回正弹性。
        这种情况下自动降级为 First-Difference 回归或启发式估算。

        最小需要 15 个数据点；少于 15 个则降级为启发式估算。
        """
        if target_month is None:
            target_month = date.today().month

        # 1. 全量 First-Difference 回归（消除季节性混杂）
        fd_result = self._first_diff_elasticity(month_filter=None)

        # 2. 同月分层 First-Difference
        fd_monthly = self._first_diff_elasticity(month_filter=target_month)

        # 3. 选择最佳估计源
        if fd_monthly["n_samples"] >= 10 and fd_monthly["elasticity"] < -0.01:
            primary = fd_monthly
            primary["source"] = f"{target_month}月Δlog回归（{fd_monthly['n_samples']} 样本）"
        elif fd_result["n_samples"] >= 15 and fd_result["elasticity"] < -0.01:
            primary = fd_result
            primary["source"] = f"全量Δlog回归（{fd_result['n_samples']} 样本）"
        else:
            # 降级：OLS 回归或启发式
            ols = self._ols_elasticity(month_filter=target_month)
            if ols["n_samples"] >= 10 and ols["elasticity"] < -0.01:
                primary = ols
                primary["source"] = f"{target_month}月OLS回归（{ols['n_samples']} 样本）"
            else:
                primary = self._heuristic_estimate(target_month)
                primary["source"] = "启发式估算（回归符号异常，使用行业基准值）"

        # 4. 约束弹性在合理范围
        elasticity = primary["elasticity"]
        if elasticity >= -0.01:  # 正或接近零 → 用启发式
            primary = self._heuristic_estimate(target_month)
            primary["source"] = "启发式估算（回归为正弹性，季节性混杂）"
            elasticity = primary["elasticity"]

        # 5. 生成建议
        recommendation = self._recommend(elasticity, target_month)

        return {
            "elasticity": round(elasticity, 3),
            "elasticity_abs": round(abs(elasticity), 3),
            "r_squared": primary.get("r_squared", 0),
            "n_samples": primary.get("n_samples", 0),
            "source": primary["source"],
            "month": target_month,
            "recommendation": recommendation,
            "fd_elasticity": fd_result.get("elasticity"),
            "ols_elasticity": None,
        }

    def _ols_elasticity(self, month_filter: int = None) -> dict:
        """执行 log-log OLS 回归。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if month_filter:
            rows = conn.execute("""
                SELECT adr, occ FROM daily_metrics
                WHERE hotel_id = 1
                  AND CAST(substr(date, 6, 2) AS INTEGER) = ?
                  AND adr > 100 AND occ > 0 AND occ <= 100
                ORDER BY date
            """, (month_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT adr, occ FROM daily_metrics
                WHERE hotel_id = 1
                  AND adr > 100 AND occ > 0 AND occ <= 100
                ORDER BY date
            """).fetchall()
        conn.close()

        if len(rows) < 5:
            return {"elasticity": -1.0, "r_squared": 0, "n_samples": len(rows)}

        adr = np.array([r["adr"] for r in rows], dtype=float)
        occ = np.array([r["occ"] for r in rows], dtype=float)

        # log-log 变换
        log_adr = np.log(adr)
        log_occ = np.log(occ)

        # OLS: log_occ = α + β × log_adr
        # β = Cov(log_adr, log_occ) / Var(log_adr)
        log_adr_mean = np.mean(log_adr)
        log_occ_mean = np.mean(log_occ)

        cov = np.mean((log_adr - log_adr_mean) * (log_occ - log_occ_mean))
        var = np.var(log_adr)

        if var < 1e-10:
            return {"elasticity": -0.5, "r_squared": 0, "n_samples": len(rows)}

        beta = cov / var
        alpha = log_occ_mean - beta * log_adr_mean

        # R²
        log_occ_pred = alpha + beta * log_adr
        ss_res = np.sum((log_occ - log_occ_pred) ** 2)
        ss_tot = np.sum((log_occ - log_occ_mean) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            "elasticity": round(beta, 4),
            "alpha": round(alpha, 4),
            "r_squared": round(r_squared, 4),
            "n_samples": len(rows),
        }

    def _first_diff_elasticity(self, month_filter: int = None) -> dict:
        """First-Difference log-log 回归：Δlog(OCC) = β × Δlog(ADR)。

        差分消除不随时间变化的混杂因素（如酒店星级、品牌定位），
        能更准确地识别价格变化对需求变化的因果效应。
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if month_filter:
            rows = conn.execute("""
                SELECT adr, occ FROM daily_metrics
                WHERE hotel_id = 1
                  AND CAST(substr(date, 6, 2) AS INTEGER) = ?
                  AND adr > 100 AND occ > 0 AND occ <= 100
                ORDER BY date
            """, (month_filter,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT adr, occ FROM daily_metrics
                WHERE hotel_id = 1
                  AND adr > 100 AND occ > 0 AND occ <= 100
                ORDER BY date
            """).fetchall()
        conn.close()

        if len(rows) < 6:
            return {"elasticity": -1.0, "r_squared": 0, "n_samples": 0}

        adr = np.array([r["adr"] for r in rows], dtype=float)
        occ = np.array([r["occ"] for r in rows], dtype=float)

        # First difference of logs
        d_log_adr = np.diff(np.log(adr))
        d_log_occ = np.diff(np.log(occ))

        # OLS: d_log_occ = β × d_log_adr (no intercept)
        var_da = np.var(d_log_adr)
        if var_da < 1e-10:
            return {"elasticity": -1.0, "r_squared": 0, "n_samples": len(d_log_adr)}

        beta = np.mean(d_log_occ * d_log_adr) / var_da

        # R²
        d_log_occ_pred = beta * d_log_adr
        ss_res = np.sum((d_log_occ - d_log_occ_pred) ** 2)
        ss_tot = np.sum(d_log_occ ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            "elasticity": round(beta, 4),
            "r_squared": round(r_squared, 4),
            "n_samples": len(d_log_adr),
        }

    def _heuristic_estimate(self, month: int) -> dict:
        """启发式弹性估算（行业基准值）。

        度假酒店弹性基准：
          旺季（4/5/7/8/9/10）：-0.25
          平季（6/11）：-0.60
          淡季（1/2/3/12）：-1.20
        """
        if month in (4, 5, 7, 8, 9, 10):
            e = -0.25
        elif month in (6, 11):
            e = -0.60
        else:
            e = -1.20
        return {"elasticity": e, "r_squared": 0, "n_samples": 0}

    def _recommend(self, elasticity: float, month: int) -> str:
        """基于弹性估算给出定价建议。"""
        e = abs(elasticity)

        if e < 0.3:
            return (
                f"价格弹性极低（|ε|={e:.2f}<0.3），需求对价格不敏感。"
                f"建议：旺季大胆提价 10-15%，OCC 损失可控（<3%），利润净增。"
            )
        elif e < 0.6:
            return (
                f"价格弹性较低（|ε|={e:.2f}），需求对价格不太敏感。"
                f"建议：适度提价 5-10%，需监控 Pace 变化；如 Pace 未放缓可继续上调。"
            )
        elif e < 1.0:
            return (
                f"价格弹性中等（|ε|={e:.2f}），价格变动会明确影响需求。"
                f"建议：谨慎调价，每次 ≤5%，观察 48h 后 Pace 变化再决定下一步。"
            )
        elif e < 1.5:
            return (
                f"价格弹性较高（|ε|={e:.2f}>1.0），降价可换取显著的 OCC 提升。"
                f"建议：淡季降价 8-12% 以提升出租率，但注意不破保本点。"
            )
        else:
            return (
                f"价格弹性很高（|ε|={e:.2f}>1.5），需求高度价格敏感。"
                f"建议：大幅降价抢量（不破底价 ¥399），重点关注 GOP 率而非 ADR。"
            )

    def revenue_optimal_price(self, current_price: float, elasticity: float,
                              variable_cost: float = 45) -> dict:
        """计算收益最优价格（基于价格弹性）。

        当 |ε| > 1（弹性需求）：P* = MC × ε/(1+ε)
        当 |ε| < 1（缺乏弹性）：理论上可无限提价，实际约束于竞对和季节性上限
        当 |ε| ≤ 0：无效弹性，按缺乏弹性处理

        Returns: {"optimal_price", "current_price", "recommended_change_pct", "rationale", ...}
        """
        e = abs(elasticity)  # 用绝对值判断弹性幅度
        base = {
            "current_price": current_price,
            "variable_cost": variable_cost,
            "elasticity_used": elasticity,
        }

        if e < 0.05:  # 弹性极小，不调
            return {**base, "optimal_price": current_price,
                    "recommended_change_pct": 0,
                    "rationale": "弹性接近零，当前价格即为最优"}

        if e < 1.0:
            # 缺乏弹性 → 可提价，上限为 current × 1.25
            optimal = min(current_price * 1.15, current_price * (1 + (1 - e) * 0.25))
            optimal = max(current_price, optimal)
            change_pct = (optimal - current_price) / current_price * 100
            return {**base,
                    "optimal_price": round(optimal, 0),
                    "recommended_change_pct": round(change_pct, 1),
                    "rationale": f"缺乏弹性（|ε|={e:.2f}<1）→ 建议提价 {change_pct:.0f}% 至 ¥{optimal:.0f}，提价增收 > 销量损失"}
        else:
            # 弹性需求 → 利润最大化公式 P* = MC × ε/(1+ε)
            # ε 是负值，ε/(1+ε) 当 |ε|>1 时为正值
            neg_e = -abs(elasticity)  # 确保负号
            if abs(1 + neg_e) > 1e-10:
                revenue_optimal = variable_cost * neg_e / (1 + neg_e)
            else:
                revenue_optimal = current_price

            # clamp
            revenue_optimal = max(399, min(current_price * 1.3, revenue_optimal))
            change_pct = (revenue_optimal - current_price) / current_price * 100

            if change_pct > 0:
                rationale = f"建议提价 {change_pct:.0f}% 至 ¥{revenue_optimal:.0f}（弹性需求最优价）"
            elif change_pct < -5:
                rationale = f"建议降价 {abs(change_pct):.0f}% 至 ¥{revenue_optimal:.0f}（以量换利）"
            else:
                rationale = f"当前价格 ¥{current_price:.0f} 接近最优"

            return {**base,
                    "optimal_price": round(revenue_optimal, 0),
                    "recommended_change_pct": round(change_pct, 1),
                    "rationale": rationale}


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def estimate_elasticity(month: int = None) -> dict:
    """估算当前价格弹性。"""
    est = ElasticityEstimator()
    return est.estimate(target_month=month)


def optimal_price(current_price: float, month: int = None) -> dict:
    """计算收益最优价格。"""
    est = ElasticityEstimator()
    result = est.estimate(target_month=month)
    return est.revenue_optimal_price(current_price, result["elasticity"])


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    today = date.today()
    est = ElasticityEstimator()

    print("=" * 55)
    print(f"  价格弹性 OLS 回归 —— {today}")
    print("=" * 55)

    result = est.estimate(target_month=today.month)
    print(f"\n  当前月（{today.month}月）弹性：{result['elasticity']}")
    print(f"  R²：{result['r_squared']}  |  样本：{result['n_samples']} 个")
    print(f"  数据源：{result['source']}")
    print(f"\n  💡 {result['recommendation']}")

    # 最优价格
    opt = est.revenue_optimal_price(670, result["elasticity"])
    print(f"\n  当前 BAR：¥{opt['current_price']:.0f}")
    print(f"  最优价格：¥{opt['optimal_price']:.0f}")
    print(f"  {opt['rationale']}")

    # 按月份展示弹性变化
    print(f"\n  ── 各月弹性估算 ──")
    for m in range(1, 13):
        mr = est.estimate(target_month=m)
        bar = "▓" * int(abs(mr["elasticity"]) * 10) if mr["n_samples"] >= 5 else "░" * 5
        tag = "✓" if mr["n_samples"] >= 10 else ("~" if mr["n_samples"] >= 5 else "?")
        print(f"  {m:2d}月  ε={mr['elasticity']:6.2f}  {bar}  "
              f"R²={mr['r_squared']:.2f}  n={mr['n_samples']}  {tag}")
