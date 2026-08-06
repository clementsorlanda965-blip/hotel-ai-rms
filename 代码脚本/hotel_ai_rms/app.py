"""
Hotel AI-RMS (AI收益增长飞轮)  v2.0
══════════════════════════════════════════════════════════════
酒店AI智能收益管理驾驶舱 — 知客→定价→竞品监控→触达→数据回流
AI创新大赛现场演示，单机运行，无需外部数据库/API
══════════════════════════════════════════════════════════════
启动: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
from datetime import datetime, timedelta, date
from io import BytesIO
from pathlib import Path
import warnings
import copy
import re
import time
import subprocess
import sys
import os

warnings.filterwarnings("ignore")

# 导入本项目的持久化与BI模块
try:
    from database import (
        init_db, get_summary_stats, get_latest_metrics,
        save_price_decision, get_price_decisions, get_adoption_rate,
        get_competitive_set, add_competitor, remove_competitor,
        save_competitor_prices, get_competitor_prices,
        log_decision as db_log_decision, get_decision_logs,
        save_daily_metrics,
    )
    _DB_READY = True
except ImportError:
    _DB_READY = False

try:
    from bi_reports import (
        generate_sample_data, generate_excel_report, gop_deep_dive,
        generate_channel_analysis, compute_kpi_summary, rate_kpi,
        load_from_database,
    )
    _BI_READY = True
except ImportError:
    _BI_READY = False

# ══════════════════════════════════════════════════════════════
# Page Config
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Hotel AI-RMS | 收益管理驾驶舱",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════
# Custom CSS — 深蓝 + 金色专业主题
# ══════════════════════════════════════════════════════════════
st.markdown(
    """
