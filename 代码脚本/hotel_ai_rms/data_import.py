"""
data_import.py — 数据导入模块
支持：PMS导出CSV、OTA比价CSV、手动录入、批量导入
自动识别格式、清洗、写入 SQLite
"""
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

OUTPUT_DIR = Path(r"E:\工作AI\酒店管理\数据分析")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# PMS 数据导入 (Opera/西软/绿云 等)
# ═══════════════════════════════════════════════════════════════

PMS_COLUMN_MAPS = {
    # Opera 导出格式
    "opera": {
        "date": ["Business Date", "业务日期", "日期", "Date", "日期 "],
        "occ": ["Occupancy%", "出租率", "OCC%", "入住率", "OCC"],
        "adr": ["ADR", "平均房价", "Average Rate"],
        "revpar": ["RevPAR", "每间可卖房收入", "REVPAR"],
        "revenue": ["Total Revenue", "总收入", "Revenue", "收入"],
        "room_revenue": ["Room Revenue", "客房收入", "Rooms Revenue"],
        "room_sold": ["Room Nights", "已售房数", "Rooms Sold", "间夜数"],
    },
    # 西软/绿云 通用格式
    "generic": {
        "date": ["日期", "date", "Date", "营业日"],
        "occ": ["出租率", "OCC", "入住率", "occ"],
        "adr": ["平均房价", "ADR", "均价", "adr"],
        "revpar": ["RevPAR", "revpar", "单房收益"],
        "revenue": ["总收入", "收入合计", "revenue", "营业总额"],
        "room_revenue": ["客房收入", "房费收入"],
        "fb_revenue": ["餐饮收入", "餐饮"],
        "other_revenue": ["其他收入", "其他"],
        "room_sold": ["已售房数", "售出房间", "间夜"],
        "total_cost": ["总成本", "费用合计", "成本"],
        "gop": ["GOP", "经营毛利", "毛利"],
    },
}


def detect_pms_format(file_path: str) -> str:
    """自动检测PMS导出文件格式。"""
    df = pd.read_csv(file_path, nrows=3, encoding="utf-8-sig") if file_path.endswith(".csv") else pd.read_excel(file_path, nrows=3)
    cols = [c.strip().lower() for c in df.columns]

    if "business date" in cols or "arrival" in cols:
        return "opera"
    return "generic"


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """在DataFrame中匹配第一个存在的列。"""
    for c in candidates:
        for col in df.columns:
            if c.lower() in col.lower().strip():
                return col
    return None


def import_pms_data(file_path: str, source: str = "pms") -> pd.DataFrame:
    """导入PMS导出的经营数据，自动映射列名。

    返回标准化的 DataFrame，可直接写入 database.daily_metrics。
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    else:
        df = pd.read_excel(file_path)

    fmt = detect_pms_format(file_path)
    col_map = PMS_COLUMN_MAPS.get(fmt, PMS_COLUMN_MAPS["generic"])

    result_rows = []
    for _, row in df.iterrows():
        record = {"source": source}

        date_col = _find_column(df, col_map["date"])
        if date_col:
            raw = row[date_col]
            try:
                d = pd.to_datetime(raw).date()
                record["date"] = d.strftime("%Y-%m-%d")
            except Exception:
                continue

        for key in ["occ", "adr", "revpar", "revenue", "room_revenue",
                     "fb_revenue", "other_revenue", "room_sold", "total_cost", "gop"]:
            if key in col_map:
                col = _find_column(df, col_map[key])
                if col and pd.notna(row[col]):
                    try:
                        val = float(str(row[col]).replace(",", "").replace("¥", "").replace("%", ""))
                        record[key] = val
                    except (ValueError, TypeError):
                        pass

        # 计算缺失的指标
        if "occ" in record and "adr" in record and "revpar" not in record:
            record["revpar"] = round(record["occ"] * record["adr"] / 100, 2)

        if "revpar" in record and "gop_rate" not in record:
            if "revenue" in record and "gop" in record and record["revenue"] > 0:
                record["gop_rate"] = round(record["gop"] / record["revenue"] * 100, 1)

        result_rows.append(record)

    parsed_df = pd.DataFrame(result_rows)

    # 保存到 SQLite
    if not parsed_df.empty:
        try:
            from database import get_conn
            conn = get_conn()
            for _, row in parsed_df.iterrows():
                data = {k: v for k, v in row.items() if pd.notna(v)}
                if "date" not in data:
                    continue
                metrics = {
                    "date": data["date"],
                    "occ": data.get("occ"),
                    "adr": data.get("adr"),
                    "revpar": data.get("revpar"),
                    "total_revenue": data.get("revenue"),
                    "room_revenue": data.get("room_revenue"),
                    "fb_revenue": data.get("fb_revenue"),
                    "other_revenue": data.get("other_revenue"),
                    "total_cost": data.get("total_cost"),
                    "gop": data.get("gop"),
                    "gop_rate": data.get("gop_rate"),
                    "room_sold": data.get("room_sold"),
                    "source": data.get("source", "pms"),
                }
                conn.execute(
                    """INSERT OR REPLACE INTO daily_metrics
                    (date, occ, adr, revpar, total_revenue, room_revenue, fb_revenue,
                     other_revenue, total_cost, gop, gop_rate, room_sold, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    tuple(metrics.get(k) for k in [
                        "date", "occ", "adr", "revpar", "total_revenue",
                        "room_revenue", "fb_revenue", "other_revenue",
                        "total_cost", "gop", "gop_rate", "room_sold", "source",
                    ]),
                )
            conn.commit()
            conn.close()
        except ImportError:
            pass

    return parsed_df


