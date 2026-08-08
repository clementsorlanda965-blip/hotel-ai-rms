"""
OTA价格定时采集调度器 v2.0
- 采集 → 质量校验 → 存库 → 降幅检测 → 飞书告警
- 支持 Windows 计划任务调用

用法:
  python scraper_scheduler.py                  # 单次采集+存库+告警
  python scraper_scheduler.py --mode dry-run   # 只采集不存库
  python scraper_scheduler.py --mode ctrip     # 仅携程CDP采集
"""
import sys, json, time as _time
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def collect_prices(mode: str = "ctrip") -> dict:
    """执行价格采集"""
    from ota_scraper import scrape_all, save_results

    print(f"[{_now()}] 开始OTA价格采集 (模式: {mode})")
    try:
        result = scrape_all(mode=mode)
    except Exception as e:
        print(f"  采集失败: {e}")
        return {"error": str(e), "data": [], "source": "失败", "count": 0,
                "hotels_covered": 0, "real_price_count": 0}

    print(f"[{_now()}] 完成: {result['source']}")
    print(f"  {result['count']} 条 / {result['hotels_covered']} 家")

    # 保存 CSV/JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = ROOT / f"ota_prices_{ts}.csv"
    json_path = ROOT / f"ota_prices_{ts}.json"
    save_results(result["data"], csv_path, json_path)

    # 也保存为最新
    save_results(result["data"])

    return result


def validate_quality(data: list[dict]) -> dict:
    """质量校验"""
    from price_validator import validate_prices, print_validation_report

    vresult = validate_prices(data)
    print_validation_report(vresult)
    return vresult


def store_to_database(result: dict) -> int:
    """将真实价格写入SQLite"""
    try:
        from database import get_conn
        db = get_conn()
        cursor = db.cursor()
    except Exception as e:
        print(f"  数据库不可用: {e}")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")
    count = 0

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ota_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT NOT NULL,
            ota_platform TEXT DEFAULT '携程',
            room_type TEXT DEFAULT '标准房',
            price_cny REAL NOT NULL,
            data_source TEXT,
            fetch_date TEXT NOT NULL,
            fetch_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 建索引（幂等）
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ota_date
            ON ota_price_history(hotel_name, fetch_date)
        """)
    except:
        pass

    # 批量写入
    rows_to_insert = []
    for r in result.get("data", []):
        if not r.get("is_real", False):
            continue
        rows_to_insert.append((
            r["酒店名称"],
            r.get("OTA平台", "携程"),
            r.get("房型", "标准房"),
            r["单价_晚"],
            r.get("数据来源", ""),
            today,
            now_time,
        ))

    if rows_to_insert:
        cursor.executemany("""
            INSERT INTO ota_price_history
            (hotel_name, ota_platform, room_type, price_cny,
             data_source, fetch_date, fetch_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)
        count = len(rows_to_insert)

    db.commit()
    db.close()
    print(f"  数据库: {count} 条写入")
    return count


def check_price_drops(result: dict, threshold: float = 0.15) -> list[dict]:
    """检测降幅>threshold的酒店"""
    try:
        from database import get_conn
        db = get_conn()
        cursor = db.cursor()
    except:
        return []

    today_prices = {}
    for r in result.get("data", []):
        if not r.get("is_real", False):
            continue
        name = r["酒店名称"]
        if name not in today_prices or r["单价_晚"] < today_prices[name]:
            today_prices[name] = r["单价_晚"]

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    alerts = []

    for hotel_name, cur in today_prices.items():
        try:
            cursor.execute("""
                SELECT AVG(price_cny) as avg_price
                FROM ota_price_history
                WHERE hotel_name = ? AND fetch_date = ?
            """, (hotel_name, yesterday))
            row = cursor.fetchone()
            if row and row[0]:
                prev = row[0]
                drop = (prev - cur) / prev
                if drop > threshold:
                    alerts.append({
                        "hotel_name": hotel_name,
                        "prev_price": round(prev),
                        "current_price": cur,
                        "drop_pct": round(drop * 100, 1),
                    })
        except:
            pass

    db.close()
    return alerts


def send_alerts(alerts: list[dict], result: dict = None) -> bool:
    """发送飞书告警"""
    if not alerts:
        return False

    try:
        from feishu_alert import AlertEngine
        engine = AlertEngine()
        sent = engine.send_price_drop_alert(alerts)

        if sent:
            print(f"  🔔 飞书告警: {len(alerts)} 条降幅异常")
        return sent
    except Exception as e:
        print(f"  飞书告警失败: {e}")
        return False


def print_summary(result: dict):
    """打印价格摘要"""
    prices = {}
    for r in result.get("data", []):
        if r.get("is_real", False) and r.get("OTA平台") == "携程":
            name = r["酒店名称"]
            if name not in prices or r["单价_晚"] < prices[name]:
                prices[name] = r["单价_晚"]

    if not prices:
        print("\n⚠️ 无携程真实价格")
        return

    print(f"\n{'='*50}")
    print(f"📊 携程真实价格 ({datetime.now().strftime('%Y-%m-%d')})")
    print(f"{'='*50}")
    print(f"{'酒店':<30s} {'最低价':>8s}")
    print(f"{'-'*40}")
    for name in sorted(prices, key=lambda n: prices[n]):
        print(f"  {name:<28s} ¥{prices[name]:>6}")
    print(f"{'='*50}")
    print(f"共 {len(prices)} 家 | 来源: {result.get('source','?')}")


