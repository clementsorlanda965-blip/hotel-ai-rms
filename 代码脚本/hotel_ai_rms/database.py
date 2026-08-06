"""
database.py — Hotel AI-RMS 数据持久化层 (SQLite)
替代 session_state，支持历史趋势分析和跨会话数据保留
"""
import sqlite3
import json
import hashlib
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any
import pandas as pd

DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "rms.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化所有表结构。"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hotel_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT NOT NULL DEFAULT '我的酒店',
            city TEXT DEFAULT '',
            star_level INTEGER DEFAULT 4,
            total_rooms INTEGER DEFAULT 120,
            base_price REAL DEFAULT 500,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS daily_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            occ REAL,           -- 出租率 %
            adr REAL,           -- 平均房价
            revpar REAL,        -- 每间可卖房收入
            total_revenue REAL, -- 总收入
            room_revenue REAL,  -- 客房收入
            fb_revenue REAL,    -- 餐饮收入
            other_revenue REAL, -- 其他收入
            total_cost REAL,    -- 总成本
            gop REAL,           -- 经营毛利
            gop_rate REAL,      -- GOP率 %
            room_sold INTEGER,  -- 已售房间数
            source TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(date, source)
        );

        CREATE TABLE IF NOT EXISTS price_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            base_price REAL,
            suggested_price REAL,
            adopted_price REAL,
            decision_basis TEXT,
            price_zone TEXT,     -- 提价区/平价区/降价区
            forecast_occ REAL,
            is_adopted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS competitor_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_date TEXT NOT NULL,
            checkin_date TEXT NOT NULL,
            hotel_name TEXT NOT NULL,
            room_type TEXT,
            platform TEXT,
            price REAL,
            star_level INTEGER,
            data_source TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS marketing_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_date TEXT NOT NULL,
            customer_count INTEGER,
            channel TEXT,
            benefit_type TEXT,
            estimated_revenue REAL,
            status TEXT DEFAULT 'generated',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS decision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            detail TEXT,
            estimated_impact TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS budget_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            target_occ REAL,
            target_adr REAL,
            target_revpar REAL,
            target_revenue REAL,
            target_gop_rate REAL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS competitive_set (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT NOT NULL,
            star_level INTEGER,
            city TEXT,
            address TEXT,
            base_price REAL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()

    # 确保有默认酒店配置
    cur = conn.execute("SELECT COUNT(*) as cnt FROM hotel_config")
    if cur.fetchone()["cnt"] == 0:
        conn.execute(
            "INSERT INTO hotel_config (hotel_name, city, star_level, total_rooms, base_price) VALUES (?,?,?,?,?)",
            ("我的酒店", "九寨沟", 4, 120, 500),
        )
        conn.commit()

    # 确保有默认竞品组
    cur = conn.execute("SELECT COUNT(*) as cnt FROM competitive_set")
    if cur.fetchone()["cnt"] == 0:
        default_competitors = [
            ("九寨沟悦榕庄", 5, "九寨沟", "漳扎镇", 1600),
            ("九寨沟希尔顿度假酒店", 5, "九寨沟", "漳扎镇", 1100),
            ("九寨沟天堂洲际大饭店", 5, "九寨沟", "漳扎镇甘海子", 1350),
            ("九寨沟喜来登国际大酒店", 5, "九寨沟", "漳扎镇", 950),
            ("九寨沟天源豪生度假酒店", 5, "九寨沟", "漳扎镇", 850),
            ("九寨沟亚朵酒店", 4, "九寨沟", "漳扎镇", 500),
            ("全季酒店(九寨沟景区店)", 4, "九寨沟", "漳扎镇", 380),
            ("九寨度假村酒店", 4, "九寨沟", "漳扎镇彭丰村", 550),
            ("汉庭酒店(九寨沟景区店)", 3, "九寨沟", "漳扎镇", 240),
            ("如家精选酒店(九寨沟店)", 3, "九寨沟", "漳扎镇", 220),
        ]
        for comp in default_competitors:
            conn.execute(
                "INSERT INTO competitive_set (hotel_name, star_level, city, address, base_price) VALUES (?,?,?,?,?)",
                comp,
            )
        conn.commit()

    conn.close()


# ═══════════════════════════════════════════════════════════════
# 日常指标 CRUD
# ═══════════════════════════════════════════════════════════════

def save_daily_metrics(metrics: dict) -> int:
    """保存或更新单日经营指标。"""
    conn = get_conn()
    cols = ", ".join(metrics.keys())
    placeholders = ", ".join(["?" for _ in metrics])
    values = list(metrics.values())
    updates = ", ".join(f"{k}=excluded.{k}" for k in metrics if k != "date")
    conn.execute(
        f"INSERT INTO daily_metrics ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(date) DO UPDATE SET {updates}",
        values,
    )
    conn.commit()
    conn.close()
    return metrics.get("date", "")


def get_daily_metrics(start_date: str, end_date: str) -> pd.DataFrame:
    """查询日期区间的经营指标。"""
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM daily_metrics WHERE date BETWEEN ? AND ? ORDER BY date",
        conn, params=(start_date, end_date),
    )
    conn.close()
    return df


def get_latest_metrics(days: int = 30) -> pd.DataFrame:
    """获取最近N天指标。"""
    end = date.today().strftime("%Y-%m-%d")
    start = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    return get_daily_metrics(start, end)


# ═══════════════════════════════════════════════════════════════
# 价格决策 CRUD
# ═══════════════════════════════════════════════════════════════

def save_price_decision(decision: dict):
    conn = get_conn()
    cols = ", ".join(decision.keys())
    placeholders = ", ".join(["?" for _ in decision])
    conn.execute(
        f"INSERT INTO price_decisions ({cols}) VALUES ({placeholders})",
        list(decision.values()),
    )
    conn.commit()
    conn.close()


