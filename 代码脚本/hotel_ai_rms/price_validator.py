"""
价格质量校验器 — 5维评分，<60分阻止写入DB
可被 scraper_scheduler.py 或 server.py 导入

评分维度:
  1. 覆盖度 (30%): 应采15家，实采N家
  2. 价格合理性 (30%): 各酒店价格在历史均值±50%范围内
  3. 房型完整性 (20%): 平均每家≥3个房型
  4. 数据新鲜度 (10%): 非历史缓存
  5. 异常值比例 (10%): 被标记异常的数据占比

用法:
  from price_validator import validate_prices
  result = validate_prices(data)
  if result["score"] >= 60:
      store_to_database(data)
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent

# 各酒店历史价格参考区间（2026-08 旺季基准，后续随采集累积自动更新）
PRICE_BANDS = {
    "九寨沟诺富特酒店": (300, 1200),
    "九寨沟万怡酒店": (300, 1200),
    "九寨沟德尔塔酒店": (400, 1800),
    "全季酒店九寨沟九寨大道店": (150, 700),
}


def get_historical_bands() -> dict:
    """从数据库动态更新价格区间（30天历史均值±50%）。"""
    try:
        from database import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        rows = conn.execute(
            """SELECT hotel_name, AVG(price_cny) as avg_price,
                      MIN(price_cny) as min_price, MAX(price_cny) as max_price
               FROM ota_price_history
               WHERE fetch_date >= ? AND price_cny > 0
               GROUP BY hotel_name""",
            (thirty_days_ago,),
        ).fetchall()
        conn.close()

        bands = {}
        for row in rows:
            avg = row["avg_price"]
            if avg and avg > 0:
                bands[row["hotel_name"]] = (
                    max(50, round(avg * 0.5)),
                    round(avg * 1.5),
                )
        return bands
    except Exception:
        return {}


def validate_prices(data: list[dict], checkin: str = None) -> dict:
    """5维质量评分。

    返回:
      {
        "score": 85,          # 总分 0-100
        "passed": True,       # 是否通过（≥60）
        "dimensions": {...},  # 各维度得分
        "warnings": [...],    # 警告信息
        "errors": [...],      # 错误信息
        "anomalies": [...],   # 异常数据行索引
      }
    """
    if not data:
        return {
            "score": 0, "passed": False,
            "dimensions": {}, "warnings": ["无数据"],
            "errors": ["采集结果为空"], "anomalies": [],
        }

    warnings = []
    errors = []
    anomalies = []

    # ── 1. 覆盖度 (30分) ──
    hotels_covered = set()
    for r in data:
        name = r.get("酒店名称", "")
        if name:
            hotels_covered.add(name)

    TARGET = 4
    coverage = len(hotels_covered) / TARGET
    coverage_score = min(30, round(coverage * 30))

    if coverage < 0.6:
        errors.append(f"覆盖率过低: {len(hotels_covered)}/{TARGET} 家")
    elif coverage < 0.8:
        warnings.append(f"覆盖率不足: {len(hotels_covered)}/{TARGET} 家")

    # ── 2. 价格合理性 (30分) ──
    bands = {**PRICE_BANDS, **get_historical_bands()}

    reasonable_count = 0
    total_price_rows = 0
    for i, r in enumerate(data):
        price = r.get("单价_晚", 0)
        if not price or price <= 0:
            continue

        total_price_rows += 1
        name = r.get("酒店名称", "")
        band = bands.get(name)

        if band:
            lo, hi = band
            if lo <= price <= hi:
                reasonable_count += 1
            else:
                anomalies.append({
                    "row": i,
                    "hotel": name,
                    "price": price,
                    "band": band,
                    "reason": f"价格{price}不在合理区间[{lo}, {hi}]",
                })
        else:
            # 无历史区间，仅做基本范围检查
            if 80 <= price <= 50000:
                reasonable_count += 1
            else:
                anomalies.append({
                    "row": i, "hotel": name, "price": price,
                    "reason": f"价格{price}超出基本范围[80, 50000]",
                })

    if total_price_rows > 0:
        reasonability = reasonable_count / total_price_rows
    else:
        reasonability = 0
    price_score = min(30, round(reasonability * 30))

    if reasonability < 0.7:
        errors.append(f"价格异常率过高: {total_price_rows - reasonable_count}/{total_price_rows}")
    elif reasonability < 0.9:
        warnings.append(f"部分价格异常: {total_price_rows - reasonable_count}/{total_price_rows}")

    # ── 3. 房型完整性 (20分) ──
    room_counts = {}
    for r in data:
        name = r.get("酒店名称", "")
        if name not in room_counts:
            room_counts[name] = set()
        room_counts[name].add(r.get("房型", ""))

    avg_rooms = sum(len(v) for v in room_counts.values()) / max(len(room_counts), 1)
    room_score = min(20, round(avg_rooms / 3 * 20))

    if avg_rooms < 1.5:
        warnings.append(f"房型数据稀少: 平均每家 {avg_rooms:.1f} 个房型")

    # ── 4. 数据新鲜度 (10分) ──
    now = datetime.now()
    fresh_count = 0
    for r in data:
        fetch_time = r.get("采集时间", "")
        try:
            ft = datetime.strptime(fetch_time, "%Y-%m-%d %H:%M:%S")
            if (now - ft).total_seconds() < 3600:  # 1小时内
                fresh_count += 1
        except:
            pass

    freshness_ratio = fresh_count / max(len(data), 1)
    fresh_score = min(10, round(freshness_ratio * 10))

    if freshness_ratio < 0.5:
        warnings.append("数据可能为历史缓存")

    # ── 5. 异常值比例 (10分) ──
    anomaly_ratio = len(anomalies) / max(len(data), 1)
    anomaly_score = min(10, round((1 - anomaly_ratio) * 10))

    if anomaly_ratio > 0.3:
        errors.append(f"异常值比例过高: {len(anomalies)}/{len(data)}")

    # ── 汇总 ──
    dimensions = {
        "覆盖度": {"score": coverage_score, "max": 30, "detail": f"{len(hotels_covered)}/{TARGET} 家"},
        "价格合理性": {"score": price_score, "max": 30, "detail": f"{reasonable_count}/{total_price_rows} 合理"},
        "房型完整性": {"score": room_score, "max": 20, "detail": f"平均 {avg_rooms:.1f} 房型/家"},
        "数据新鲜度": {"score": fresh_score, "max": 10, "detail": f"{fresh_count}/{len(data)} 条1h内"},
        "异常值比例": {"score": anomaly_score, "max": 10, "detail": f"{len(anomalies)} 条异常"},
    }

    total_score = sum(d["score"] for d in dimensions.values())

    return {
        "score": total_score,
        "passed": total_score >= 60,
        "dimensions": dimensions,
        "warnings": warnings,
        "errors": errors,
        "anomalies": anomalies,
        "hotels_covered": len(hotels_covered),
        "total_hotels": TARGET,
        "avg_rooms_per_hotel": round(avg_rooms, 1),
    }


def print_validation_report(result: dict):
    """打印质量报告"""
    print(f"\n{'='*50}")
    print(f"📋 数据质量报告 — 总分: {result['score']}/100 {'✅' if result['passed'] else '❌'}")
    print(f"{'='*50}")
    for dim, info in result["dimensions"].items():
        bar = "█" * (info["score"] // 2) + "░" * ((info["max"] - info["score"]) // 2)
        print(f"  {dim:12s} [{bar}] {info['score']}/{info['max']} — {info['detail']}")

    if result["warnings"]:
        print(f"\n  ⚠️ 警告:")
        for w in result["warnings"]:
            print(f"    • {w}")

    if result["errors"]:
        print(f"\n  ❌ 错误:")
        for e in result["errors"]:
            print(f"    • {e}")

    if result["anomalies"]:
        print(f"\n  🔍 异常数据 ({len(result['anomalies'])} 条):")
        for a in result["anomalies"][:5]:
            print(f"    • {a['hotel']}: ¥{a['price']} — {a['reason']}")
