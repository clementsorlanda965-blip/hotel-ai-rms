"""
sync_hotel_data.py —— 从 config.py 同步酒店主数据到 SQLite

用途：一次性运行，将 config.py 中的权威酒店数据写入数据库。
      hotel_config + competitive_set 两表对齐 config 定义。

用法：
  python sync_hotel_data.py          # 同步（覆盖已有数据）
  python sync_hotel_data.py --check  # 仅检查差异，不写入
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "rms.db"

from config import (
    SELF_HOTEL_ID, SELF_HOTEL_NAME, FLOOR_PRICE, TOTAL_ROOMS, STAR_LEVEL,
    COMPETITORS, CTRIP_REFERENCE_PRICES,
)


def sync(check_only: bool = False):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    changes = []

    # ── 1. 更新 hotel_config（自家酒店主数据）──
    cur = conn.execute("SELECT * FROM hotel_config WHERE id = ?", (SELF_HOTEL_ID,))
    row = cur.fetchone()
    if row:
        current = dict(row)
        expected = {
            "hotel_name": SELF_HOTEL_NAME,
            "star_level": STAR_LEVEL,
            "total_rooms": TOTAL_ROOMS,
            "base_price": CTRIP_REFERENCE_PRICES.get(SELF_HOTEL_NAME, 500),
        }
        diffs = {}
        for k, v in expected.items():
            cv = current.get(k)
            # 数值型比较用 float 容差，避免 357.0 vs 357 假阳性
            try:
                if abs(float(cv) - float(v)) > 0.01:
                    diffs[k] = (cv, v)
            except (TypeError, ValueError):
                if str(cv) != str(v):
                    diffs[k] = (cv, v)

        if diffs:
            changes.append(f"hotel_config (id={SELF_HOTEL_ID}):")
            for k, (old, new) in diffs.items():
                changes.append(f"  {k}: {old} → {new}")
            if not check_only:
                conn.execute(
                    "UPDATE hotel_config SET hotel_name=?, star_level=?, total_rooms=?, base_price=? WHERE id=?",
                    (SELF_HOTEL_NAME, STAR_LEVEL, TOTAL_ROOMS,
                     CTRIP_REFERENCE_PRICES.get(SELF_HOTEL_NAME, 500), SELF_HOTEL_ID),
                )
    else:
        changes.append(f"hotel_config: 新建 id={SELF_HOTEL_ID} → {SELF_HOTEL_NAME}")
        if not check_only:
            conn.execute(
                "INSERT INTO hotel_config (id, hotel_name, city, star_level, total_rooms, base_price) VALUES (?,?,?,?,?,?)",
                (SELF_HOTEL_ID, SELF_HOTEL_NAME, "九寨沟", STAR_LEVEL, TOTAL_ROOMS,
                 CTRIP_REFERENCE_PRICES.get(SELF_HOTEL_NAME, 500)),
            )

    # ── 2. 确保 competitive_set 有 property_type 列 ──
    try:
        conn.execute("ALTER TABLE competitive_set ADD COLUMN property_type TEXT DEFAULT 'competitor'")
        changes.append("competitive_set: 添加 property_type 列")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            raise

    # ── 3. 确保 competitive_set 有 ctrip_id 列 ──
    try:
        conn.execute("ALTER TABLE competitive_set ADD COLUMN ctrip_id TEXT")
        changes.append("competitive_set: 添加 ctrip_id 列")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            raise

    # ── 4. 同步 competitive_set（upsert 4 家酒店）──
    for comp in COMPETITORS:
        existing = conn.execute(
            "SELECT * FROM competitive_set WHERE hotel_name = ?",
            (comp["name"],),
        ).fetchone()

        if existing:
            ex = dict(existing)
            updates = {}
            field_map = {
                "star_level": comp.get("star", 4),
                "base_price": comp.get("base", 500),
                "property_type": comp.get("property_type", "competitor"),
                "ctrip_id": comp.get("ctrip_id", ""),
                "total_rooms": comp.get("total_rooms", 120),
                "address": comp.get("address", ""),
            }
            for field, expected_val in field_map.items():
                current_val = ex.get(field)
                try:
                    same = abs(float(current_val or 0) - float(expected_val or 0)) < 0.01
                except (TypeError, ValueError):
                    same = str(current_val) == str(expected_val)
                if not same:
                    updates[field] = (current_val, expected_val)

            if updates:
                changes.append(f"competitive_set '{comp['name']}':")
                for k, (old, new) in updates.items():
                    changes.append(f"  {k}: {old} → {new}")
                if not check_only:
                    set_clause = ", ".join(f"{k}=?" for k in updates)
                    new_vals = [new for _, new in updates.values()]
                    conn.execute(
                        f"UPDATE competitive_set SET {set_clause} WHERE hotel_name=?",
                        new_vals + [comp["name"]],
                    )
        else:
            changes.append(f"competitive_set: 新建 '{comp['name']}' ({comp.get('property_type', 'competitor')})")
            if not check_only:
                conn.execute(
                    """INSERT INTO competitive_set
                       (hotel_name, star_level, city, address, base_price, is_active, property_type, ctrip_id)
                       VALUES (?,?,?,?,?,1,?,?)""",
                    (comp["name"], comp.get("star", 4), "九寨沟",
                     comp.get("address", ""), comp.get("base", 500),
                     comp.get("property_type", "competitor"), comp.get("ctrip_id", "")),
                )

    # ── 5. 同步 total_rooms 列到 competitive_set ──
    try:
        conn.execute("ALTER TABLE competitive_set ADD COLUMN total_rooms INTEGER DEFAULT 120")
        changes.append("competitive_set: 添加 total_rooms 列")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            raise

    # 更新 total_rooms
    for comp in COMPETITORS:
        conn.execute(
            "UPDATE competitive_set SET total_rooms=? WHERE hotel_name=?",
            (comp.get("total_rooms", 120), comp["name"]),
        )

    conn.commit()

    # ── 输出 ──
    if not changes:
        print("✅ 数据库酒店主数据已与 config.py 一致，无需同步。")
    else:
        action = "将执行" if not check_only else "检测到差异（--check 模式，未写入）"
        print(f"📋 {action} {len(changes)} 项变更：")
        for c in changes:
            print(f"  {c}")
        if not check_only:
            print("✅ 同步完成。")

    # 打印最终状态
    print()
    print("── hotel_config ──")
    h = conn.execute("SELECT * FROM hotel_config WHERE id=?", (SELF_HOTEL_ID,)).fetchone()
    if h:
        for k in h.keys():
            print(f"  {k}: {h[k]}")

    print()
    print("── competitive_set ──")
    for r in conn.execute("SELECT * FROM competitive_set WHERE is_active=1 ORDER BY star_level DESC").fetchall():
        rd = dict(r)
        pt = rd.get("property_type", "competitor") or "competitor"
        tr = rd.get("total_rooms", "?") or "?"
        ct = rd.get("ctrip_id", "?") or "?"
        print(f"  {rd['hotel_name']:<20s} {rd['star_level']}星  {pt:<12s} "
              f"{str(tr):>4s}间  底价¥{rd['base_price']:.0f}  ctrip:{ct}")

    conn.close()
    return len(changes) == 0


if __name__ == "__main__":
    check_only = "--check" in sys.argv
    sync(check_only)