def get_price_decisions(start_date: str, end_date: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM price_decisions WHERE date BETWEEN ? AND ? ORDER BY date",
        conn, params=(start_date, end_date),
    )
    conn.close()
    return df


def get_adoption_rate(days: int = 90) -> float:
    conn = get_conn()
    cur = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_adopted) as adopted FROM price_decisions "
        "WHERE date >= ?",
        ((date.today() - timedelta(days=days)).strftime("%Y-%m-%d"),),
    )
    row = cur.fetchone()
    conn.close()
    if row["total"] == 0:
        return 0.0
    return row["adopted"] / row["total"] * 100


# ═══════════════════════════════════════════════════════════════
# 竞品价格
# ═══════════════════════════════════════════════════════════════

def save_competitor_prices(prices: list[dict]):
    conn = get_conn()
    for p in prices:
        cols = ", ".join(p.keys())
        placeholders = ", ".join(["?" for _ in p])
        conn.execute(
            f"INSERT INTO competitor_prices ({cols}) VALUES ({placeholders})",
            list(p.values()),
        )
    conn.commit()
    conn.close()


def get_competitor_prices(checkin_date: str = None, days: int = 7) -> pd.DataFrame:
    conn = get_conn()
    if checkin_date:
        df = pd.read_sql_query(
            "SELECT * FROM competitor_prices WHERE checkin_date = ? ORDER BY price",
            conn, params=(checkin_date,),
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM competitor_prices WHERE fetch_date >= date('now', ?) ORDER BY fetch_date DESC, price",
            conn, params=(f"-{days}",),
        )
    conn.close()
    return df


# ═══════════════════════════════════════════════════════════════
# 竞品组管理
# ═══════════════════════════════════════════════════════════════

def get_competitive_set(active_only: bool = True) -> list[dict]:
    conn = get_conn()
    sql = "SELECT * FROM competitive_set"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY star_level DESC, base_price DESC"
    rows = [dict(r) for r in conn.execute(sql).fetchall()]
    conn.close()
    return rows


def add_competitor(hotel_name: str, star_level: int, city: str = "", address: str = "", base_price: float = 0):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO competitive_set (hotel_name, star_level, city, address, base_price) VALUES (?,?,?,?,?)",
        (hotel_name, star_level, city, address, base_price),
    )
    conn.commit()
    conn.close()


def remove_competitor(hotel_name: str):
    conn = get_conn()
    conn.execute("UPDATE competitive_set SET is_active=0 WHERE hotel_name=?", (hotel_name,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# 决策日志
# ═══════════════════════════════════════════════════════════════

def log_decision(action_type: str, detail: str, estimated_impact: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO decision_log (action_type, detail, estimated_impact) VALUES (?,?,?)",
        (action_type, detail, estimated_impact),
    )
    conn.commit()
    conn.close()


def get_decision_logs(limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM decision_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()]
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════
# 预算目标
# ═══════════════════════════════════════════════════════════════

def save_budget_target(year: int, month: int, targets: dict):
    conn = get_conn()
    conn.execute(
        """INSERT INTO budget_targets (year, month, target_occ, target_adr, target_revpar, target_revenue, target_gop_rate)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(year, month) DO UPDATE SET
           target_occ=excluded.target_occ, target_adr=excluded.target_adr,
           target_revpar=excluded.target_revpar, target_revenue=excluded.target_revenue,
           target_gop_rate=excluded.target_gop_rate""",
        (year, month, targets.get("occ"), targets.get("adr"), targets.get("revpar"),
         targets.get("revenue"), targets.get("gop_rate")),
    )
    conn.commit()
    conn.close()


def get_budget_target(year: int, month: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM budget_targets WHERE year=? AND month=?", (year, month)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ═══════════════════════════════════════════════════════════════
# 统计摘要
# ═══════════════════════════════════════════════════════════════

def get_summary_stats(days: int = 30) -> dict:
    """获取近期关键统计。"""
    conn = get_conn()
    end = date.today()
    start = end - timedelta(days=days)

    metrics = conn.execute(
        "SELECT AVG(occ) as avg_occ, AVG(adr) as avg_adr, AVG(revpar) as avg_revpar, "
        "AVG(gop_rate) as avg_gop, SUM(total_revenue) as total_revenue "
        "FROM daily_metrics WHERE date BETWEEN ? AND ?",
        (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
    ).fetchone()

    decisions = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_adopted) as adopted FROM price_decisions "
        "WHERE date BETWEEN ? AND ?",
        (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
    ).fetchone()

    hotel = conn.execute("SELECT * FROM hotel_config LIMIT 1").fetchone()

    alerts = conn.execute(
        "SELECT COUNT(*) as cnt FROM competitor_prices WHERE fetch_date >= ?",
        (start.strftime("%Y-%m-%d"),),
    ).fetchone()

    conn.close()

    return {
        "avg_occ": round(metrics["avg_occ"] or 0, 1),
        "avg_adr": round(metrics["avg_adr"] or 0, 0),
        "avg_revpar": round(metrics["avg_revpar"] or 0, 0),
        "avg_gop_rate": round(metrics["avg_gop"] or 0, 1),
        "total_revenue": round(metrics["total_revenue"] or 0, 0),
        "adoption_rate": round(
            (decisions["adopted"] / decisions["total"] * 100) if decisions["total"] > 0 else 0, 1
        ),
        "total_decisions": decisions["total"],
        "comp_alerts": alerts["cnt"],
        "hotel_name": hotel["hotel_name"] if hotel else "我的酒店",
        "total_rooms": hotel["total_rooms"] if hotel else 120,
    }


# 初始化
init_db()
