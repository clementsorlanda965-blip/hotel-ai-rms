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


_db_initialized = False


def get_conn() -> sqlite3.Connection:
    global _db_initialized
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    if not _db_initialized:
        _init_tables(conn)
        _db_initialized = True
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate_add_column(conn: sqlite3.Connection, table: str, col: str, col_def: str):
    """安全迁移：表已存在时补加缺失列（仅忽略列已存在错误）。"""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            pass  # 列已存在，预期内
        else:
            raise  # 其他错误（表不存在、语法错等）继续抛出


def _init_tables(conn: sqlite3.Connection):
    """在给定连接上创建所有表并插入默认数据（仅内部调用）。"""
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
            hotel_id INTEGER DEFAULT 1,
            date TEXT NOT NULL,
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
            UNIQUE(hotel_id, date, source)
        );

        CREATE TABLE IF NOT EXISTS price_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            date TEXT NOT NULL,
            base_price REAL,
            suggested_price REAL,
            adopted_price REAL,
            decision_basis TEXT,
            price_zone TEXT,     -- 提价区/平价区/降价区
            forecast_occ REAL,
            is_adopted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(hotel_id, date)
        );

        CREATE TABLE IF NOT EXISTS competitor_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
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
            hotel_id INTEGER DEFAULT 1,
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
            hotel_id INTEGER DEFAULT 1,
            action_type TEXT NOT NULL,
            detail TEXT,
            estimated_impact TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS budget_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            target_occ REAL,
            target_adr REAL,
            target_revpar REAL,
            target_revenue REAL,
            target_gop_rate REAL,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(hotel_id, year, month)
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

        -- 预订进度表（Pickup）—— 收益管理核心数据
        CREATE TABLE IF NOT EXISTS booking_pace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            stay_date TEXT NOT NULL,          -- 入住日期
            snapshot_date TEXT NOT NULL,       -- 快照日期（哪天记录的）
            days_before_arrival INTEGER,       -- 距入住日天数
            rooms_booked INTEGER DEFAULT 0,    -- 累计已预订间夜
            revenue_booked REAL DEFAULT 0,     -- 累计已预订收入
            adr_booked REAL DEFAULT 0,         -- 当前预订 ADR
            source TEXT DEFAULT 'manual',      -- 数据来源: pms/manual/csv
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(hotel_id, stay_date, snapshot_date)
        );

        -- 渠道产量明细表
        CREATE TABLE IF NOT EXISTS channel_mix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            date TEXT NOT NULL,
            channel TEXT NOT NULL,              -- 渠道名称
            room_nights INTEGER DEFAULT 0,      -- 间夜数
            revenue REAL DEFAULT 0,             -- 收入
            commission REAL DEFAULT 0,          -- 佣金
            avg_lead_time REAL DEFAULT 0,       -- 平均提前预订天数
            cancellation_count INTEGER DEFAULT 0,
            no_show_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(hotel_id, date, channel)
        );

        -- 告警事件表
        CREATE TABLE IF NOT EXISTS alerts_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            event_time TEXT NOT NULL,
            alert_type TEXT NOT NULL,            -- price_inversion/occ_anomaly/comp_drop/gop_drop
            severity INTEGER DEFAULT 3,          -- 1-5, 5=最严重
            alert_message TEXT,
            related_entity_type TEXT,            -- hotel/competitor/channel
            related_entity_id TEXT,
            is_resolved INTEGER DEFAULT 0,
            resolved_by TEXT,
            resolved_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- 事件/节假日日历
        CREATE TABLE IF NOT EXISTS event_calendar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            event_name TEXT NOT NULL,
            event_type TEXT DEFAULT 'holiday',   -- holiday/exhibition/concert/sport/local_event
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            city TEXT DEFAULT '',
            expected_occ_impact REAL DEFAULT 0,  -- 预期出租率影响 %
            expected_adr_impact REAL DEFAULT 0,  -- 预期 ADR 影响 %
            historical_occ_lift REAL,            -- 历史出租率提升（回归校准值）
            historical_adr_lift REAL,            -- 历史 ADR 提升（回归校准值）
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- 客户画像表（持久化）
        CREATE TABLE IF NOT EXISTS guest_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            guest_name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            member_tier TEXT DEFAULT '普通',      -- 普通/银卡/金卡/钻石
            total_spend REAL DEFAULT 0,
            first_stay_date TEXT,
            last_stay_date TEXT,
            total_stays INTEGER DEFAULT 0,
            preferred_room_type TEXT,
            preferred_channel TEXT,
            segment_type TEXT,                   -- 客源类型：品牌散客/企业商务/OTA线上/旅行社团/长住客/上门客
            avg_stay_length REAL DEFAULT 0,      -- 平均入住时长（晚）
            price_sensitivity_score REAL DEFAULT 0.5,
            churn_risk_score REAL DEFAULT 0,
            lifetime_value REAL DEFAULT 0,
            rf_recency_days INTEGER,
            rf_frequency INTEGER DEFAULT 0,
            rf_monetary REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- 客源细分汇总表（渠道×客源类型 × 日期快照）
        CREATE TABLE IF NOT EXISTS segment_mix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER DEFAULT 1,
            date TEXT NOT NULL,                 -- 汇总日期（快照日）
            segment_type TEXT NOT NULL,         -- 品牌散客/企业商务/OTA渠道/旅行团/长住客/上门客
            channel TEXT DEFAULT '',            -- 渠道名称（可为通用)
            customer_count INTEGER DEFAULT 0,   -- 客户数
            room_nights REAL DEFAULT 0,         -- 间夜数
            revenue REAL DEFAULT 0,             -- 收入
            commission REAL DEFAULT 0,          -- 佣金
            avg_stay_length REAL DEFAULT 0,     -- 平均入住时长（晚）
            source TEXT DEFAULT 'manual',       -- simulated/csv/db
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(hotel_id, date, segment_type, channel, source)
        );

        -- OTA价格历史记录表（定时采集+告警引擎共用）
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
        );

        -- 报表发送状态表（飞书早报日级去重）
        CREATE TABLE IF NOT EXISTS report_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_name TEXT NOT NULL,
            last_sent_date TEXT NOT NULL,
            UNIQUE(report_name)
        );

    """
    )
    conn.commit()

    # ── 迁移：为旧表补加 hotel_id 列（兼容已有数据库，必须在索引创建前执行）──
    _migrate_add_column(conn, "daily_metrics", "hotel_id", "INTEGER DEFAULT 1")
    _migrate_add_column(conn, "price_decisions", "hotel_id", "INTEGER DEFAULT 1")
    _migrate_add_column(conn, "competitor_prices", "hotel_id", "INTEGER DEFAULT 1")
    _migrate_add_column(conn, "marketing_log", "hotel_id", "INTEGER DEFAULT 1")
    _migrate_add_column(conn, "decision_log", "hotel_id", "INTEGER DEFAULT 1")
    _migrate_add_column(conn, "budget_targets", "hotel_id", "INTEGER DEFAULT 1")
    # 客源细分：guest_profiles 扩段（幂等，已存在则跳过）
    _migrate_add_column(conn, "guest_profiles", "segment_type", "TEXT")
    _migrate_add_column(conn, "guest_profiles", "avg_stay_length", "REAL DEFAULT 0")

    # ── 业务索引（在列迁移之后创建，确保 hotel_id 已存在）──
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_dm_hotel_date ON daily_metrics(hotel_id, date);
        CREATE INDEX IF NOT EXISTS idx_cp_lookup ON competitor_prices(fetch_date, checkin_date, hotel_name);
        CREATE INDEX IF NOT EXISTS idx_cp_hotel_date ON competitor_prices(hotel_name, checkin_date);
        CREATE INDEX IF NOT EXISTS idx_pd_hotel_date ON price_decisions(hotel_id, date);
        CREATE INDEX IF NOT EXISTS idx_bt_hotel_ym ON budget_targets(hotel_id, year, month);
        CREATE INDEX IF NOT EXISTS idx_ml_hotel_date ON marketing_log(hotel_id, target_date);
        CREATE INDEX IF NOT EXISTS idx_bp_stay_snapshot ON booking_pace(stay_date, snapshot_date);
        CREATE INDEX IF NOT EXISTS idx_bp_hotel_stay ON booking_pace(hotel_id, stay_date);
        CREATE INDEX IF NOT EXISTS idx_cm_hotel_date ON channel_mix(hotel_id, date);
        CREATE INDEX IF NOT EXISTS idx_ae_hotel_time ON alerts_events(hotel_id, event_time);
        CREATE INDEX IF NOT EXISTS idx_sm_date_seg ON segment_mix(hotel_id, date, segment_type);
        CREATE INDEX IF NOT EXISTS idx_gp_segment ON guest_profiles(hotel_id, segment_type);
        CREATE INDEX IF NOT EXISTS idx_ota_date ON ota_price_history(hotel_name, fetch_date);
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
            ("九寨沟诺富特酒店", 4, "九寨沟", "九寨沟县", 600),
            ("九寨沟万怡酒店", 4, "九寨沟", "九寨沟县", 650),
            ("九寨沟德尔塔酒店", 5, "九寨沟", "九寨沟县", 800),
            ("全季酒店九寨沟九寨大道店", 3, "九寨沟", "九寨沟县南坪镇滨江路2号", 350),
        ]
        for comp in default_competitors:
            conn.execute(
                "INSERT INTO competitive_set (hotel_name, star_level, city, address, base_price) VALUES (?,?,?,?,?)",
                comp,
            )
        conn.commit()


def init_db():
    """Initialize all table structures (public API, backward compatible).
    Table creation is now integrated into get_conn() lazy initialization.
    This function ensures explicit calls also trigger initialization.
    """
    get_conn().close()


# ═══════════════════════════════════════════════════════════════
# 日常指标 CRUD
# ═══════════════════════════════════════════════════════════════

def save_daily_metrics(metrics: dict) -> int:
    """保存或更新单日经营指标。"""
    conn = get_conn()
    payload = {"hotel_id": 1, "source": "manual", **metrics}
    keys = list(payload)
    updates = [key for key in keys if key not in {"hotel_id", "date", "source"}]
    try:
        if updates:
            result = conn.execute(
                f"UPDATE daily_metrics SET {', '.join(f'{key}=?' for key in updates)} "
                "WHERE hotel_id=? AND date=? AND source=?",
                [payload[key] for key in updates] + [payload["hotel_id"], payload["date"], payload["source"]],
            )
        else:
            result = conn.execute(
                "SELECT 1 FROM daily_metrics WHERE hotel_id=? AND date=? AND source=?",
                (payload["hotel_id"], payload["date"], payload["source"]),
            )
        if result.rowcount == 0:
            conn.execute(
                f"INSERT INTO daily_metrics ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})",
                [payload[key] for key in keys],
            )
        conn.commit()
    finally:
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
    values = (targets.get("occ"), targets.get("adr"), targets.get("revpar"),
              targets.get("revenue"), targets.get("gop_rate"), 1, year, month)
    try:
        result = conn.execute(
            """UPDATE budget_targets
               SET target_occ=?, target_adr=?, target_revpar=?, target_revenue=?, target_gop_rate=?
               WHERE hotel_id=? AND year=? AND month=?""",
            values,
        )
        if result.rowcount == 0:
            conn.execute(
                """INSERT INTO budget_targets
                   (hotel_id, year, month, target_occ, target_adr, target_revpar, target_revenue, target_gop_rate)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (1, year, month, *values[:5]),
            )
        conn.commit()
    finally:
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