# ═══════════════════════════════════════════════════════════════
# OTA 比价 CSV 导入
# ═══════════════════════════════════════════════════════════════

def import_ota_csv(file_path: str) -> pd.DataFrame:
    """导入OTA比价CSV，自动检测格式并写入 competitor_prices 表。"""
    df = pd.read_csv(file_path, encoding="utf-8-sig")

    required = ["酒店名称", "单价_晚"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV缺少必要列：{', '.join(missing)}。必须包含：酒店名称, 单价_晚")

    today = date.today().strftime("%Y-%m-%d")

    records = []
    for _, row in df.iterrows():
        records.append({
            "fetch_date": today,
            "checkin_date": row.get("入住日期", row.get("checkin_date", today)),
            "hotel_name": row["酒店名称"],
            "room_type": row.get("房型", row.get("room_type", "")),
            "platform": row.get("OTA平台", row.get("platform", "CSV导入")),
            "price": float(row["单价_晚"]),
            "star_level": int(row.get("星级", row.get("star_level", 4))),
            "data_source": row.get("数据来源", "csv"),
        })

    try:
        from database import save_competitor_prices
        save_competitor_prices(records)
    except ImportError:
        pass

    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════
# 批量生成示例数据（用于初始化空数据库）
# ═══════════════════════════════════════════════════════════════

def seed_sample_data(days: int = 90):
    """为空白数据库生成历史经营数据种子。"""
    import numpy as np
    from database import get_conn

    rng = np.random.default_rng(42)
    today = date.today()
    conn = get_conn()

    base_occ = 68.0
    base_adr = 500.0
    base_rooms = 120

    season_factors = {
        1: 0.65, 2: 0.70, 3: 0.80, 4: 1.30, 5: 1.40,
        6: 1.10, 7: 1.35, 8: 1.35, 9: 1.30, 10: 1.50, 11: 0.90, 12: 0.75,
    }

    count = 0
    for d in range(days, 0, -1):
        cur = today - timedelta(days=d)
        m = cur.month
        season = season_factors.get(m, 1.0)
        dow = cur.weekday()
        weekend = 1.12 if dow >= 5 else 1.0
        noise = float(rng.normal(0, 0.05))

        occ = min(98, max(20, base_occ * season * weekend * (1 + noise)))
        adr = max(150, round(base_adr * season * (1 + noise * 0.6), 2))
        revpar = round(occ / 100 * adr, 2)
        rooms = round(occ / 100 * base_rooms)
        room_rev = round(adr * rooms, 2)
        fb_rev = round(room_rev * rng.uniform(0.15, 0.35), 2)
        other_rev = round(room_rev * rng.uniform(0.03, 0.10), 2)
        total_rev = room_rev + fb_rev + other_rev
        total_cost = round(total_rev * rng.uniform(0.52, 0.68), 2)
        gop_val = round(total_rev - total_cost, 2)
        gop_rate = round(gop_val / total_rev * 100, 1) if total_rev > 0 else 0

        conn.execute(
            """INSERT OR IGNORE INTO daily_metrics
            (date, occ, adr, revpar, total_revenue, room_revenue, fb_revenue,
             other_revenue, total_cost, gop, gop_rate, room_sold, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cur.strftime("%Y-%m-%d"), round(occ,1), adr, revpar, total_rev,
             room_rev, fb_rev, other_rev, total_cost, gop_val, gop_rate, rooms, "seed"),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def export_metrics_csv(start_date: str = None, end_date: str = None, output_path: str = None):
    """导出经营数据为CSV（用于备份或分享）。"""
    from database import get_daily_metrics

    if start_date is None:
        start_date = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = date.today().strftime("%Y-%m-%d")

    df = get_daily_metrics(start_date, end_date)
    if df.empty:
        print("无数据可导出。")
        return None

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d")
        output_path = str(OUTPUT_DIR / f"经营数据导出_{ts}.csv")

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python data_import.py <command> [args]")
        print("  seed [days]          — 生成示例历史数据")
        print("  import-pms <file>    — 导入PMS导出的经营数据")
        print("  import-ota <file>    — 导入OTA比价CSV")
        print("  export [start] [end] — 导出经营数据CSV")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "seed":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        n = seed_sample_data(days)
        print(f"已生成 {n} 天历史经营数据。")

    elif cmd == "import-pms":
        if len(sys.argv) < 3:
            print("请指定PMS导出文件路径")
            sys.exit(1)
        df = import_pms_data(sys.argv[2])
        print(f"已导入 {len(df)} 条PMS经营数据。")

    elif cmd == "import-ota":
        if len(sys.argv) < 3:
            print("请指定OTA比价CSV文件路径")
            sys.exit(1)
        df = import_ota_csv(sys.argv[2])
        print(f"已导入 {len(df)} 条OTA比价数据。")

    elif cmd == "export":
        path = export_metrics_csv(
            sys.argv[2] if len(sys.argv) > 2 else None,
            sys.argv[3] if len(sys.argv) > 3 else None,
        )
        if path:
            print(f"数据已导出至：{path}")
