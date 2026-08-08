"""
ota_radar.py —— OTA 分销雷达 / 竞争指数引擎 v1.0

计算酒店行业标准的三个核心竞争指数：
  - MPI (Market Penetration Index)    — 市场渗透指数：出租率 vs 竞对平均
  - ARI (Average Rate Index)          — 价格指数：ADR vs 竞对平均
  - RGI (Revenue Generation Index)    — 收益生成指数：RevPAR vs 竞对平均

附加分析：
  - 渠道效率评分（直销/OTA/协议/团客）
  - 价格倒挂检测（美团/同程低于携程 ≥5%）
  - 竞争格局雷达图数据
  - 定价健康度仪表盘

公式（STR 标准）：
  MPI = 自家 OCC / 竞对平均 OCC × 100
  ARI = 自家 ADR / 竞对平均 ADR × 100
  RGI = 自家 RevPAR / 竞对平均 RevPAR × 100

解读：
  MPI > 100 → 市场渗透力强（卖出更多房间）
  ARI > 100 → 定价溢价（品牌力强）
  RGI > 100 → 综合收益优于竞对（最核心指标）

用法：
  from ota_radar import CompetitorRadar
  radar = CompetitorRadar()
  indices = radar.calculate(today)
  radar.print_radar(indices)

数据来源：
  - ota_price_history（竞对实时价格）
  - daily_metrics（自家历史 OCC/ADR/RevPAR）
  - competitive_set（竞对基础信息）
  - channel_mix（渠道产量）
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "rms.db"

from config import (
    SELF_HOTEL_NAME, COMPETITORS, COMPETITOR_HOTELS,
    PRICE_INVERSION_THRESHOLD, FLOOR_PRICE,
)

# ═══════════════════════════════════════════════════════════════
# 竞争指数计算
# ═══════════════════════════════════════════════════════════════

class CompetitorRadar:
    """OTA 分销雷达 —— 竞争指数 + 渠道效率 + 价格倒挂检测"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── MPI / ARI / RGI ──

    def calculate(self, target_date: date = None) -> dict:
        """计算完整竞争指数。

        Returns:
          {"date", "mpi", "ari", "rgi",
           "self": {"occ", "adr", "revpar"},
           "comp_set": {"occ", "adr", "revpar", "count"},
           "verdict": "优于竞对/持平/落后",
           "trend": {"mpi_7d_ago": float, "ari_7d_ago": float, ...},
           "channel_efficiency": {...},
           "price_inversions": [...],
           }
        """
        target = target_date or date.today()
        date_str = target.strftime("%Y-%m-%d")

        # 自家指标（取最近可用日）
        self_metrics = self._get_self_metrics(target)

        # 竞对价格（最新采集）
        comp_price_data = self._get_competitor_prices()

        # 竞对 OCC 估算（基于价格 + 星级回归）
        comp_metrics = self._estimate_competitor_metrics(comp_price_data, self_metrics)

        # 计算指数
        if comp_metrics["adr"] > 0 and self_metrics["adr"] > 0:
            mpi = (self_metrics["occ"] / comp_metrics["occ"] * 100) if comp_metrics["occ"] > 0 else 100
            ari = self_metrics["adr"] / comp_metrics["adr"] * 100
            rgi = self_metrics["revpar"] / comp_metrics["revpar"] * 100 if comp_metrics["revpar"] > 0 else 100
        else:
            mpi = ari = rgi = 100

        # 判决
        if rgi > 110:
            verdict = "显著优于竞对"
        elif rgi > 100:
            verdict = "优于竞对"
        elif rgi > 95:
            verdict = "持平"
        elif rgi > 85:
            verdict = "落后于竞对"
        else:
            verdict = "严重落后"

        # 7 天前趋势
        trend = self._get_trend(target)

        # 渠道效率
        channel_eff = self._channel_efficiency()

        # 价格倒挂
        inversions = self._detect_price_inversion()

        return {
            "date": date_str,
            "mpi": round(mpi, 1),
            "ari": round(ari, 1),
            "rgi": round(rgi, 1),
            "verdict": verdict,
            "self": self_metrics,
            "comp_set": comp_metrics,
            "trend": trend,
            "channel_efficiency": channel_eff,
            "price_inversions": inversions,
        }

    def _get_self_metrics(self, target: date) -> dict:
        """从 daily_metrics 获取自家最新指标。"""
        conn = self._conn()
        row = conn.execute("""
            SELECT occ, adr, revpar
            FROM daily_metrics
            WHERE hotel_id = 1 AND date <= ?
            ORDER BY date DESC LIMIT 1
        """, (target.strftime("%Y-%m-%d"),)).fetchone()
        conn.close()

        if row:
            return {"occ": row["occ"] or 65, "adr": row["adr"] or 450,
                    "revpar": row["revpar"] or 293}
        # 兜底
        return {"occ": 65, "adr": 450, "revpar": 293}

    def _get_competitor_prices(self) -> list[dict]:
        """获取竞对最新价格。"""
        conn = self._conn()
        rows = conn.execute("""
            SELECT hotel_name, MIN(price_cny) as min_price,
                   AVG(price_cny) as avg_price, ota_platform
            FROM ota_price_history
            WHERE fetch_date = (SELECT MAX(fetch_date) FROM ota_price_history)
              AND hotel_name != ?
            GROUP BY hotel_name
        """, (SELF_HOTEL_NAME,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _estimate_competitor_metrics(self, comp_prices: list, self_metrics: dict) -> dict:
        """估算竞对 OCC/ADR/RevPAR。

        ADR 已知（携程实时价格 → 全渠道 ADR 约等于携程最低价 × 1.15）。
        OCC 基于价格-星级回归估算（行业经验模型）。
        """
        if not comp_prices:
            # 兜底：使用 config 参考价
            comp_adrs = [h["base"] for h in COMPETITOR_HOTELS]
            comp_stars = [h["star"] for h in COMPETITOR_HOTELS]
            comp_avg_adr = np.mean(comp_adrs)
        else:
            comp_adrs = [r.get("avg_price", r.get("min_price", 350)) for r in comp_prices]
            comp_avg_adr = np.mean(comp_adrs) if comp_adrs else 400

        # 估算竞对 OCC：基于价格星级模型
        # 行业经验：价格越高的酒店 OCC 通常越低（除旺季外）
        # 诺富特周边：万怡 OCC ≈ 65%，德尔塔 OCC ≈ 55%，全季 OCC ≈ 72%
        # 简化：以全季 OCC=72% 为基准，每高 ¥100 降 3% OCC
        base_occ = 72
        comp_avg_occ = max(50, min(85, base_occ - (comp_avg_adr - 350) / 100 * 3))

        comp_avg_revpar = comp_avg_adr * comp_avg_occ / 100

        return {
            "occ": round(comp_avg_occ, 1),
            "adr": round(comp_avg_adr, 0),
            "revpar": round(comp_avg_revpar, 0),
            "count": len(comp_prices),
            "hotels_priced": [r.get("hotel_name", "?") for r in comp_prices] if comp_prices else [],
        }

    def _get_trend(self, target: date) -> dict:
        """7 天前趋势对比。直接取数不递归。"""
        week_ago = target - timedelta(days=7)
        week_ago_self = self._get_self_metrics(week_ago)
        comp_prices = self._get_competitor_prices()
        week_ago_comp = self._estimate_competitor_metrics(comp_prices, week_ago_self)

        if week_ago_comp["adr"] > 0 and week_ago_self["adr"] > 0:
            mpi_7d = (week_ago_self["occ"] / week_ago_comp["occ"] * 100) if week_ago_comp["occ"] > 0 else 100
            ari_7d = week_ago_self["adr"] / week_ago_comp["adr"] * 100
            rgi_7d = week_ago_self["revpar"] / week_ago_comp["revpar"] * 100 if week_ago_comp["revpar"] > 0 else 100
        else:
            mpi_7d = ari_7d = rgi_7d = 100

        return {
            "mpi_7d_ago": round(mpi_7d, 1),
            "ari_7d_ago": round(ari_7d, 1),
            "rgi_7d_ago": round(rgi_7d, 1),
        }

    # ── 渠道效率分析 ──

    def _channel_efficiency(self) -> dict:
        """计算各渠道效率评分（基于 channel_mix 表）。"""
        conn = self._conn()
        rows = conn.execute("""
            SELECT channel,
                   SUM(room_nights) as total_rn,
                   SUM(revenue) as total_rev,
                   AVG(commission) as avg_comm,
                   COUNT(DISTINCT date) as active_days
            FROM channel_mix
            WHERE date >= date('now', '-30 days')
            GROUP BY channel
        """).fetchall()
        conn.close()

        channels = {}
        for r in rows:
            rd = dict(r)
            channel = rd.get("channel", "未知")
            rn = rd.get("total_rn", 0) or 0
            rev = rd.get("total_rev", 0) or 0
            adr = rev / rn if rn > 0 else 0
            comm_rate = rd.get("avg_comm", 0) or 0
            # 效率分 = 净 ADR（扣佣金） × 活跃天数权重
            net_adr = adr * (1 - comm_rate)
            efficiency = min(100, max(20, net_adr / 500 * 100))
            channels[channel] = {
                "room_nights": rn,
                "revenue": round(rev, 0),
                "adr": round(adr, 0),
                "commission_rate": round(comm_rate * 100, 1),
                "net_adr": round(net_adr, 0),
                "efficiency_score": round(efficiency, 1),
                "active_days": rd.get("active_days", 0),
            }

        return channels

    # ── 价格倒挂检测 ──

    def _detect_price_inversion(self) -> list[dict]:
        """检测自家酒店在非携程渠道是否低于携程价 > 阈值。

        返回倒挂列表 [{"platform", "ctrip_price", "other_price", "gap_pct"}, ...]
        """
        conn = self._conn()
        rows = conn.execute("""
            SELECT ota_platform, MIN(price_cny) as min_price
            FROM ota_price_history
            WHERE hotel_name = ?
              AND fetch_date = (SELECT MAX(fetch_date) FROM ota_price_history)
            GROUP BY ota_platform
        """, (SELF_HOTEL_NAME,)).fetchall()
        conn.close()

        prices = {r["ota_platform"]: r["min_price"] for r in rows}
        ctrip_price = prices.get("携程", None)
        if not ctrip_price:
            return []

        inversions = []
        for platform, price in prices.items():
            if platform == "携程":
                continue
            gap = (ctrip_price - price) / ctrip_price
            if gap >= PRICE_INVERSION_THRESHOLD:
                inversions.append({
                    "platform": platform,
                    "ctrip_price": ctrip_price,
                    "other_price": price,
                    "gap_pct": round(gap * 100, 1),
                })

        return sorted(inversions, key=lambda x: x["gap_pct"], reverse=True)

    # ── 竞争格局雷达图数据 ──

    def radar_data(self) -> dict:
        """生成雷达图的 6 维度数据（竞争格局可视化）。"""
        indices = self.calculate()
        ch = indices.get("channel_efficiency", {})

        # 6 维度：MPI, ARI, RGI, 直销效率, OTA效率, 价格健康度
        direct_eff = max(ch.get("直销", {}).get("efficiency_score", 60),
                         ch.get("官网", {}).get("efficiency_score", 60),
                         ch.get("微信小程序", {}).get("efficiency_score", 55))
        ota_eff = max(ch.get("携程", {}).get("efficiency_score", 55),
                      ch.get("美团", {}).get("efficiency_score", 50),
                      ch.get("飞猪", {}).get("efficiency_score", 50))
        inversions = len(indices.get("price_inversions", []))
        price_health = max(30, 100 - inversions * 20)

        return {
            "labels": ["MPI", "ARI", "RGI", "直销效率", "OTA效率", "价格健康度"],
            "self": [indices["mpi"], indices["ari"], indices["rgi"],
                     direct_eff, ota_eff, price_health],
            "benchmark": [100, 100, 100, 60, 55, 80],  # 行业基准线
        }

    # ── 定价健康度仪表盘 ──

    def health_dashboard(self) -> dict:
        """一次性输出竞争格局的全部关键信号。"""
        indices = self.calculate()
        inversions = indices.get("price_inversions", [])

        # 信号灯
        signals = []

        # RGI 信号
        rgi = indices["rgi"]
        if rgi >= 110:
            signals.append({"light": "green", "label": "RGI 优秀",
                           "detail": f"RGI={rgi}，综合收益远超竞对"})
        elif rgi >= 95:
            signals.append({"light": "green", "label": "RGI 健康",
                           "detail": f"RGI={rgi}，与竞对持平或略优"})
        elif rgi >= 85:
            signals.append({"light": "yellow", "label": "RGI 需关注",
                           "detail": f"RGI={rgi}，落后竞对 5-15%"})
        else:
            signals.append({"light": "red", "label": "RGI 预警",
                           "detail": f"RGI={rgi}，严重落后，需紧急调整定价"})

        # ARI 信号
        ari = indices["ari"]
        if ari > 110:
            signals.append({"light": "yellow", "label": "ARI 偏高",
                           "detail": f"ARI={ari}，溢价 >10%，需关注价格敏感性"})
        elif ari >= 95:
            signals.append({"light": "green", "label": "ARI 健康",
                           "detail": f"ARI={ari}，价格定位合理"})
        else:
            signals.append({"light": "red", "label": "ARI 偏低",
                           "detail": f"ARI={ari}，定价低于竞对，品牌溢价受损"})

        # 价格倒挂
        if inversions:
            platforms = ", ".join(i["platform"] for i in inversions)
            signals.append({"light": "red", "label": "价格倒挂",
                           "detail": f"{platforms} 低于携程 >{PRICE_INVERSION_THRESHOLD:.0%}"})
        else:
            signals.append({"light": "green", "label": "渠道价格一致",
                           "detail": "各渠道无显著价格倒挂"})

        # MPI
        mpi = indices["mpi"]
        if mpi >= 105:
            signals.append({"light": "green", "label": "MPI 强势",
                           "detail": f"MPI={mpi}，市场份额优于竞对"})
        elif mpi >= 90:
            signals.append({"light": "yellow", "label": "MPI 持平",
                           "detail": f"MPI={mpi}，市场份额与竞对相近"})
        else:
            signals.append({"light": "red", "label": "MPI 弱势",
                           "detail": f"MPI={mpi}，市场份额落后"})

        return {
            "date": indices["date"],
            "mpi": indices["mpi"],
            "ari": indices["ari"],
            "rgi": indices["rgi"],
            "verdict": indices["verdict"],
            "signals": signals,
            "price_inversions": inversions,
        }

    # ── 终端输出 ──

    def print_radar(self, data: dict = None):
        """格式化打印竞争雷达图。"""
        d = data or self.calculate()

        print("=" * 55)
        print(f"  📡 OTA 分销雷达 — {d['date']}")
        print("=" * 55)
        print(f"  {'指标':<12s} {'自家':>8s} {'竞对均值':>10s} {'指数':>8s}  {'判定':<10s}")
        print(f"  {'-'*50}")
        print(f"  {'OCC %':<12s} {d['self']['occ']:>8.1f} {d['comp_set']['occ']:>10.1f} {d['mpi']:>8.1f}  {'✅' if d['mpi']>=100 else '⚠️':<10s}")
        print(f"  {'ADR ¥':<12s} {d['self']['adr']:>8.0f} {d['comp_set']['adr']:>10.0f} {d['ari']:>8.1f}  {'✅' if d['ari']>=100 else '⚠️':<10s}")
        print(f"  {'RevPAR ¥':<12s} {d['self']['revpar']:>8.0f} {d['comp_set']['revpar']:>10.0f} {d['rgi']:>8.1f}  {'✅' if d['rgi']>=100 else '⚠️':<10s}")
        print(f"  {'='*55}")
        print(f"  🏆 综合判定：{d['verdict']}")
        print(f"  竞对覆盖：{d['comp_set']['count']} 家 — {d['comp_set'].get('hotels_priced', [])}")

        # 渠道效率
        ch = d.get("channel_efficiency", {})
        if ch:
            print(f"\n  ── 渠道效率评分（近30天）──")
            for name in sorted(ch, key=lambda n: ch[n]["efficiency_score"], reverse=True):
                info = ch[name]
                bar = "█" * int(info["efficiency_score"] / 5)
                print(f"  {name:<10s} {bar:<20s} {info['efficiency_score']:.0f}分  "
                      f"净ADR ¥{info['net_adr']:.0f}  {info['room_nights']:.0f}间夜")

        # 价格倒挂
        inv = d.get("price_inversions", [])
        if inv:
            print(f"\n  🔴 价格倒挂告警：")
            for i in inv:
                print(f"  {i['platform']} ¥{i['other_price']} vs 携程 ¥{i['ctrip_price']} "
                      f"（倒挂 {i['gap_pct']}%）")
        else:
            print(f"\n  ✅ 各渠道价格一致，无倒挂。")


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def get_competition_indices(target_date: date = None) -> dict:
    """获取竞争指数（便捷函数）。"""
    radar = CompetitorRadar()
    return radar.calculate(target_date)


def get_health_dashboard() -> dict:
    """获取定价健康度仪表盘。"""
    radar = CompetitorRadar()
    return radar.health_dashboard()


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    radar = CompetitorRadar()
    data = radar.calculate()
    radar.print_radar(data)

    print(f"\n  ── 定价健康度 ──")
    health = radar.health_dashboard()
    for s in health["signals"]:
        emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(s["light"], "⚪")
        print(f"  {emoji} {s['label']}: {s['detail']}")

    print(f"\n  ── 雷达图数据 ──")
    rd = radar.radar_data()
    for i, label in enumerate(rd["labels"]):
        bar_self = "█" * int(rd["self"][i] / 5)
        bar_bench = "┄" * int(rd["benchmark"][i] / 5)
        print(f"  {label:<8s} {bar_self:<22s} {rd['self'][i]:.0f}  (基准 {rd['benchmark'][i]})")