# ═══════════════════════════════════════════════════════════════
# 客源细分（segment_mix / report_state）
# ═══════════════════════════════════════════════════════════════

def save_segment_mix(rows: list[dict]):
    """批量写入客源细分汇总（按 日期+客源类型+渠道+来源 幂等覆盖）。"""
    conn = get_conn()
    for r in rows:
        conn.execute(
            """INSERT INTO segment_mix
               (hotel_id, date, segment_type, channel, customer_count,
                room_nights, revenue, commission, avg_stay_length, source)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(hotel_id, date, segment_type, channel, source) DO UPDATE SET
                 customer_count=excluded.customer_count,
                 room_nights=excluded.room_nights,
                 revenue=excluded.revenue,
                 commission=excluded.commission,
                 avg_stay_length=excluded.avg_stay_length,
                 source=excluded.source,
                 created_at=(datetime('now','localtime'))""",
            (r.get("hotel_id", 1), r["date"], r["segment_type"], r.get("channel", ""),
             r.get("customer_count", 0), r.get("room_nights", 0), r.get("revenue", 0),
             r.get("commission", 0), r.get("avg_stay_length", 0), r.get("source", "manual")),
        )
    conn.commit()
    conn.close()


def get_segment_mix(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """读取客源细分数据（可按日期区间过滤）。"""
    conn = get_conn()
    if start_date and end_date:
        df = pd.read_sql_query(
            "SELECT * FROM segment_mix WHERE date BETWEEN ? AND ? ORDER BY date, segment_type",
            conn, params=(start_date, end_date),
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM segment_mix ORDER BY date, segment_type", conn
        )
    conn.close()
    return df


def mark_report_sent(report_name: str, sent_date: str):
    """记录报表发送状态（UPSERT）。"""
    conn = get_conn()
    conn.execute(
        """INSERT INTO report_state (report_name, last_sent_date) VALUES (?,?)
           ON CONFLICT(report_name) DO UPDATE SET last_sent_date=excluded.last_sent_date""",
        (report_name, sent_date),
    )
    conn.commit()
    conn.close()


def get_report_state(report_name: str) -> str | None:
    """查询报表上次发送日期，None 表示从未发送。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT last_sent_date FROM report_state WHERE report_name=?", (report_name,)
    ).fetchone()
    conn.close()
    return row["last_sent_date"] if row else None


if __name__ == "__main__":
    init_db()
    print(f"数据库已初始化: {DB_PATH}")