def run_once(mode: str = "production"):
    """单次运行：采集 → 校验 → 存库 → 检测 → 告警"""
    print("═" * 55)
    print(f"🏨 OTA价格定时采集 — {_now()}")
    print("═" * 55)

    # 1. 采集
    result = collect_prices(mode=mode)

    if result.get("error"):
        # 采集失败告警
        send_alerts([], result)
        return result

    # 2. 质量校验
    if result.get("data"):
        vresult = validate_quality(result["data"])
        if not vresult.get("passed"):
            print(f"\n  ❌ 质量校验未通过 (得分: {vresult['score']}/100)")
            # 仍继续，但标记来源
            result["quality_warning"] = True

    # 3. 存库（仅 production 模式）
    if mode == "production":
        store_to_database(result)

    # 4-7. 仅 production 模式执行后续管线（dry-run/data-check 止于校验）
    if mode == "production":
        # 4. 降幅检测
        alerts = check_price_drops(result)

        # 5. 飞书告警
        if alerts:
            print(f"\n🚨 价格降幅告警 ({len(alerts)} 条):")
            for a in sorted(alerts, key=lambda x: x["drop_pct"], reverse=True):
                print(f"  {a['hotel_name']}: ¥{a['prev_price']}→¥{a['current_price']} "
                      f"({a['drop_pct']}%)")
            send_alerts(alerts)

        # 6. 日汇总
        print_summary(result)

        # 7. 发送日汇总报告
        try:
            from feishu_alert import AlertEngine
            prices = {}
            for r in result.get("data", []):
                if r.get("is_real", False) and r.get("OTA平台") == "携程":
                    name = r["酒店名称"]
                    if name not in prices or r["单价_晚"] < prices[name]:
                        prices[name] = r["单价_晚"]

            engine = AlertEngine()
            engine.send_daily_summary({
                "hotels_covered": result.get("hotels_covered", 0),
                "total_hotels": 4,
                "source": result.get("source", ""),
                "prices": prices,
            })
        except Exception:
            pass
    else:
        # dry-run/data-check: 仅打印摘要不发送
        print_summary(result)

    return result


# ═══════════════════════════════════════════════════════════════
# 历史数据查询（供 server.py API 使用）
# ═══════════════════════════════════════════════════════════════

DB_PATH = ROOT / "data" / "rms.db"


def ensure_history_tables():
    """确保 ota_price_history 表存在（供 server.py 启动时调用）。"""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ota_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT NOT NULL,
            ota_platform TEXT DEFAULT '携程',
            room_type TEXT DEFAULT '标准房',
            price_cny REAL NOT NULL,
            data_source TEXT,
            fetch_date TEXT NOT NULL,
            fetch_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ota_date
        ON ota_price_history(hotel_name, fetch_date)
    """)
    conn.commit()
    conn.close()


def query_price_trend(hotel_name: str, days: int = 30) -> list[dict]:
    """查询指定酒店的历史价格趋势（每日最低价）。"""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT fetch_date,
               MIN(price_cny) as min_price,
               AVG(price_cny) as avg_price,
               MAX(price_cny) as max_price,
               COUNT(*) as room_types
        FROM ota_price_history
        WHERE hotel_name = ?
          AND fetch_date >= date('now', '-' || ? || ' days')
        GROUP BY fetch_date
        ORDER BY fetch_date ASC
    """, (hotel_name, days)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_competitor_avg(hotel_name: str, platform: str, days: int = 30) -> list[dict]:
    """查询指定酒店在指定平台的均价趋势。"""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT fetch_date,
               AVG(price_cny) as avg_price,
               MIN(price_cny) as min_price,
               MAX(price_cny) as max_price
        FROM ota_price_history
        WHERE hotel_name = ? AND ota_platform = ?
          AND fetch_date >= date('now', '-' || ? || ' days')
        GROUP BY fetch_date
        ORDER BY fetch_date ASC
    """, (hotel_name, platform, days)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_all_hotels_latest() -> list[dict]:
    """查询所有酒店最新一次采集的最低价格和房型数。"""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT hotel_name,
               MIN(price_cny) as min_price,
               AVG(price_cny) as avg_price,
               MAX(price_cny) as max_price,
               COUNT(DISTINCT room_type) as room_types,
               MAX(fetch_date) as fetch_date,
               MAX(fetch_time) as fetch_time
        FROM ota_price_history
        WHERE fetch_date = (SELECT MAX(fetch_date) FROM ota_price_history)
        GROUP BY hotel_name
        ORDER BY min_price ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_health_status() -> dict:
    """系统健康状态（供 /api/health 使用）。"""
    import sqlite3
    try:
        conn = sqlite3.connect(str(DB_PATH))
        latest = conn.execute(
            "SELECT MAX(fetch_date) as last_fetch FROM ota_price_history"
        ).fetchone()[0]
        hotel_count = conn.execute(
            "SELECT COUNT(DISTINCT hotel_name) FROM ota_price_history"
        ).fetchone()[0]
        total_records = conn.execute(
            "SELECT COUNT(*) FROM ota_price_history"
        ).fetchone()[0]
        conn.close()
        return {
            "status": "healthy",
            "last_fetch": latest,
            "hotels_tracked": hotel_count,
            "total_records": total_records,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="OTA价格定时采集调度器 v2.0")
    p.add_argument("--mode", default="production",
                   choices=["production", "dry-run", "ctrip"])
    args = p.parse_args()

    mode = "production" if args.mode == "production" else args.mode
    if args.mode == "dry-run":
        mode = "dry-run"

    run_once(mode)