<style>
    /* ── 全局 ── */
    .stApp { background: linear-gradient(135deg, #0a1628 0%, #132240 100%); }
    .main .block-container { padding-top: 1rem; padding-bottom: 0.5rem; }
    section[data-testid="stSidebar"] { display: none; }

    /* ── 标题栏 ── */
    .title-bar {
        background: linear-gradient(90deg, #0d1f3c 0%, #1a3a6b 50%, #0d1f3c 100%);
        border-bottom: 3px solid #c8963e;
        padding: 18px 30px; text-align: center; margin-bottom: 8px; border-radius: 8px;
    }
    .title-bar h1 { color:#fff; font-size:28px; font-weight:700; margin:0; letter-spacing:2px; }
    .title-bar .sub { color:#c8963e; font-size:13px; letter-spacing:4px; margin-top:4px; }

    /* ── Tab 栏覆写 ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: #0d1f3c; border-radius: 10px; padding: 4px;
        border: 1px solid #2a4a6d;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8899bb !important; font-weight: 600; font-size: 14px;
        border-radius: 8px; padding: 10px 20px; letter-spacing: 1px;
        transition: all 0.3s;
    }
    .stTabs [data-baseweb="tab"]:hover { background: rgba(200,150,62,0.1); color: #c8963e !important; }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #c8963e, #a67c2e) !important;
        color: #0a1628 !important;
    }

    /* ── 卡片 ── */
    .card {
        background: linear-gradient(135deg, #142642 0%, #1a3050 100%);
        border: 1px solid #2a4a6d; border-radius: 10px; padding: 16px;
        margin-bottom: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .card-accent { border-left: 3px solid #c8963e; }
    .card-green { border-left: 3px solid #28a745; }
    .card-red { border-left: 3px solid #dc3545; }

    /* ── 统计卡片 ── */
    .stat-card {
        background: linear-gradient(135deg, #0f2040 0%, #183050 100%);
        border: 1px solid #2a4a6d; border-radius: 10px; padding: 12px 14px;
        text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .stat-card .val { font-size:28px; font-weight:800; color:#c8963e; line-height:1.2; }
    .stat-card .lbl { font-size:11px; color:#8899bb; margin-top:3px; }
    .stat-card .delta { font-size:10px; color:#28a745; margin-top:1px; }

    /* ── KPI ── */
    .kpi-row { display:flex; gap:10px; margin:8px 0; }
    .kpi-card {
        flex:1; background:linear-gradient(135deg,#0d1f3c,#162d50);
        border:1px solid #2a4a6d; border-radius:10px; padding:14px; text-align:center;
    }
    .kpi-card .kv { font-size:26px; font-weight:800; color:#c8963e; }
    .kpi-card .kl { font-size:11px; color:#8899bb; }

    /* ── 按钮 ── */
    .stButton > button {
        background: linear-gradient(135deg, #c8963e, #a67c2e); color:#0a1628;
        border:none; border-radius:6px; font-weight:700; font-size:14px;
        padding:8px 20px; letter-spacing:1px; transition:all 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #d4a54e, #b88c38);
        box-shadow:0 4px 15px rgba(200,150,62,0.4); transform:translateY(-1px);
    }
    .demo-btn > button {
        background: linear-gradient(135deg, #28a745, #1e7e34) !important;
        color:#fff !important; font-size:16px !important; padding:12px 30px !important;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { box-shadow:0 0 0 0 rgba(40,167,69,0.5); }
        70% { box-shadow:0 0 0 15px rgba(40,167,69,0); }
        100% { box-shadow:0 0 0 0 rgba(40,167,69,0); }
    }

    /* ── OTA 标签 ── */
    .ota-tag {
        display:inline-block; padding:2px 8px; border-radius:10px;
        font-size:10px; font-weight:700; margin:1px;
    }
    .ota-ctrip { background:#0066cc; color:#fff; }
    .ota-meituan { background:#ffc700; color:#000; }
    .ota-fliggy { background:#ff5000; color:#fff; }
    .ota-qunar { background:#1976d2; color:#fff; }
    .ota-tongcheng { background:#07c160; color:#fff; }
    .ota-elong { background:#e60044; color:#fff; }

    /* ── 徽章 ── */
    .badge {
        display:inline-block; padding:2px 8px; border-radius:10px;
        font-size:10px; font-weight:700;
    }
    .badge-lowest { background:rgba(40,167,69,0.2); color:#28a745; border:1px solid #28a745; }
    .badge-warn { background:rgba(220,53,69,0.2); color:#dc3545; border:1px solid #dc3545; }
    .price-badge-adopted {
        display:inline-block; background:#c8963e; color:#0a1628;
        font-size:10px; font-weight:700; padding:2px 8px; border-radius:10px; margin-left:4px;
    }

    /* ── 消息卡片 ── */
    .msg-card {
        background:linear-gradient(135deg,#142642,#1e3555);
        border:1px solid #2a4a6d; border-radius:8px; padding:12px;
        margin:6px 0; font-size:13px; line-height:1.6; color:#d0d8e8;
    }
    .channel-tag {
        display:inline-block; background:#1e3a5c; color:#c8963e;
        font-size:10px; padding:3px 10px; border-radius:12px; margin-top:4px;
    }

    /* ── 分区标题 ── */
    .section-title {
        font-size:17px; font-weight:700; color:#c8963e;
        border-bottom:2px solid #c8963e; padding-bottom:6px; margin-bottom:10px; letter-spacing:1px;
    }

    /* ── 原生组件覆写 ── */
    .stDataFrame, .stTable { background:#142642; }
    div[data-testid="stMetricValue"] { color:#c8963e !important; font-weight:800 !important; }
    div[data-testid="stMetricLabel"] { color:#8899bb !important; }

    /* ── 日志时间线 ── */
    .timeline-item {
        display:flex; gap:12px; padding:10px 0; border-left:2px solid #2a4a6d;
        margin-left:10px; padding-left:16px; position:relative;
    }
    .timeline-item::before {
        content:''; position:absolute; left:-6px; top:14px;
        width:10px; height:10px; border-radius:50%; background:#c8963e;
    }
    .timeline-item.adopted::before { background:#28a745; }
    .timeline-item.sent::before { background:#3b82f6; }

    /* ── 成功动画 ── */
    .success-toast {
        background:#1a3a2a; border:1px solid #28a745; color:#28a745;
        padding:12px 20px; border-radius:8px; font-weight:700; text-align:center;
        animation:fadeIn 0.5s ease;
    }
    @keyframes fadeIn {
        from { opacity:0; transform:translateY(-10px); }
        to { opacity:1; transform:translateY(0); }
    }
</style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════
# ─── 数据生成：客户数据库 (≥220位) ───
# 价值：精准客群分层是收益管理第一步，知客方能定价
# ══════════════════════════════════════════════════════════════

_SURNAMES = [
    "王","李","张","刘","陈","杨","黄","赵","周","吴",
    "徐","孙","马","朱","胡","郭","何","林","罗","高",
    "梁","郑","谢","宋","唐","韩","冯","于","董","萧",
    "程","曹","袁","邓","许","傅","沈","曾","彭","吕",
]
_GIVEN_M = ["伟","强","磊","军","勇","涛","明","辉","鹏","浩","杰","峰","宇","超","波","东","刚","斌","文","华"]
_GIVEN_F = ["芳","敏","静","丽","婷","雪","琳","玲","颖","娜","萍","燕","霞","洁","菲","娟","莉","秀","云","慧"]
_GIVEN_N = ["睿","洋","博","思","远","宁","然","月","安","晨"]

PREFS = ["商务大床房","行政套房","豪华双床房","亲子家庭房","主题特色房","标准大床房","海景大床房"]
CHANNELS = ["携程","美团","飞猪","官方小程序","抖音团购","Booking.com","前台散客","企业协议"]
KWP = ["服务周到","位置优越","性价比高","干净整洁","早餐丰盛","升级惊喜","设施新"]
KWN = ["中规中矩","房价适中","周边一般","停车困难","电梯慢","房间偏小"]
KWNG = ["噪音大","热水不稳","床品老旧","前台态度差","虚假宣传","卫生堪忧"]

CHURN_MULT = 1.5
AVG_INT = 68


@st.cache_data
def generate_customer_data(n: int = 220) -> pd.DataFrame:
    """生成模拟客户数据库。"""
    random.seed(42); np.random.seed(42)
    today = date.today()
    rows = []
    for i in range(1, n + 1):
        gender = random.choice(["男","女","女"])
        surname = random.choice(_SURNAMES)
        given = random.choice(_GIVEN_M + _GIVEN_N) if gender == "男" else random.choice(_GIVEN_F + _GIVEN_N)
        name = surname + given
        age = int(np.random.normal(38, 12)); age = max(18, min(75, age))
        r = random.random()
        tier = "钻石" if r < 0.05 else ("金卡" if r < 0.18 else ("银卡" if r < 0.45 else "普通"))
        bs = {"钻石": (50000,200000),"金卡":(20000,80000),"银卡":(8000,30000),"普通":(500,12000)}[tier]
        total_spend = round(random.uniform(*bs), 2)
        avg_int = int(np.random.normal(AVG_INT, 25)); avg_int = max(15, min(200, avg_int))
        dsl = int(np.random.exponential(avg_int * 0.7)); dsl = min(400, dsl)
        last_stay = today - timedelta(days=dsl)
        pref = random.choice(PREFS)
        chw = [0.28,0.20,0.15,0.12,0.10,0.06,0.05,0.04]
        channel = random.choices(CHANNELS, weights=chw, k=1)[0]
        has_comp = random.random() < 0.12
        nkw = random.randint(1, 3)
        all_kw = KWP + KWN + KWNG
        keywords = ", ".join(random.sample(all_kw, nkw))
        if any(k in keywords for k in KWNG):
            sent = "负面" if random.random() < 0.8 else "中性"
        elif any(k in keywords for k in KWP):
            sent = "正面" if random.random() < 0.85 else "中性"
        else:
            sent = random.choice(["正面","中性","中性"])
        rows.append({
            "客户ID": f"CUST{i:04d}", "姓名": name, "性别": gender,
            "年龄": age, "会员等级": tier, "总消费金额": total_spend,
            "最近入住": last_stay, "平均间隔天数": avg_int,
            "偏好房型": pref, "预订渠道": channel,
            "曾投诉": has_comp, "评论关键词": keywords, "情感标签": sent,
        })
    df = pd.DataFrame(rows)
    df["最近入住"] = pd.to_datetime(df["最近入住"])
    df["流失风险"] = ((today - df["最近入住"].dt.date).dt.days > df["平均间隔天数"] * CHURN_MULT)
    df["价格敏感"] = df.apply(_is_price_sensitive, axis=1)
    df["高价值"] = df["总消费金额"] >= df["总消费金额"].quantile(0.8)
    return df


def _is_price_sensitive(row):
    sk = ["性价比高","房价适中","价格"]
    kwm = any(k in str(row["评论关键词"]) for k in sk)
    return kwm or (row["总消费金额"] < 30000 and random.random() < 0.4)


# ══════════════════════════════════════════════════════════════
# ─── 价格日历 ───
# 价值：动态定价替代人工拍脑袋，最大化每间可卖房收入
# ══════════════════════════════════════════════════════════════

@st.cache_data
def generate_price_calendar(start_date: date, days: int = 90) -> pd.DataFrame:
    """未来90天动态价格日历。"""
    random.seed(77); np.random.seed(77)
    bp = random.uniform(380, 680)

    event_desc = {}
    event_impact = {}

    for d in range(days):
        cur = start_date + timedelta(days=d)
        dow = cur.weekday()
        if dow >= 5:
            event_desc[cur] = "周末出游需求上升，周边酒店入住率预计85%+"
            event_impact[cur] = random.uniform(0.10, 0.25)
        elif dow == 0:
            event_desc[cur] = "周一商务出行回落，需求偏弱"
            event_impact[cur] = random.uniform(-0.10, 0.00)
        else:
            event_desc[cur] = "平日正常需求"
            event_impact[cur] = random.uniform(-0.03, 0.05)

    festivals = {
        start_date + timedelta(days=25): ("动漫节期间，周边酒店已涨价20%+，客流激增", random.uniform(0.20,0.30)),
        start_date + timedelta(days=26): ("动漫节第二天，热度不减", random.uniform(0.18,0.28)),
        start_date + timedelta(days=27): ("动漫节最后一天，晚间散场需求", random.uniform(0.10,0.20)),
        start_date + timedelta(days=55): ("音乐节周末，周边酒店满房率95%", random.uniform(0.22,0.30)),
        start_date + timedelta(days=56): ("音乐节第二日，余热未消", random.uniform(0.15,0.25)),
        start_date + timedelta(days=48): ("节后淡季开始，竞对已降价10-15%抢客", random.uniform(-0.15,-0.08)),
        start_date + timedelta(days=49): ("淡季持续，出租率预计仅45%", random.uniform(-0.18,-0.10)),
        start_date + timedelta(days=50): ("淡季第三日，库存压力大", random.uniform(-0.20,-0.12)),
        start_date + timedelta(days=72): ("本地商务会议，协议客户集中入住", random.uniform(0.08,0.15)),
        start_date + timedelta(days=73): ("商务会议第二日", random.uniform(0.05,0.12)),
    }
    for dt, (desc, imp) in festivals.items():
        if start_date <= dt < start_date + timedelta(days=days):
            event_desc[dt] = desc
            event_impact[dt] = imp

    rows = []
    for d in range(days):
        cur = start_date + timedelta(days=d)
        impact = event_impact.get(cur, 0.0) + random.uniform(-0.02, 0.02)
        sp = round(bp * (1 + impact), -1)
        sp = max(180, min(1200, sp))
        occ_b = 0.68 + impact * 1.5 + random.uniform(-0.05, 0.05)
        if cur.weekday() >= 5: occ_b += 0.12
        occ_b = max(0.25, min(0.98, occ_b))
        zone = "提价区" if impact >= 0.10 else ("降价区" if impact <= -0.08 else "平价区")
        rows.append({
            "日期": cur,
            "星期": ["一","二","三","四","五","六","日"][cur.weekday()],
            "基础价": round(bp, -1),
            "价格浮动": round(impact * 100, 1),
            "建议房价": sp,
            "预测出租率": round(occ_b * 100, 1),
            "决策依据": event_desc[cur],
            "颜色区域": zone,
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# ─── OTA竞品数据：九寨沟酒店 ───
# 价值：竞品价格是定价的锚，知己知彼方能科学定价
# ══════════════════════════════════════════════════════════════

# 九寨沟酒店基础价 —— 基于网络公开信息校准（淡季/标准房型参考价）
# 旺季(4-5月/9-10月)约为基础价×1.5-2.0，暑期(7-8月)×1.3-1.5，淡季(11-3月)×0.6-0.8
# 数据来源：Trip.com公开价格 + 携程搜索页价格区间 + 什么值得买历史促销价
JIUZHAIGOU_HOTELS = [
    {"名称":"九寨沟悦榕庄","星级":5,"基础价":1600,"地址":"漳扎镇","房间":["大床房","套房","别墅"]},
    {"名称":"九寨沟希尔顿度假酒店","星级":5,"基础价":1100,"地址":"漳扎镇","房间":["大床房","双床房","套房"]},
    {"名称":"九寨沟天堂洲际大饭店","星级":5,"基础价":1350,"地址":"漳扎镇甘海子","房间":["大床房","套房","行政房"]},
    {"名称":"九寨沟喜来登国际大酒店","星级":5,"基础价":950,"地址":"漳扎镇","房间":["大床房","双床房","套房","行政房"]},
    {"名称":"九寨沟天源豪生度假酒店","星级":5,"基础价":850,"地址":"漳扎镇","房间":["大床房","双床房","套房"]},
    {"名称":"九寨沟金龙国际度假酒店","星级":5,"基础价":750,"地址":"漳扎镇","房间":["大床房","双床房","亲子房"]},
    {"名称":"九寨沟亚朵酒店","星级":4,"基础价":500,"地址":"漳扎镇","房间":["大床房","双床房","亲子房"]},
    {"名称":"星程酒店(九寨沟风景区店)","星级":4,"基础价":430,"地址":"漳扎镇","房间":["大床房","双床房","套房"]},
    {"名称":"全季酒店(九寨沟景区店)","星级":4,"基础价":380,"地址":"漳扎镇","房间":["大床房","双床房"]},
    {"名称":"九寨度假村酒店","星级":4,"基础价":550,"地址":"漳扎镇彭丰村","房间":["大床房","双床房","套房","亲子房"]},
    {"名称":"汉庭酒店(九寨沟景区店)","星级":3,"基础价":240,"地址":"漳扎镇","房间":["大床房","双床房"]},
    {"名称":"如家精选酒店(九寨沟店)","星级":3,"基础价":220,"地址":"漳扎镇","房间":["大床房","双床房","亲子房"]},
    {"名称":"九寨沟眼境民宿","星级":3,"基础价":170,"地址":"景区入口附近","房间":["大床房","标准间"]},
    {"名称":"九寨沟云居客栈","星级":3,"基础价":200,"地址":"景区入口附近","房间":["大床房","标准间"]},
    {"名称":"九寨沟喇嘛岭寺客栈","星级":3,"基础价":150,"地址":"漳扎镇","房间":["标准间","大床房"]},
]

# 默认OTA平台列表
OTA_PLATFORMS = ["携程","美团","飞猪","去哪儿","同程","艺龙"]
OTA_BIAS = {
    "携程": {"commission":0.15,"priceBias":1.00},
    "美团": {"commission":0.12,"priceBias":0.97},
    "飞猪": {"commission":0.10,"priceBias":0.95},
    "去哪儿":{"commission":0.13,"priceBias":0.93},
    "同程": {"commission":0.11,"priceBias":0.96},
    "艺龙": {"commission":0.14,"priceBias":0.98},
}

OTA_PLATFORMS = ["携程","美团","飞猪","去哪儿","同程","艺龙"]
OTA_BIAS = {
    "携程": {"commission":0.15,"priceBias":1.00},
    "美团": {"commission":0.12,"priceBias":0.97},
    "飞猪": {"commission":0.10,"priceBias":0.95},
    "去哪儿":{"commission":0.13,"priceBias":0.93},
    "同程": {"commission":0.11,"priceBias":0.96},
    "艺龙": {"commission":0.14,"priceBias":0.98},
}

@st.cache_data
def generate_ota_prices(
    checkin: date = None, nights: int = 1, star_filter: str = "all", room_filter: str = "all"
) -> pd.DataFrame:
    """生成九寨沟OTA全网比价数据（模拟参考价 - 基于公开信息校准）。"""
    random.seed(99); np.random.seed(99)
    if checkin is None: checkin = date.today() + timedelta(days=3)
    ci = checkin
    m = ci.month
    # 季节系数：旺季×1.6, 暑期×1.35, 淡季×0.7
    season = 1.6 if m in (4,5,9,10) else (1.35 if m in (7,8) else (0.7 if m in (1,2,12) else 0.9))
    if ci.weekday() >= 5: season *= 1.12

    rows = []
    for h in JIUZHAIGOU_HOTELS:
        if star_filter != "all" and h["星级"] != int(star_filter): continue
        rooms = h["房间"] if room_filter == "all" else [r for r in h["房间"] if room_filter in r]
        if not rooms: continue  # 该酒店无此房型则跳过
        for room in rooms:
            rc = 1.6 if ("套房" in room or "别墅" in room) else (1.4 if "行政" in room else (1.25 if "亲子" in room else (1.1 if "双床" in room else 1.0)))
            for plat, bias in OTA_BIAS.items():
                noise = 1 + (random.random() - 0.5) * 0.10
                price = round(h["基础价"] * season * rc * bias["priceBias"] * noise / 10) * 10
                price = max(80, price)
                total = price * nights
                # 高星酒店默认含早概率高
                has_bf = "是" if (h["星级"] >= 4 and random.random() > 0.25) or (h["星级"] >= 5) else ("是" if random.random() > 0.55 else "否")
                can_cancel = "是" if price > 500 and random.random() > 0.3 or random.random() > 0.75 else "否"
                rows.append({
                    "酒店名称": h["名称"], "星级": h["星级"], "地址": h["地址"],
                    "房型": room, "OTA平台": plat, "单价_晚": price,
                    "总价": total, "含早": has_bf,
                    "可取消": can_cancel, "入住日期": checkin,
                    "离店日期": checkin + timedelta(days=nights), "晚数": nights,
                    "数据来源": "模拟参考" if "模拟参考" in locals() else "模拟参考",
                })
    return pd.DataFrame(rows)


def merge_ota_data(sim_df: pd.DataFrame, real_df: pd.DataFrame) -> pd.DataFrame:
    """合并模拟参考价与用户导入的真实价格，真实价格覆盖同酒店+房型+平台的模拟值。"""
    if real_df is None or real_df.empty:
        return sim_df
    # 标准化的关键列检查
    req_cols = ["酒店名称","房型","OTA平台","单价_晚"]
    for c in req_cols:
        if c not in real_df.columns:
            st.warning(f"导入文件缺少「{c}」列，请检查格式。已回退到模拟参考价。")
            return sim_df
    # 构建去重键
    key_cols = ["酒店名称","房型","OTA平台"]
    real_df["_key"] = real_df[key_cols].apply(lambda r: "|".join(r.astype(str)), axis=1)
    sim_df["_key"] = sim_df[key_cols].apply(lambda r: "|".join(r.astype(str)), axis=1)
    # 用真实数据覆盖
    real_keys = set(real_df["_key"])
    merged = sim_df[~sim_df["_key"].isin(real_keys)].copy()
    real_copy = real_df.copy()
    for c in sim_df.columns:
        if c not in real_copy.columns:
            real_copy[c] = ""
    merged = pd.concat([merged, real_copy], ignore_index=True)
    merged.drop(columns=["_key"], inplace=True, errors="ignore")
    # 确保数字类型
    if "单价_晚" in merged.columns:
        merged["单价_晚"] = pd.to_numeric(merged["单价_晚"], errors="coerce").fillna(0).astype(int)
    if "总价" in merged.columns:
        merged["总价"] = pd.to_numeric(merged["总价"], errors="coerce").fillna(0).astype(int)
    return merged


# ══════════════════════════════════════════════════════════════
# ─── 营销文案生成 ───
# 价值：千人千面精准营销，转化率比群发高3-5倍
# ══════════════════════════════════════════════════════════════

def _pronoun(name, gender):
    return f"{name}女士" if gender == "女" else f"{name}先生"


def generate_marketing_message(cust, dt_obj, event_hint):
    pronoun = _pronoun(cust["姓名"], cust["性别"])
    ps, hv, tier, ch = cust["价格敏感"], cust["高价值"], cust["会员等级"], cust["预订渠道"]
    is_churn = cust["流失风险"]
    pref = cust.get("偏好房型", "标准大床房")

    # 权益匹配
    if ps and is_churn:
        benefit, btype = "专属回归礼遇：满500减80定向券 + 延迟退房至14:00", "满减券"
    elif ps:
        benefit, btype = "限时闪促：预订即享7折早鸟价 + 免费升级同价位房型", "折扣"
    elif hv and tier in ("钻石","金卡"):
        benefit, btype = "VIP尊享：免费升房至行政套房 + 双人行政酒廊礼遇", "升房体验"
    elif is_churn:
        benefit, btype = "唤醒礼包：回归首单立减100元 + 双倍积分", "满减券"
    elif tier in ("金卡","钻石"):
        benefit, btype = "会员专属：预订享优先升房 + 迎宾果盘", "升房体验"
    else:
        benefit, btype = "限时优惠：房价9折 + 免费早餐一份", "折扣"

    ds = dt_obj.strftime("%m月%d日")
    if "动漫" in event_hint:
        dh, dh2 = f"恰逢{ds}动漫节", f"{ds}动漫节期间专享接驳车服务"
    elif "音乐节" in event_hint:
        dh, dh2 = f"锁定{ds}音乐节", f"{ds}专享演出场馆免费接驳"
    elif "商务" in event_hint or "会议" in event_hint:
        dh, dh2 = f"{ds}商务出行优选", "会议期间专属商务楼层服务"
    elif "淡季" in event_hint:
        dh, dh2 = "错峰出游正当时", f"{ds}静享悠闲入住体验"
    elif dt_obj.weekday() >= 5:
        dh, dh2 = f"{ds}周末小憩", f"周末入住享{pref}专属价"
    else:
        dh2 = f"平日入住享{pref}安静楼层"
        dh = f"{ds}周{['一','二','三','四','五','六','日'][dt_obj.weekday()]}"

    chmap = {"携程":"App推送+站内信","美团":"App推送","飞猪":"App推送+短信",
             "官方小程序":"微信服务通知","抖音团购":"抖音私信","Booking.com":"邮件",
             "前台散客":"短信","企业协议":"企业微信"}
    sug_ch = chmap.get(ch, "短信")

    greetings = [f"{dh}，{pronoun}您好！", f"{pronoun}，{dh}的专属礼遇已就位！"]
    body_tpls = [
        f"我们为您准备了{benefit}。{dh2}，期待为您提供一如既往的贴心服务。",
        f"为回馈{'您长期的支持' if hv else '您的信任'}，特别呈上{benefit}。{dh2}。",
    ]
    msg = f"{random.choice(greetings)}\n{random.choice(body_tpls)}"
    return {
        "客户ID": cust["客户ID"], "称呼": pronoun,
        "日期": dt_obj.strftime("%Y-%m-%d"), "消息内容": msg,
        "权益类型": btype, "建议渠道": sug_ch,
    }


# ══════════════════════════════════════════════════════════════
# ─── 决策日志 ───
# 价值：全流程数据回流，形成AI决策→执行→效果验证闭环
# ══════════════════════════════════════════════════════════════

if "decision_log" not in st.session_state:
    st.session_state["decision_log"] = []


def log_decision(action_type: str, detail: str, impact: str = ""):
    """记录AI决策到日志。"""
    st.session_state["decision_log"].append({
        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "类型": action_type,
        "详情": detail,
        "预计影响": impact,
    })
    # 保留最近50条
    if len(st.session_state["decision_log"]) > 50:
        st.session_state["decision_log"] = st.session_state["decision_log"][-50:]


# ══════════════════════════════════════════════════════════════
# Session State 初始化
# ══════════════════════════════════════════════════════════════
if "adopted_prices" not in st.session_state:
    st.session_state["adopted_prices"] = {}
if "sent_messages" not in st.session_state:
    st.session_state["sent_messages"] = set()
if "generated_messages" not in st.session_state:
    st.session_state["generated_messages"] = []
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = None
if "show_success" not in st.session_state:
    st.session_state["show_success"] = False
if "marketing_target_date" not in st.session_state:
    st.session_state["marketing_target_date"] = None
if "demo_active" not in st.session_state:
    st.session_state["demo_active"] = False
if "msg_page" not in st.session_state:
    st.session_state["msg_page"] = 0
if "ota_scraped" not in st.session_state:
    st.session_state["ota_scraped"] = False
if "ota_imported_df" not in st.session_state:
    st.session_state["ota_imported_df"] = None  # 用户导入的真实价格DataFrame
if "ota_data_source" not in st.session_state:
    st.session_state["ota_data_source"] = "模拟参考"  # "模拟参考" | "CSV导入" | "混合"
if "manual_prices" not in st.session_state:
    st.session_state["manual_prices"] = {}  # {key: price} 手动录入缓存


def activate_demo(customers_df, calendar_df):
    """一键演示：客群→定价→营销 全闭环。"""
    st.session_state["demo_active"] = True
    st.session_state["generated_messages"] = []
    st.session_state["show_success"] = False
    # 找降价日
    red = calendar_df[calendar_df["颜色区域"] == "降价区"]
    if not red.empty:
        target = red.iloc[0]
        st.session_state["selected_date"] = target["日期"]
        st.session_state["marketing_target_date"] = target["日期"]
    log_decision("演示路径", "一键启动AI收益飞轮闭环演示", "预计增收+12%")


def csv_download_button(df, filename, label="📥 下载CSV"):
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(label=label, data=csv_bytes, file_name=filename, mime="text/csv")


# ══════════════════════════════════════════════════════════════
# ─── 日历热力图 ───
# ══════════════════════════════════════════════════════════════

def build_calendar_matrix(cal_df, adopted):
    start = cal_df["日期"].min()
    cal_start = start - timedelta(days=start.weekday())
    total_days = (cal_df["日期"].max() - cal_start).days + 1
    nw = (total_days + 6) // 7

    z = np.full((nw, 7), np.nan)
    txt = np.full((nw, 7), "", dtype=object)
    hover = np.full((nw, 7), "", dtype=object)

    for _, row in cal_df.iterrows():
        d = row["日期"]
        offset = (d - cal_start).days
        wi, di = offset // 7, offset % 7
        if 0 <= wi < nw:
            z[wi, di] = row["价格浮动"]
            ap = adopted.get(d.strftime("%Y-%m-%d"))
            mark = " ✓" if ap else ""
            txt[wi, di] = f"{d.day}{mark}"
            hover[wi, di] = (
                f"{d.strftime('%m月%d日')} 周{row['星期']}<br>"
                f"建议: ¥{row['建议房价']}{f' 已采纳¥{ap}' if ap else ''}<br>"
                f"浮动: {row['价格浮动']:+.1f}% | 出租率: {row['预测出租率']}%<br>"
                f"<i>{row['决策依据'][:45]}...</i>"
            )

    wl = []
    for w in range(nw):
        ws = cal_start + timedelta(days=w*7)
        we = ws + timedelta(days=6)
        m1, d1 = ws.month, ws.day
        m2, d2 = we.month, we.day
        wl.append(f"{m1}月{d1}-{m2}月{d2}日" if m1 != m2 else f"{m1}月{d1}-{d2}日")

    return z, txt, hover, wl


def plot_calendar_heatmap(cal_df, adopted):
    z, txt, hover, wl = build_calendar_matrix(cal_df, adopted)
    mask = ~np.isnan(z)

    hover_2d = []
    for i in range(hover.shape[0]):
        row_list = []
        for j in range(hover.shape[1]):
            row_list.append([hover[i, j] if hover[i, j] else ""])
        hover_2d.append(row_list)

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=np.where(mask, z, None),
        x=["周一","周二","周三","周四","周五","周六","周日"],
        y=wl,
        text=np.where(mask, txt, ""),
        texttemplate="%{text}",
        textfont={"size": 10, "color": "#ffffff"},
        colorscale=[
            [0.0,"#dc3545"],[0.25,"#e8833a"],[0.45,"#f0c040"],
            [0.6,"#c8d840"],[0.75,"#60b048"],[0.9,"#28a745"],[1.0,"#1a8a2e"],
        ],
        zmin=-20, zmax=30, zmid=0, showscale=True,
        colorbar={
            "title":"浮动%","titleside":"right",
            "tickfont":{"color":"#8899bb"},"titlefont":{"color":"#8899bb"},
            "thickness":12, "len":0.7,
        },
        hovertemplate="%{customdata[0]}<extra></extra>",
        customdata=hover_2d, xgap=3, ygap=3,
    ))
    fig.update_layout(
        height=max(380, len(wl)*36),
        margin={"l":10,"r":10,"t":10,"b":10},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"side":"top","tickfont":{"color":"#8899bb","size":11},"gridcolor":"rgba(42,74,109,0.3)"},
        yaxis={"autorange":"reversed","tickfont":{"color":"#8899bb","size":10},"gridcolor":"rgba(42,74,109,0.3)"},
    )
    return fig


# ══════════════════════════════════════════════════════════════
# ─── 模块 1：收益驾驶舱（三列原版布局） ───
# ══════════════════════════════════════════════════════════════

def render_dashboard_tab(customers_df, calendar_df, today):
    demo_col1, demo_col2, _ = st.columns([2, 2, 4])
    with demo_col1:
        if st.button("🚀 一键演示：AI收益飞轮闭环", key="demo_btn", use_container_width=True):
            activate_demo(customers_df, calendar_df)
            st.rerun()
    with demo_col2:
        if st.session_state["demo_active"]:
            st.markdown(
                '<span style="color:#28a745;font-weight:700;">✅ 演示中 — 3步走完知客→定价→触达闭环</span>',
                unsafe_allow_html=True,
            )
    st.markdown("<hr style='border-color:#2a4a6d;margin:6px 0;'>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1.1, 2, 1])

    # ═══ 左列：智能客群画像 ═══
    with col_left:
        st.markdown('<div class="section-title">🎯 智能客群画像</div>', unsafe_allow_html=True)

        demo_on = st.session_state["demo_active"]
        with st.expander("🔍 客群筛选条件", expanded=True):
            tiers = st.multiselect(
                "会员等级", ["普通","银卡","金卡","钻石"],
                default=["普通","银卡"] if demo_on else ["普通","银卡","金卡","钻石"],
                key="ft",
                label_visibility="collapsed" if False else "visible",
            )
            # 这里有个bug——label_visibility needs to work properly
            # 直接重来
            ...
        # 修复上面的写法
        with st.expander("🔍 客群筛选条件", expanded=True):
            tiers = st.multiselect(
                "会员等级",
                ["普通","银卡","金卡","钻石"],
                default=["普通","银卡"] if demo_on else ["普通","银卡","金卡","钻石"],
                key="filter_tier",
            )
            spend_range = st.slider(
                "消费金额区间 (元)", 0, 250000,
                (500, 30000) if demo_on else (0, 250000),
                step=5000, key="filter_spend",
            )
            sentiments = st.multiselect(
                "情感倾向", ["正面","中性","负面"],
                default=["正面","中性","负面"], key="filter_sentiment",
            )
            churn_only = st.checkbox("仅显示流失风险客户", value=demo_on, key="filter_churn")
            price_only = st.checkbox("仅显示价格敏感客户", value=demo_on, key="filter_price")

        # 筛选
        filtered = customers_df[
            customers_df["会员等级"].isin(tiers)
            & customers_df["总消费金额"].between(*spend_range)
            & customers_df["情感标签"].isin(sentiments)
        ]
        if churn_only: filtered = filtered[filtered["流失风险"]]
        if price_only: filtered = filtered[filtered["价格敏感"]]

        hv_cnt = filtered["高价值"].sum()
        ch_cnt = filtered["流失风险"].sum()
        ps_cnt = filtered["价格敏感"].sum()

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f'<div class="stat-card"><div class="val">{hv_cnt}</div><div class="lbl">高价值客户</div></div>', unsafe_allow_html=True)
        with sc2:
            clr = "#dc3545" if ch_cnt > 15 else "#c8963e"
            st.markdown(f'<div class="stat-card" style="border-color:{"#dc3545" if ch_cnt > 15 else "#2a4a6d"};"><div class="val" style="color:{clr};">{ch_cnt}</div><div class="lbl">流失预警</div></div>', unsafe_allow_html=True)
        with sc3:
            st.markdown(f'<div class="stat-card"><div class="val">{ps_cnt}</div><div class="lbl">价格敏感</div></div>', unsafe_allow_html=True)

        # 图表
        t1, t2 = st.tabs(["会员分布", "情感分布"])
        with t1:
            tc = filtered["会员等级"].value_counts().reset_index()
            tc.columns = ["等级","人数"]
            cm = {"钻石":"#c8963e","金卡":"#b8a060","银卡":"#8899bb","普通":"#4a6080"}
            fig_p = px.pie(tc, names="等级", values="人数", color="等级", color_discrete_map=cm, hole=0.4)
            fig_p.update_layout(height=240, margin={"l":0,"r":0,"t":10,"b":10},
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color":"#8899bb"}, legend={"orientation":"h","yanchor":"bottom","y":-0.3})
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})
        with t2:
            sc = filtered["情感标签"].value_counts().reindex(["正面","中性","负面"], fill_value=0).reset_index()
            sc.columns = ["情感","人数"]
            cs = {"正面":"#28a745","中性":"#f0c040","负面":"#dc3545"}
            fig_b = px.bar(sc, x="情感", y="人数", color="情感", color_discrete_map=cs, text="人数")
            fig_b.update_layout(height=240, margin={"l":0,"r":0,"t":10,"b":10},
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color":"#8899bb"}, showlegend=False)
            fig_b.update_traces(textposition="outside", textfont={"color":"#8899bb"})
            st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar":False})

        # 表格
        st.markdown(f'<div style="color:#8899bb;font-size:13px;margin-top:4px;">📋 筛选结果：{len(filtered)} 位</div>', unsafe_allow_html=True)
        dcols = ["客户ID","姓名","会员等级","总消费金额","情感标签","流失风险","价格敏感","偏好房型","最近入住"]
        dd = filtered[dcols].copy()
        dd["最近入住"] = dd["最近入住"].dt.strftime("%Y-%m-%d")
        dd["流失风险"] = dd["流失风险"].map({True:"⚠️是",False:"否"})
        dd["价格敏感"] = dd["价格敏感"].map({True:"💲是",False:"否"})
        st.dataframe(dd, height=200, use_container_width=True, hide_index=True)
        csv_download_button(dd, "客群画像_筛选结果.csv")

    # ═══ 中列：智能价格日历 ═══
    with col_center:
        st.markdown('<div class="section-title">📅 智能价格日历 (未来90天)</div>', unsafe_allow_html=True)

        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            st.markdown('<span style="display:inline-block;width:12px;height:12px;background:#28a745;border-radius:3px;margin-right:4px;"></span><span style="color:#28a745;font-size:12px;font-weight:600;">提价区</span>', unsafe_allow_html=True)
        with lc2:
            st.markdown('<span style="display:inline-block;width:12px;height:12px;background:#f0c040;border-radius:3px;margin-right:4px;"></span><span style="color:#f0c040;font-size:12px;font-weight:600;">平价区</span>', unsafe_allow_html=True)
        with lc3:
            st.markdown('<span style="display:inline-block;width:12px;height:12px;background:#dc3545;border-radius:3px;margin-right:4px;"></span><span style="color:#dc3545;font-size:12px;font-weight:600;">降价区</span>', unsafe_allow_html=True)

        fig_cal = plot_calendar_heatmap(calendar_df, st.session_state["adopted_prices"])
        st.plotly_chart(fig_cal, use_container_width=True, config={"displayModeBar":False})

        # 日期选择器
        default_sel = st.session_state.get("selected_date") if st.session_state.get("selected_date") else today + timedelta(days=25)
        sel_d = st.date_input("🔎 选取日期查看AI定价建议：", value=default_sel,
                              min_value=today, max_value=today + timedelta(days=89), key="dp")
        if sel_d:
            st.session_state["selected_date"] = sel_d

        # AI定价建议卡
        if st.session_state.get("selected_date"):
            sd = st.session_state["selected_date"]
            row = calendar_df[calendar_df["日期"] == sd]
            if not row.empty:
                r = row.iloc[0]
                ap = st.session_state["adopted_prices"].get(sd.strftime("%Y-%m-%d"))
                ze = {"提价区":"🟢","平价区":"🟡","降价区":"🔴"}.get(r["颜色区域"],"⚪")

                badge_html = f'<span class="price-badge-adopted">已采纳 ¥{ap}</span>' if ap else ""
                st.markdown(
                    f'<div class="card card-accent">'
                    f'<div style="font-size:16px;font-weight:700;color:#c8963e;margin-bottom:8px;">'
                    f'{ze} AI定价建议卡 — {sd.strftime("%Y年%m月%d日")} 周{r["星期"]}{badge_html}</div>',
                    unsafe_allow_html=True,
                )

                k1, k2, k3 = st.columns(3)
                with k1: st.metric("💰 建议房价", f"¥{r['建议房价']:.0f}", f"{r['价格浮动']:+.1f}%")
                with k2: st.metric("📊 预测出租率", f"{r['预测出租率']:.1f}%")
                with k3:
                    dc2 = "inverse" if r["价格浮动"] < 0 else "normal"
                    st.metric("📈 基础价", f"¥{r['基础价']:.0f}",
                              delta=f"{r['建议房价'] - r['基础价']:+.0f}", delta_color=dc2)

                st.markdown(
                    f'<div style="color:#aabbcc;font-size:13px;margin:8px 0;padding:10px;'
                    f'background:#0f2040;border-radius:6px;">'
                    f'🧠 <b>决策依据：</b>{r["决策依据"]}</div>',
                    unsafe_allow_html=True,
                )

                bc1, bc2 = st.columns([1, 2])
                with bc1:
                    if not ap:
                        if st.button(f"✅ 一键采纳 ¥{r['建议房价']:.0f}", key="adopt", use_container_width=True):
                            st.session_state["adopted_prices"][sd.strftime("%Y-%m-%d")] = r["建议房价"]
                            log_decision("采纳定价", f"日期 {sd} 采纳AI建议价 ¥{r['建议房价']}，浮动{r['价格浮动']:+.1f}%", f"预计增收 ¥{r['建议房价']*0.12:.0f}/间夜")
                            st.rerun()
                    else:
                        if st.button("↩ 取消采纳", key="unadopt", use_container_width=True):
                            del st.session_state["adopted_prices"][sd.strftime("%Y-%m-%d")]
                            log_decision("取消定价", f"日期 {sd} 取消采纳，恢复人工定价")
                            st.rerun()
                with bc2:
                    if r["颜色区域"] == "降价区":
                        if st.button("🎯 为此日生成营销方案 →", key="goto_mkt", use_container_width=True):
                            st.session_state["marketing_target_date"] = sd
                            st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        # KPI
        st.markdown("<br>", unsafe_allow_html=True)
        kc1, kc2, kc3, kc4 = st.columns(4)
        avg_p = calendar_df["建议房价"].mean()
        avg_o = calendar_df["预测出租率"].mean()
        ac = len(st.session_state["adopted_prices"])
        td_days = len(calendar_df)
        br = avg_p * (avg_o / 100) * td_days
        ar = br * (1 + calendar_df["价格浮动"].mean() / 100 * 0.6)
        uplift = (ar - br) / br * 100 if br > 0 else 0
        est_revpar = avg_p * (avg_o / 100)

        with kc1: st.metric("💎 预计RevPAR", f"¥{est_revpar:.0f}")
        with kc2: st.metric("✅ AI采纳率", f"{ac/td_days*100:.0f}%", delta=f"{ac}/{td_days}天")
        with kc3: st.metric("📈 动态定价增收", f"{uplift:+.1f}%", delta="vs固定定价")
        with kc4: st.metric("📊 均价/出租率", f"¥{avg_p:.0f}/{avg_o:.0f}%")

    # ═══ 右列：智能营销工坊 ═══
    with col_right:
        st.markdown('<div class="section-title">📨 智能营销工坊</div>', unsafe_allow_html=True)

        red_days = calendar_df[calendar_df["颜色区域"] == "降价区"]["日期"].tolist()
        if red_days:
            st.markdown(
                f'<div class="card card-red" style="font-size:13px;color:#dc3545;">'
                f'⚠️ 检测到 <b>{len(red_days)}</b> 个降价日（库存压力）</div>',
                unsafe_allow_html=True,
            )

        mkt_def_idx = 0
        if st.session_state.get("marketing_target_date"):
            md = st.session_state["marketing_target_date"]
            if md in red_days:
                try: mkt_def_idx = red_days.index(md)
                except ValueError: pass

        mkt_date = None
        if red_days or st.session_state.get("marketing_target_date"):
            dopt = red_days if red_days else [st.session_state["marketing_target_date"]]
            mkt_date = st.selectbox(
                "📅 营销目标日期：", dopt, index=min(mkt_def_idx, len(dopt)-1),
                format_func=lambda d: f'{d.strftime("%m月%d日")} 周{["一","二","三","四","五","六","日"][d.weekday()]} {"🔴降价" if d in red_days else ""}',
                key="mds",
            )
        else:
            st.info("暂无降价日。AI将在库存压力时自动触发。")

        if mkt_date:
            mr = calendar_df[calendar_df["日期"] == mkt_date]
            if not mr.empty:
                mkr = mr.iloc[0]
                st.markdown('<div style="color:#8899bb;font-size:12px;margin-bottom:6px;">🎯 基于客群画像，自动筛选「价格敏感+流失风险」目标客户</div>', unsafe_allow_html=True)

                targets = customers_df[customers_df["价格敏感"] & customers_df["流失风险"]]
                if len(targets) < 3:
                    targets = customers_df[customers_df["价格敏感"] | customers_df["流失风险"]]

                st.markdown(f'<span style="color:#c8963e;font-size:13px;">匹配到 <b>{len(targets)}</b> 位目标客户</span>', unsafe_allow_html=True)

                if st.button("🤖 生成个性化营销话术", key="gen_msgs", use_container_width=True):
                    with st.spinner("🧠 AI正在为每位客户生成定制文案…"):
                        msgs = [generate_marketing_message(cust, mkt_date, mkr["决策依据"]) for _, cust in targets.iterrows()]
                        st.session_state["generated_messages"] = msgs
                    log_decision("生成文案", f"为 {len(msgs)} 位客户生成个性化营销话术，目标日期 {mkt_date}", "预计转化率+3-5倍")
                    st.rerun()

                # 消息列表
                msgs = st.session_state.get("generated_messages", [])
                if msgs:
                    st.markdown(f'<div style="color:#8899bb;font-size:12px;margin-top:10px;">📋 {len(msgs)} 条消息待发送</div>', unsafe_allow_html=True)

                    ps2 = 5
                    tp = max(1, (len(msgs) + ps2 - 1) // ps2)
                    page = min(st.session_state["msg_page"], tp - 1) if tp > 0 else 0
                    si = page * ps2
                    ei = min(si + ps2, len(msgs))

                    selected_ids = []
                    for i in range(si, ei):
                        m = msgs[i]
                        cid = m["客户ID"]
                        is_sent = cid in st.session_state["sent_messages"]
                        checked = st.checkbox(
                            f"{'✅' if is_sent else ''}{m['称呼']} | {m['权益类型']} | {m['建议渠道']}",
                            value=False, key=f"msg_{cid}", disabled=is_sent,
                        )
                        if checked and not is_sent:
                            selected_ids.append(cid)
                        with st.expander(f"{'✅' if is_sent else '📩'}{m['称呼']} — {m['权益类型']}", expanded=(i == si and not is_sent)):
                            st.markdown(
                                f'<div class="msg-card">{m["消息内容"].replace(chr(10),"<br>")}'
                                f'<br><span class="channel-tag">📡 {m["建议渠道"]}</span></div>',
                                unsafe_allow_html=True,
                            )

                    pc1, pc2, pc3 = st.columns([1, 1, 1])
                    with pc1:
                        if st.button("◀ 上一页", disabled=(page == 0), key="prev"):
                            st.session_state["msg_page"] = max(0, page - 1)
                            st.rerun()
                    with pc2:
                        st.markdown(f'<div style="text-align:center;color:#8899bb;font-size:12px;">{page+1}/{tp}</div>', unsafe_allow_html=True)
                    with pc3:
                        if st.button("下一页 ▶", disabled=(page >= tp - 1), key="next"):
                            st.session_state["msg_page"] = min(tp - 1, page + 1)
                            st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🚀 一键模拟发送（全部未发送）", key="batch_send", use_container_width=True):
                        sent_any = False
                        for m in msgs:
                            cid = m["客户ID"]
                            if cid not in st.session_state["sent_messages"]:
                                st.session_state["sent_messages"].add(cid)
                                sent_any = True
                        if sent_any:
                            st.session_state["show_success"] = True
                            log_decision("模拟发送", f"向 {len(st.session_state['sent_messages'])} 位客户发送营销消息", f"预计增收 ¥{len(st.session_state['sent_messages'])*180:,.0f}+")
                            st.rerun()
                        else:
                            st.info("所有消息已发送完毕。")

                    if st.session_state.get("show_success"):
                        scnt = len(st.session_state["sent_messages"])
                        st.markdown(
                            f'<div class="success-toast">'
                            f'✨ 发送成功！已触达 <b>{scnt}</b> 位目标客户<br>'
                            f'<span style="font-size:11px;color:#60b048;">预计响应率提升3-5倍，增收潜力 ¥{scnt*180:,}+</span></div>',
                            unsafe_allow_html=True,
                        )

                if st.session_state["sent_messages"]:
                    st.markdown(f'<div style="color:#28a745;font-size:12px;margin-top:8px;">📊 累计触达：{len(st.session_state["sent_messages"])} 位</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# ─── 模块 2：竞品OTA监控 ───
# 价值：实时掌握竞品价格动态，为定价决策提供外部锚点
# ══════════════════════════════════════════════════════════════

def render_ota_tab():
    st.markdown('<div class="section-title">🏔️ 九寨沟 · 竞品OTA全网比价</div>', unsafe_allow_html=True)

    # ── 数据来源说明 ──
    ds = st.session_state.get("ota_data_source", "模拟参考")
    ds_color = "#28a745" if ds == "CSV导入" else ("#3b82f6" if ds == "混合" else "#f0c040")
    ds_text = "✅ 真实采集" if ds == "CSV导入" else ("🔵 模拟+导入混合" if ds == "混合" else "⚠️ 模拟参考（点击下方导入真实数据）")

    with st.expander(f"📡 数据来源：{ds_text}", expanded=(ds == "模拟参考")):
        # ═══ 一键采集按钮 ═══
        st.markdown(
            '<div style="background:linear-gradient(135deg,#1a2a10,#1e3515);border:1px solid #28a745;'
            'border-radius:10px;padding:14px 18px;margin-bottom:12px;">'
            '<b style="color:#28a745;font-size:15px;">🚀 获取真实价格</b><br>'
            '<span style="color:#aaccaa;font-size:12px;">运行 <code>真实OTA采集.py</code> 自动采集去哪儿酒店价格，输出CSV后自动导入</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        rcol1, rcol2, rcol3 = st.columns([1.5, 1, 1])
        with rcol1:
            if st.button("🔄 运行采集脚本（HTML直抓）", key="run_scraper", use_container_width=True,
                         help="纯requests+BS4抓取去哪儿，无需浏览器。结果自动CSV导入。"):
                with st.spinner("🔍 正在采集九寨沟OTA价格..."):
                    script_dir = Path(__file__).parent if "__file__" in dir() else Path.cwd()
                    scraper_path = script_dir / "真实OTA采集.py"
                    if scraper_path.exists():
                        result = subprocess.run(
                            [sys.executable, str(scraper_path), "--auto"],
                            capture_output=True, text=True, timeout=120,
                            cwd=str(script_dir),
                        )
                        csv_path = script_dir / "ota_real_prices.csv"
                        if csv_path.exists():
                            real_df = pd.read_csv(csv_path)
                            st.session_state["ota_imported_df"] = real_df
                            st.session_state["ota_data_source"] = "CSV导入" if any(
                                s == "HTML直抓" for s in real_df.get("数据来源", [])
                            ) else "混合"
                            st.cache_data.clear()
                            st.success(f"✅ 采集成功！导入 {len(real_df)} 条价格记录")
                            st.rerun()
                        else:
                            st.warning(f"采集脚本已运行，但未生成CSV。请检查：\n```\n{result.stderr[-500:]}\n```")
                    else:
                        st.error(f"未找到采集脚本: {scraper_path}")
        with rcol2:
            if st.button("📥 下载CSV模板", key="download_template", use_container_width=True):
                template_path = Path(__file__).parent / "OTA价格导入模板.csv" if "__file__" in dir() else Path("OTA价格导入模板.csv")
                if template_path.exists():
                    with open(template_path, "r", encoding="utf-8-sig") as f:
                        st.download_button(
                            "点击下载模板CSV", f.read(),
                            file_name="OTA价格导入模板.csv",
                            mime="text/csv",
                        )
                else:
                    st.info("模板文件不存在")
        with rcol3:
            st.markdown(
                '<div style="color:#8899bb;font-size:11px;line-height:1.6;">'
                '💡 <b>采集原理：</b><br>'
                'requests+BS4直抓<br>'
                '去哪儿 SSR 页面<br>'
                '提取JSON+DOM价格<br>'
                '→ 自动生成CSV导入'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='border-color:#2a4a6d;margin:10px 0;'>", unsafe_allow_html=True)

        st.markdown(
            '<div style="color:#8899bb;font-size:13px;line-height:1.8;">'
            '<b>📋 其他获取真实价格的方式：</b>'
            '</div>',
            unsafe_allow_html=True,
        )

        # CSV导入
        uploaded = st.file_uploader(
            "📁 拖入OTA价格CSV文件（真实数据）",
            type=["csv"], key="ota_csv",
            help="必须包含：酒店名称, 房型, OTA平台, 单价_晚",
        )
        if uploaded is not None:
            try:
                real_df = pd.read_csv(uploaded)
                required = ["酒店名称","房型","OTA平台","单价_晚"]
                missing = [c for c in required if c not in real_df.columns]
                if missing:
                    st.error(f"❌ 缺少必要列：{', '.join(missing)}")
                else:
                    real_df["总价"] = real_df.get("总价", real_df["单价_晚"] * 1)
                    real_df["含早"] = real_df.get("含早", "")
                    real_df["可取消"] = real_df.get("可取消", "")
                    real_df["数据来源"] = "真实采集"
                    st.session_state["ota_imported_df"] = real_df
                    st.session_state["ota_data_source"] = "CSV导入"
                    st.success(f"✅ 已导入 {len(real_df)} 条真实价格记录！")
                    st.cache_data.clear()  # 刷新缓存让合并生效
            except Exception as e:
                st.error(f"❌ CSV解析失败：{e}")

        if st.button("🔄 重置为模拟参考价", key="reset_ota"):
            st.session_state["ota_imported_df"] = None
            st.session_state["ota_data_source"] = "模拟参考"
            st.cache_data.clear()
            st.rerun()

    # ── 控制栏 ──
    ctrl1, ctrl2, ctrl3, ctrl4, ctrl5, ctrl6 = st.columns([1.3, 0.8, 1.1, 0.8, 0.8, 1.2])
    with ctrl1:
        ci_date = st.date_input("入住日期", value=date.today() + timedelta(days=3), key="ota_ci")
    with ctrl2:
        nights = st.number_input("晚数", 1, 7, 1, key="ota_nights")
    with ctrl3:
        co_date = ci_date + timedelta(days=nights)
        st.markdown(f'<label style="color:#8899bb;font-size:11px;">离店</label><br><span style="color:#fff;">{co_date.strftime("%Y-%m-%d")}</span>', unsafe_allow_html=True)
    with ctrl4:
        sf = st.selectbox("星级", ["all","5","4","3"], format_func=lambda x: "全部" if x=="all" else f"{x}⭐", key="ota_star")
    with ctrl5:
        rf = st.selectbox("房型", ["all","大床房","双床房","套房","亲子房","标准间","行政房","别墅"], key="ota_room")
    with ctrl6:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新", key="ota_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── 构建数据：模拟 + 导入合并 ──
    sim_df = generate_ota_prices(ci_date, nights, sf, rf)
    imported = st.session_state.get("ota_imported_df")
    if imported is not None and not imported.empty:
        # 只保留匹配当前筛选条件的数据
        imp = imported.copy()
        if sf != "all":
            # 尝试从名称推断星级
            star_map = {h["名称"]: h["星级"] for h in JIUZHAIGOU_HOTELS}
            imp["_star"] = imp["酒店名称"].map(star_map).fillna(4)
            imp = imp[imp["_star"] == int(sf)]
            imp.drop(columns=["_star"], inplace=True)
        if rf != "all":
            imp = imp[imp["房型"].str.contains(rf, na=False)]
        ota_df = merge_ota_data(sim_df, imp)
    else:
        ota_df = sim_df

    hotel_count = ota_df["酒店名称"].nunique()
    ds_tag = st.session_state.get("ota_data_source", "模拟参考")

    # ── 数据来源色标 ──
    ds_badge = "🟢 真实采集" if ds_tag == "CSV导入" else ("🔵 混合" if ds_tag == "混合" else "🟡 模拟参考")
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        f'<span style="color:#8899bb;font-size:12px;">数据来源：<b style="color:{"#28a745" if ds_tag=="CSV导入" else ("#3b82f6" if ds_tag=="混合" else "#f0c040")};">{ds_badge}</b></span>'
        f'<span style="color:#8899bb;font-size:12px;">共 {len(ota_df)} 条记录 | {hotel_count} 家酒店</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 统计卡片 ──
    prices = ota_df["单价_晚"].values
    min_p, max_p, avg_p = int(prices.min()), int(prices.max()), int(round(prices.mean()))
    keyed = {}
    for _, r in ota_df.iterrows():
        k = r["酒店名称"] + "|" + r["房型"]
        if k not in keyed or r["单价_晚"] < keyed[k]["单价_晚"]:
            keyed[k] = r
    deals = list(keyed.values())
    avg_low = int(round(sum(d["单价_晚"] for d in deals) / len(deals))) if deals else 0
    savings_per = round((avg_p - avg_low) / avg_p * 100, 1) if avg_p > 0 else 0

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1: st.markdown(f'<div class="stat-card"><div class="val">{hotel_count}</div><div class="lbl">监控酒店</div><div class="delta">九寨沟全域覆盖</div></div>', unsafe_allow_html=True)
    with sc2: st.markdown(f'<div class="stat-card"><div class="val">¥{min_p}</div><div class="lbl">全网最低价/晚</div></div>', unsafe_allow_html=True)
    with sc3: st.markdown(f'<div class="stat-card"><div class="val">¥{avg_p}</div><div class="lbl">全网均价/晚</div><div class="delta">{len(ota_df)}条记录</div></div>', unsafe_allow_html=True)
    with sc4: st.markdown(f'<div class="stat-card" style="border-left:3px solid #28a745;"><div class="val">¥{avg_p - avg_low}</div><div class="lbl">比价可节省/晚</div><div class="delta">≈省{savings_per}%</div></div>', unsafe_allow_html=True)
    with sc5: st.markdown(f'<div class="stat-card"><div class="val">{get_season_label(ci_date)}</div><div class="lbl">当前季节</div></div>', unsafe_allow_html=True)

    # ── 图表行 ──
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown('<h4 style="color:#c8963e;font-size:14px;">📊 各酒店OTA价差分布</h4>', unsafe_allow_html=True)
        hs = ota_df.groupby("酒店名称")["单价_晚"].agg(["min","max","mean"]).reset_index()
        hs.columns = ["酒店","最低","最高","均价"]
        hs["价差"] = hs["最高"] - hs["最低"]
        hs = hs.sort_values("价差", ascending=False).head(10)
        hs["显示名"] = hs["酒店"].str.slice(0, 12)

        fig_s = go.Figure()
        for _, hr in hs.iterrows():
            fig_s.add_trace(go.Bar(
                name=hr["显示名"], x=[hr["显示名"]], y=[hr["价差"]],
                marker_color="#c8963e", text=f"¥{int(hr['价差'])}",
                textposition="outside", textfont={"color":"#8899bb","size":10},
                hovertemplate=f"{hr['酒店']}<br>最低: ¥{int(hr['最低'])}<br>最高: ¥{int(hr['最高'])}<br>价差: ¥{int(hr['价差'])}<extra></extra>",
            ))
        fig_s.update_layout(
            height=300, margin={"l":0,"r":0,"t":0,"b":60},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color":"#8899bb"}, showlegend=False,
            yaxis={"title":"价差(¥)","gridcolor":"rgba(42,74,109,0.3)","titlefont":{"color":"#8899bb"}},
            xaxis={"tickfont":{"size":9}},
        )
        st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar":False})

    with ch2:
        st.markdown('<h4 style="color:#c8963e;font-size:14px;">🏨 各OTA平台均价对比</h4>', unsafe_allow_html=True)
        pa = ota_df.groupby("OTA平台")["单价_晚"].mean().reset_index()
        pa.columns = ["平台","均价"]
        pc = {"携程":"#0066cc","美团":"#ffc700","飞猪":"#ff5000","去哪儿":"#1976d2","同程":"#07c160","艺龙":"#e60044"}
        fig_p = px.bar(pa, x="平台", y="均价", color="平台", color_discrete_map=pc,
                       text=pa["均价"].apply(lambda x: f"¥{x:.0f}"))
        fig_p.update_layout(
            height=300, margin={"l":0,"r":0,"t":0,"b":10},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color":"#8899bb"}, showlegend=False,
            yaxis={"gridcolor":"rgba(42,74,109,0.3)"},
        )
        fig_p.update_traces(textposition="outside", textfont={"color":"#8899bb"})
        st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})

    # ── 星级价格散点图 ──
    st.markdown('<h4 style="color:#c8963e;font-size:14px;">📈 价格 vs 星级 散点分布</h4>', unsafe_allow_html=True)
    sd = ota_df.groupby(["酒店名称","星级"])["单价_晚"].mean().reset_index()
    fig_sc = px.scatter(
        sd, x="星级", y="单价_晚", text="酒店名称",
        color="星级", color_continuous_scale=["#3b82f6","#f0c040","#c8963e"],
        size=sd["单价_晚"], size_max=25,
    )
    fig_sc.update_traces(
        textposition="top center", textfont={"size":9,"color":"#8899bb"},
        marker={"opacity":0.8, "line":{"width":1,"color":"#2a4a6d"}},
    )
    fig_sc.update_layout(
        height=320, margin={"l":10,"r":10,"t":10,"b":10},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color":"#8899bb"}, showlegend=False, coloraxis_showscale=False,
        xaxis={"gridcolor":"rgba(42,74,109,0.3)","dtick":1},
        yaxis={"gridcolor":"rgba(42,74,109,0.3)","title":"均价(¥)","titlefont":{"color":"#8899bb"}},
    )
    st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar":False})

    # ── 手动录入入口 ──
    with st.expander("✏️ 手动录入真实OTA价格（从手机/OTA后台查到后填入）"):
        mc1, mc2, mc3, mc4 = st.columns([2, 1.5, 1, 1])
        with mc1:
            m_hotel = st.selectbox("酒店", [h["名称"] for h in JIUZHAIGOU_HOTELS], key="man_hotel")
        with mc2:
            m_room = st.selectbox("房型", ["大床房","双床房","套房","亲子房","标准间","行政房","别墅"], key="man_room")
        with mc3:
            m_plat = st.selectbox("OTA平台", OTA_PLATFORMS, key="man_plat")
        with mc4:
            m_price = st.number_input("单价/晚(¥)", 50, 10000, 500, 10, key="man_price")

        if st.button("➕ 添加此价格", key="man_add"):
            key = f"{m_hotel}|{m_room}|{m_plat}"
            st.session_state["manual_prices"][key] = {
                "酒店名称": m_hotel, "房型": m_room, "OTA平台": m_plat,
                "单价_晚": m_price, "总价": m_price * nights,
                "含早": "", "可取消": "", "数据来源": "手动录入",
            }
            st.success(f"✅ 已记录：{m_hotel} {m_room} {m_plat} = ¥{m_price}")

        if st.session_state["manual_prices"]:
            mp_df = pd.DataFrame(st.session_state["manual_prices"].values())
            st.markdown(f'<span style="color:#c8963e;font-size:12px;">已手动录入 {len(mp_df)} 条价格</span>', unsafe_allow_html=True)
            if st.button("📥 合并手动价格到当前表格", key="man_merge"):
                # 合并导入+手动
                existing = st.session_state.get("ota_imported_df")
                if existing is not None:
                    combined = pd.concat([existing, mp_df], ignore_index=True)
                else:
                    combined = mp_df.copy()
                st.session_state["ota_imported_df"] = combined
                st.session_state["ota_data_source"] = "混合"
                st.cache_data.clear()
                st.session_state["manual_prices"] = {}
                st.rerun()

    # ── 全网比价表格 ──
    st.markdown('<h4 style="color:#c8963e;font-size:14px;">📋 全网比价明细表</h4>', unsafe_allow_html=True)

    # 找最低价
    lowest_set = set()
    for _, r in ota_df.iterrows():
        k = r["酒店名称"] + "|" + r["房型"]
        if k in keyed and keyed[k]["单价_晚"] == r["单价_晚"]:
            lowest_set.add(r["酒店名称"] + "|" + r["房型"] + "|" + r["OTA平台"] + "|" + str(r["单价_晚"]))

    # 显示列
    dcols = ["酒店名称","星级","房型","OTA平台","单价_晚","含早","可取消"]
    avail = [c for c in dcols if c in ota_df.columns]
    do = ota_df[avail].copy()
    if "星级" in do.columns:
        do["星级"] = do["星级"].apply(lambda x: "⭐"*int(x) if isinstance(x,(int,float)) else str(x))

    # 数据来源列染色
    if "数据来源" in ota_df.columns:
        do["数据来源"] = ota_df["数据来源"]

    st.dataframe(
        do,
        height=400, use_container_width=True, hide_index=True,
        column_config={
            "酒店名称": st.column_config.TextColumn("酒店名称", width="medium"),
            "单价_晚": st.column_config.NumberColumn("单价/晚", format="¥%d"),
        },
    )

    # ── 全网最低价 Top 5 ──
    st.markdown('<h4 style="color:#c8963e;font-size:14px;margin-top:14px;">🏆 全网最低价 Top 5</h4>', unsafe_allow_html=True)
    so = ota_df.sort_values("单价_晚")
    seen_k = set()
    top5 = []
    for _, r in so.iterrows():
        k = r["酒店名称"] + "|" + r["房型"]
        if k not in seen_k:
            seen_k.add(k); top5.append(r)
        if len(top5) >= 5: break

    for i, r in enumerate(top5):
        tc = "var(--green)" if i == 0 else "var(--gold)"
        pcls = {"携程":"ota-ctrip","美团":"ota-meituan","飞猪":"ota-fliggy","去哪儿":"ota-qunar","同程":"ota-tongcheng","艺龙":"ota-elong"}.get(r.get("OTA平台",""),"")
        source_tag = ""
        if r.get("数据来源") == "真实采集":
            source_tag = '<span style="color:#28a745;font-size:9px;">✅真实</span>'
        elif r.get("数据来源") == "手动录入":
            source_tag = '<span style="color:#3b82f6;font-size:9px;">✏️手动</span>'
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;'
            f'background:#142642;border:1px solid #2a4a6d;border-radius:8px;margin:4px 0;'
            f'{"border-left:3px solid #28a745;" if i == 0 else ""}">'
            f'<div style="font-size:22px;font-weight:800;color:{tc};min-width:30px;">#{i+1}</div>'
            f'<div style="flex:1;"><div style="font-weight:700;">{r["酒店名称"]}{source_tag}</div>'
            f'<div style="font-size:11px;color:#8899bb;">{r.get("房型","")} · {"⭐"*int(r.get("星级",3))}</div></div>'
            f'<div style="text-align:right;">'
            f'<div style="font-size:18px;font-weight:800;color:#28a745;">¥{int(r["单价_晚"])}</div>'
            f'<div style="font-size:10px;color:#8899bb;">'
            f'<span class="ota-tag {pcls}">{r.get("OTA平台","")}</span> '
            f'{"🍳含早" if r.get("含早")=="是" else ""} {"✅可取消" if r.get("可取消")=="是" else ""}</div></div></div>',
            unsafe_allow_html=True,
        )

    csv_download_button(ota_df, f"九寨沟OTA比价_{ci_date}.csv")


def get_season_label(d):
    m = d.month
    if m in (4,5,9,10): return "🍂旺季"
    if m in (7,8): return "☀️暑期"
    if m in (1,2,12): return "❄️淡季"
    return "🌸平季"


# ══════════════════════════════════════════════════════════════
# ─── 模块 3：AI决策日志 ───
# 价值：全链路数据回流，让每一分钱都有据可查
# ══════════════════════════════════════════════════════════════

def render_log_tab():
    st.markdown('<div class="section-title">🧠 AI决策日志 — 数据回流闭环</div>', unsafe_allow_html=True)

    # 统计
    log = st.session_state["decision_log"]
    if not log:
        st.info("📝 暂无决策记录。在收益驾驶舱中进行操作后，AI决策将记录在此。")
        st.markdown(
            '<div class="card" style="color:#8899bb;font-size:13px;">'
            '<b>💡 什么是数据回流？</b><br>'
            '每一次AI定价建议被采纳、每一次营销消息被发送，都会记录在此。'
            '系统持续学习哪些策略有效，形成「决策→执行→效果→优化」的智能飞轮。</div>',
            unsafe_allow_html=True,
        )
        return

    adopted = sum(1 for l in log if "采纳定价" in l["类型"])
    sent = sum(1 for l in log if "模拟发送" in l["类型"])
    generated = sum(1 for l in log if "生成文案" in l["类型"])
    total_impact = sum(
        int(re.search(r"¥([\d,]+)", l["预计影响"]).group(1).replace(",",""))
        for l in log if re.search(r"¥([\d,]+)", l["预计影响"])
    )

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1: st.markdown(f'<div class="stat-card"><div class="val">{len(log)}</div><div class="lbl">总决策数</div></div>', unsafe_allow_html=True)
    with sc2: st.markdown(f'<div class="stat-card"><div class="val">{adopted}</div><div class="lbl">采纳定价</div></div>', unsafe_allow_html=True)
    with sc3: st.markdown(f'<div class="stat-card"><div class="val">{sent}</div><div class="lbl">营销发送</div></div>', unsafe_allow_html=True)
    with sc4: st.markdown(f'<div class="stat-card" style="border-left:3px solid #28a745;"><div class="val">¥{total_impact:,}</div><div class="lbl">预计增收</div></div>', unsafe_allow_html=True)

    # 时间线
    st.markdown('<h4 style="color:#c8963e;font-size:14px;margin-top:14px;">⏱ 决策时间线</h4>', unsafe_allow_html=True)
    type_icons = {"采纳定价":"✅","取消定价":"↩️","生成文案":"🤖","模拟发送":"🚀","演示路径":"▶️"}
    for l in reversed(log[-30:]):
        icon = type_icons.get(l["类型"],"📌")
        cls = "adopted" if "采纳" in l["类型"] else ("sent" if "发送" in l["类型"] else "")
        impact_html = ""
        if l["预计影响"]:
            impact_html = (
                '<div style="font-size:11px;color:#28a745;margin-top:2px;">'
                f'📈 {l["预计影响"]}'
                '</div>'
            )
        st.markdown(
            f'<div class="timeline-item {cls}">'
            f'<div style="flex:1;">'
            f'<span style="color:#c8963e;font-weight:700;">{icon} {l["类型"]}</span>'
            f'<span style="color:#8899bb;font-size:11px;margin-left:8px;">{l["时间"]}</span>'
            f'<div style="font-size:13px;margin-top:2px;">{l["详情"]}</div>'
            f'{impact_html}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    if len(log) > 30:
        st.markdown(f'<div style="color:#8899bb;font-size:11px;text-align:center;">... 仅显示最近30条 (共{len(log)}条)</div>', unsafe_allow_html=True)

    if st.button("🗑 清空决策日志", key="clear_log"):
        st.session_state["decision_log"] = []
        st.rerun()


# ══════════════════════════════════════════════════════════════
# ─── 模块 4：BI经营报表 ───
# 价值：一键生成 RevPAR/ADR/OCC/GOP Excel 专业报表
# ══════════════════════════════════════════════════════════════

def render_bi_tab():
    st.markdown('<div class="section-title">📊 BI经营报表中心</div>', unsafe_allow_html=True)

    if not _BI_READY:
        st.warning("⚠️ BI报表模块未加载，请检查 bi_reports.py 是否在相同目录。")
        return

    # ── 数据源选择 ──
    st.markdown(
        '<div style="color:#8899bb;font-size:13px;margin-bottom:10px;">'
        '选择数据源并生成专业酒店经营分析 Excel 报表（含公式、图表、条件格式）</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1])
    with col1:
        report_type = st.selectbox(
            "报表类型",
            ["月度经营报告", "周经营分析", "GOP深度分析", "渠道分析", "预算执行分析"],
            key="bi_report_type",
        )
    with col2:
        use_real_data = st.checkbox("使用真实数据", value=True, key="bi_use_real",
                                     help="从数据库读取历史经营数据；关闭则使用模拟数据")
    with col3:
        report_days = st.selectbox("天数", [7, 14, 30, 60, 90], index=2, key="bi_days")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("📥 生成报表", key="bi_generate", use_container_width=True)

    # ── 酒店信息 ──
    hotel_name = st.text_input("酒店名称", value="我的酒店", key="bi_hotel_name")

    # ── 预算目标（可选）──
    with st.expander("📐 预算目标（可选，用于预算对比）"):
        bc1, bc2, bc3, bc4, bc5 = st.columns(5)
        with bc1:
            budget_occ = st.number_input("目标OCC(%)", 0, 100, 70, key="budget_occ")
        with bc2:
            budget_adr = st.number_input("目标ADR(¥)", 0, 5000, 500, 50, key="budget_adr")
        with bc3:
            budget_revpar = st.number_input("目标RevPAR(¥)", 0, 5000, 350, 50, key="budget_revpar")
        with bc4:
            budget_revenue = st.number_input("目标收入(¥)", 0, 10000000, 500000, 50000, key="budget_rev")
        with bc5:
            budget_gop = st.number_input("目标GOP率(%)", 0, 100, 35, key="budget_gop")

    budget_targets = {
        "occ": budget_occ, "adr": budget_adr, "revpar": budget_revpar,
        "revenue": budget_revenue, "gop_rate": budget_gop,
    }

    if generate_btn:
        with st.spinner("🔄 正在生成专业报表…"):
            # 获取数据
            if use_real_data and _DB_READY:
                df = load_from_database(
                    (date.today() - timedelta(days=report_days)).strftime("%Y-%m-%d"),
                    date.today().strftime("%Y-%m-%d"),
                )
                if df is None or df.empty:
                    st.info("💡 数据库中暂无历史数据，使用模拟数据进行演示。")
                    df = generate_sample_data(days=report_days)
                    data_note = " (模拟数据)"
                else:
                    data_note = " (数据库真实数据)"
            else:
                df = generate_sample_data(days=report_days)
                data_note = " (模拟数据)"

            # 生成报表
            try:
                if report_type == "GOP深度分析":
                    output_path = gop_deep_dive(df, hotel_name=hotel_name)
                elif report_type == "渠道分析":
                    channel_df = generate_channel_analysis()
                    output_path = generate_excel_report(
                        df, report_type=report_type, hotel_name=hotel_name,
                        channel_df=channel_df,
                    )
                elif report_type == "预算执行分析":
                    output_path = generate_excel_report(
                        df, report_type=report_type, hotel_name=hotel_name,
                        budget_targets=budget_targets,
                    )
                else:
                    output_path = generate_excel_report(
                        df, report_type=report_type, hotel_name=hotel_name,
                        budget_targets=budget_targets if report_type == "预算执行分析" else None,
                    )

                st.success(f"✅ 报表已生成{data_note}")

                # KPI 概览
                kpi = compute_kpi_summary(df)
                kc1, kc2, kc3, kc4, kc5 = st.columns(5)
                with kc1:
                    st.metric("平均OCC", f"{kpi['平均OCC']}%")
                with kc2:
                    st.metric("平均ADR", f"¥{kpi['平均ADR']:.0f}")
                with kc3:
                    st.metric("平均RevPAR", f"¥{kpi['平均RevPAR']:.0f}",
                              delta=f"{kpi['RevPAR趋势']:+.1f}%")
                with kc4:
                    st.metric("总收入", f"¥{kpi['总收入']:,.0f}")
                with kc5:
                    st.metric("GOP率", f"{kpi['GOP率']}%")

                # RevPAR 趋势图
                fig_trend = px.line(
                    df, x="日期", y=["RevPAR", "ADR"],
                    title=f"{hotel_name} — {report_type} 趋势",
                )
                fig_trend.update_layout(
                    height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#8899bb"},
                    legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
                )
                st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

                # 下载按钮
                with open(output_path, "rb") as f:
                    st.download_button(
                        f"📥 下载Excel报表 ({Path(output_path).name})",
                        f.read(),
                        file_name=Path(output_path).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                if _DB_READY:
                    db_log_decision("生成报表", f"生成{report_type} — {hotel_name}{data_note}", f"文件: {Path(output_path).name}")

            except Exception as e:
                st.error(f"❌ 报表生成失败：{e}")
                st.info("请检查 openpyxl 是否已安装：pip install openpyxl")

    # ── 历史报表列表 ──
    st.markdown("<hr style='border-color:#2a4a6d;margin:16px 0;'>", unsafe_allow_html=True)
    st.markdown('<div style="color:#c8963e;font-size:14px;font-weight:700;">📁 历史报表</div>', unsafe_allow_html=True)

    bi_dir = Path(r"E:\工作AI\酒店管理\数据分析")
    if bi_dir.exists():
        xlsx_files = sorted(bi_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
        if xlsx_files:
            for fp in xlsx_files:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f'<span style="color:#8899bb;font-size:12px;">📄 {fp.name}</span> '
                                f'<span style="color:#667799;font-size:10px;">({mtime})</span>',
                                unsafe_allow_html=True)
                with col_b:
                    with open(fp, "rb") as f:
                        st.download_button("⬇ 下载", f.read(), file_name=fp.name, key=f"hist_{fp.stem}")
        else:
            st.info("暂无历史报表。点击上方按钮生成第一份报表。")


# ══════════════════════════════════════════════════════════════
# ─── 模块 5：数据导入中心 ───
# 价值：打通 PMS/OTA 数据导入，让模拟系统接入真实数据
# ══════════════════════════════════════════════════════════════

def render_import_tab():
    st.markdown('<div class="section-title">📥 数据导入中心</div>', unsafe_allow_html=True)

    if not _DB_READY:
        st.warning("⚠️ 数据库模块未就绪。数据导入需要 database.py。")
        return

    tab_imp1, tab_imp2, tab_imp3 = st.tabs(["📊 PMS经营数据", "🏨 OTA比价数据", "⚙️ 竞品组管理"])

    # ── Tab 1: PMS 经营数据导入 ──
    with tab_imp1:
        st.markdown(
            '<div class="card card-accent" style="font-size:13px;color:#8899bb;margin-bottom:12px;">'
            '<b>💡 支持格式：</b>Opera PMS 导出 CSV、西软/绿云 Excel、通用日期+指标 CSV。<br>'
            '系统会自动识别列名并映射到标准字段（日期、OCC、ADR、RevPAR、收入等）。'
            '</div>',
            unsafe_allow_html=True,
        )

        uploaded_pms = st.file_uploader(
            "📁 拖入PMS导出的经营数据文件", type=["csv", "xlsx"], key="pms_upload",
            help="支持 Opera/西软/绿云 等主流PMS导出格式",
        )

        if uploaded_pms is not None:
            tmp_path = Path(r"E:\工作AI\临时文件") / uploaded_pms.name
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(uploaded_pms.getvalue())

            # 预览
            try:
                if uploaded_pms.name.endswith(".csv"):
                    preview_df = pd.read_csv(tmp_path, encoding="utf-8-sig", nrows=5)
                else:
                    preview_df = pd.read_excel(tmp_path, nrows=5)
                st.markdown(f'<span style="color:#8899bb;font-size:12px;">📋 预览（前5行）— 共 {len(preview_df.columns)} 列</span>', unsafe_allow_html=True)
                st.dataframe(preview_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"❌ 无法预览文件: {e}")

            if st.button("✅ 确认导入", key="confirm_pms_import", use_container_width=True):
                with st.spinner("正在导入PMS数据..."):
                    try:
                        from data_import import import_pms_data
                        result_df = import_pms_data(str(tmp_path))
                        if result_df is not None and not result_df.empty:
                            st.success(f"✅ 成功导入 {len(result_df)} 条经营数据到数据库！")
                            st.cache_data.clear()
                            db_log_decision("数据导入", f"导入PMS数据 {len(result_df)} 条", f"文件: {uploaded_pms.name}")
                        else:
                            st.warning("⚠️ 未识别到有效数据，请检查文件格式。")
                    except Exception as e:
                        st.error(f"❌ 导入失败：{e}")

        # 手动录入入口
        with st.expander("✏️ 手动录入单日数据"):
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                man_date = st.date_input("日期", value=date.today(), key="man_metric_date")
            with mc2:
                man_occ = st.number_input("OCC(%)", 0.0, 100.0, 65.0, 1.0, key="man_occ")
            with mc3:
                man_adr = st.number_input("ADR(¥)", 0.0, 5000.0, 500.0, 10.0, key="man_adr")
            with mc4:
                man_rev = st.number_input("总收入(¥)", 0.0, 1000000.0, 40000.0, 1000.0, key="man_rev")

            mc5, mc6, mc7, mc8 = st.columns(4)
            with mc5:
                man_cost = st.number_input("总成本(¥)", 0.0, 1000000.0, 25000.0, 1000.0, key="man_cost")
            with mc6:
                man_rooms = st.number_input("已售房数", 0, 500, 80, key="man_rooms")
            with mc7:
                man_fb = st.number_input("餐饮收入(¥)", 0.0, 500000.0, 8000.0, 500.0, key="man_fb")
            with mc8:
                man_other = st.number_input("其他收入(¥)", 0.0, 200000.0, 2000.0, 500.0, key="man_other")

            if st.button("💾 保存此日数据", key="save_manual_metric"):
                revpar = round(man_occ / 100 * man_adr, 2)
                gop_val = man_rev - man_cost
                gop_rate = round(gop_val / man_rev * 100, 1) if man_rev > 0 else 0

                save_daily_metrics({
                    "date": man_date.strftime("%Y-%m-%d"),
                    "occ": man_occ, "adr": man_adr, "revpar": revpar,
                    "total_revenue": man_rev, "room_revenue": man_rev - man_fb - man_other,
                    "fb_revenue": man_fb, "other_revenue": man_other,
                    "total_cost": man_cost, "gop": gop_val, "gop_rate": gop_rate,
                    "room_sold": man_rooms, "source": "manual",
                })
                st.success(f"✅ {man_date} 数据已保存！RevPAR=¥{revpar:.0f}")
                st.cache_data.clear()

        # 数据概览
        if _DB_READY:
            st.markdown("<hr style='border-color:#2a4a6d;margin:10px 0;'>", unsafe_allow_html=True)
            df_latest = get_latest_metrics(30)
            if not df_latest.empty:
                st.markdown(f'<span style="color:#8899bb;font-size:12px;">📊 数据库中已有 <b>{len(df_latest)}</b> 天经营数据</span>', unsafe_allow_html=True)

                # 快速趋势图
                if "occ" in df_latest.columns and len(df_latest) > 1:
                    fig_db = px.line(
                        df_latest, x="date", y=["occ", "revpar"],
                        title="数据库历史趋势 (近30天)",
                    )
                    fig_db.update_layout(
                        height=250, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font={"color": "#8899bb"}, margin={"l": 0, "r": 0, "t": 30, "b": 0},
                    )
                    st.plotly_chart(fig_db, use_container_width=True, config={"displayModeBar": False})

            # 种子数据按钮
            if df_latest.empty:
                if st.button("🌱 生成90天示例历史数据", key="seed_data", use_container_width=True):
                    from data_import import seed_sample_data
                    n = seed_sample_data(90)
                    st.success(f"✅ 已生成 {n} 天示例数据，可用于测试BI报表功能。")
                    st.rerun()

    # ── Tab 2: OTA 比价导入 ──
    with tab_imp2:
        st.markdown(
            '<div style="color:#8899bb;font-size:13px;margin-bottom:10px;">'
            '导入真实OTA价格CSV，数据会合并到竞品监控表中。</div>',
            unsafe_allow_html=True,
        )

        uploaded_ota = st.file_uploader(
            "📁 拖入OTA比价CSV文件", type=["csv"], key="ota_import_tab",
            help="必须包含：酒店名称, 单价_晚",
        )

        if uploaded_ota is not None:
            try:
                ota_preview = pd.read_csv(uploaded_ota, encoding="utf-8-sig", nrows=10)
                st.dataframe(ota_preview, use_container_width=True, hide_index=True)
            except Exception:
                st.error("无法解析CSV文件")

            if st.button("✅ 确认导入OTA数据", key="confirm_ota_import", use_container_width=True):
                tmp_path = Path(r"E:\工作AI\临时文件") / f"ota_import_{datetime.now().strftime('%Y%m%d%H%M')}.csv"
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path.write_bytes(uploaded_ota.getvalue())

                try:
                    from data_import import import_ota_csv
                    result_df = import_ota_csv(str(tmp_path))
                    st.success(f"✅ 成功导入 {len(result_df)} 条OTA比价数据！")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ 导入失败：{e}")

        # 已导入的数据统计
        comp_prices = get_competitor_prices()
        if not comp_prices.empty:
            st.markdown(f'<span style="color:#8899bb;font-size:12px;">📊 竞品价格库：<b>{len(comp_prices)}</b> 条记录</span>', unsafe_allow_html=True)

    # ── Tab 3: 竞品组管理 ──
    with tab_imp3:
        st.markdown(
            '<div style="color:#8899bb;font-size:13px;margin-bottom:10px;">'
            '管理你的竞争酒店组（Competitive Set），用于OTA比价和定位分析。</div>',
            unsafe_allow_html=True,
        )

        comp_set = get_competitive_set(active_only=False)

        # 添加新竞品
        with st.expander("➕ 添加竞品酒店"):
            nc1, nc2, nc3, nc4, nc5 = st.columns([2, 1, 1, 1, 1])
            with nc1:
                new_name = st.text_input("酒店名称", key="new_comp_name")
            with nc2:
                new_star = st.selectbox("星级", [5, 4, 3, 2], key="new_comp_star")
            with nc3:
                new_city = st.text_input("城市", value="九寨沟", key="new_comp_city")
            with nc4:
                new_addr = st.text_input("地址", key="new_comp_addr")
            with nc5:
                new_price = st.number_input("基础价(¥)", 0, 10000, 500, 50, key="new_comp_price")

            if st.button("✅ 添加竞品", key="add_comp_btn"):
                if new_name:
                    add_competitor(new_name, new_star, new_city, new_addr, new_price)
                    st.success(f"✅ 已添加竞品: {new_name}")
                    st.rerun()

        # 竞品列表
        st.markdown(f'<span style="color:#c8963e;font-size:13px;">📋 当前竞品组 ({len(comp_set)} 家)</span>', unsafe_allow_html=True)

        comp_df = pd.DataFrame(comp_set)
        if not comp_df.empty:
            comp_df["状态"] = comp_df["is_active"].map({1: "🟢 启用", 0: "🔴 停用"})
            display_cols = ["hotel_name", "star_level", "city", "base_price", "状态"]
            avail_cols = [c for c in display_cols if c in comp_df.columns]
            st.dataframe(
                comp_df[avail_cols].rename(columns={
                    "hotel_name": "酒店名称", "star_level": "星级",
                    "city": "城市", "base_price": "基础价",
                }),
                use_container_width=True, hide_index=True,
            )

            # 停用/启用
            col_a, col_b = st.columns([2, 1])
            with col_a:
                rm_name = st.selectbox(
                    "选择要停用的竞品", [c["hotel_name"] for c in comp_set if c.get("is_active")],
                    key="rm_comp",
                )
            with col_b:
                if st.button("🔴 停用此竞品", key="deactivate_comp"):
                    remove_competitor(rm_name)
                    st.rerun()


# ══════════════════════════════════════════════════════════════
# ─── 主入口 ───
# ══════════════════════════════════════════════════════════════

def main():
    # 标题栏
    st.markdown(
        """
    <div class="title-bar">
        <h1>🏨 Hotel AI-RMS — AI收益增长飞轮</h1>
        <div class="sub">知客 → 定价 → 竞品监控 → BI报表 → 触达 → 数据回流</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── 数据库初始化 + 自动种子 ──
    if _DB_READY:
        from database import init_db as db_init
        db_init()
        # 首次运行自动生成种子数据
        try:
            df_check = get_latest_metrics(30)
            if df_check.empty:
                from data_import import seed_sample_data
                seed_sample_data(90)
                st.cache_data.clear()
        except Exception:
            pass

    # 加载数据
    with st.spinner("🔄 正在初始化数据引擎…"):
        customers_df = generate_customer_data(220)
        today = date.today()
        calendar_df = generate_price_calendar(today, 90)

    # ── 自动检测已采集的CSV并导入 ──
    if not st.session_state.get("ota_data_source") or st.session_state["ota_data_source"] == "模拟参考":
        auto_csv = Path(__file__).parent / "ota_real_prices.csv" if "__file__" in dir() else Path("ota_real_prices.csv")
        if auto_csv.exists():
            try:
                auto_df = pd.read_csv(auto_csv)
                if len(auto_df) > 0 and "酒店名称" in auto_df.columns and "单价_晚" in auto_df.columns:
                    st.session_state["ota_imported_df"] = auto_df
                    sources = auto_df.get("数据来源", pd.Series(["模拟参考"]))
                    if any("HTML" in str(s) or "Playwright" in str(s) for s in sources):
                        st.session_state["ota_data_source"] = "CSV导入"
                    st.cache_data.clear()
            except Exception:
                pass

    # Tab导航
    tab_names = ["🏨 收益驾驶舱", "🏔️ 竞品OTA监控", "📊 BI经营报表", "📥 数据导入", "🧠 AI决策日志"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)

    with tab1:
        render_dashboard_tab(customers_df, calendar_df, today)

    with tab2:
        render_ota_tab()

    with tab3:
        render_bi_tab()

    with tab4:
        render_import_tab()

    with tab5:
        render_log_tab()

    # 底部状态栏
    st.markdown("<hr style='border-color:#2a4a6d;margin:12px 0 4px 0;'>", unsafe_allow_html=True)
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        st.markdown(f'<span style="color:#667799;font-size:11px;">📅 {today.strftime("%Y-%m-%d")}</span>', unsafe_allow_html=True)
    with sc2:
        st.markdown(f'<span style="color:#667799;font-size:11px;">👥 客户: {len(customers_df)}</span>', unsafe_allow_html=True)
    with sc3:
        st.markdown(f'<span style="color:#c8963e;font-size:11px;">✅ 已采纳: {len(st.session_state["adopted_prices"])}/90天</span>', unsafe_allow_html=True)
    with sc4:
        st.markdown(f'<span style="color:#28a745;font-size:11px;">📨 触达: {len(st.session_state["sent_messages"])}位</span>', unsafe_allow_html=True)
    with sc5:
        db_status = "🟢 数据库在线" if _DB_READY else "🟡 仅内存"
        st.markdown(f'<span style="color:#667799;font-size:11px;">💾 {db_status}</span>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
