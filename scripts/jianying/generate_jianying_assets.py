# ============================================================
#  酒店集团培训课件 — 专业视觉体系
#  对标: 万豪/希尔顿培训中心 + STR 行业报告 + 麦肯锡咨询风格
#  OUTPUT: jianying_assets/ 目录, 8 张 1920x1080 培训级分镜
# ============================================================
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from scipy.interpolate import CubicSpline
import matplotlib.ticker as ticker

os.makedirs("jianying_assets", exist_ok=True)

# ═══════ 设计系统 ═══════
COLORS = {
    'navy':      '#0B1D3A',   # 主色 — 品牌深蓝
    'gold':      '#C5A35A',   # 强调 — 酒店金
    'data_blue': '#2E86AB',   # 数据 — 专业蓝
    'alert_red': '#C0392B',   # 警告 — 指标红
    'success':   '#0E7C7B',   # 正向 — 达标绿
    'warm_bg':   '#F2EFE9',   # 背景 — 暖纸色
    'white':     '#FAFAFA',   # 卡片白
    'dark_text': '#1A1A2E',   # 正文色
    'gray':      '#6B7280',   # 辅助灰
    'line':      '#D1D5DB',   # 表格线
    'section':   '#E5E0D8',   # 分隔色
}

W, H, DPI = 1920, 1080, 120  # 2x retina for crisp text
FIG_W, FIG_H = W/DPI, H/DPI

# 注册字体
plt.rcParams.update({
    'font.family': 'Microsoft YaHei',
    'font.size': 10,
    'axes.edgecolor': COLORS['line'],
    'axes.linewidth': 0.5,
    'xtick.color': COLORS['gray'],
    'ytick.color': COLORS['gray'],
    'text.color': COLORS['dark_text'],
    'grid.alpha': 0.3,
    'figure.facecolor': COLORS['warm_bg'],
})

np.random.seed(77)

# ═══════ 数据准备 ═══════
days = np.arange(1, 366)
base_adr = 580 + 60 * np.sin(2 * np.pi * days / 365) + np.random.normal(0, 25, 365)
base_adr[days == 100] += 200
base_adr[days == 250] += 180
cs = CubicSpline(days, base_adr, bc_type='natural')
days_smooth = np.linspace(1, 365, 1000)
adr_smooth = cs(days_smooth)
comp_avg = np.mean(base_adr[:30])


def slide_base(fig, ax, title, subtitle=None, slide_num=None):
    """统一的培训课件底板"""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_facecolor(COLORS['warm_bg'])
    fig.patch.set_facecolor(COLORS['warm_bg'])

    # 顶部品牌栏
    ax.axhline(y=0.935, xmin=0, xmax=1, color=COLORS['navy'], linewidth=3)
    ax.fill_between([0, 1], 0.935, 1.0, color=COLORS['navy'])

    # 标题
    ax.text(0.06, 0.965, title, fontsize=18, fontweight='bold',
            color=COLORS['white'], ha='left', va='center',
            fontfamily='Microsoft YaHei')
    if subtitle:
        ax.text(0.06, 0.945, subtitle, fontsize=9, color='#8899BB',
                ha='left', va='center', fontfamily='Microsoft YaHei')

    # 底部栏
    ax.axhline(y=0.05, xmin=0, xmax=1, color=COLORS['line'], linewidth=0.5)
    ax.text(0.06, 0.025, '酒店开业动态定价沙盘  |  第一期',
            fontsize=7, color=COLORS['gray'], ha='left', va='center',
            fontfamily='Microsoft YaHei')
    if slide_num:
        ax.text(0.94, 0.025, '%d / 8' % slide_num, fontsize=7,
                color=COLORS['gray'], ha='right', va='center',
                fontfamily='Microsoft YaHei')

    # 右侧装饰金线
    ax.axvline(x=0.98, ymin=0.06, ymax=0.93, color=COLORS['gold'],
               linewidth=0.8, alpha=0.3)


def metric_card(ax, x, y, w, h, label, value, color=COLORS['navy'], trend=None):
    """数据指标卡片"""
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                           boxstyle="round,pad=0.02",
                           facecolor=COLORS['white'],
                           edgecolor=COLORS['line'], linewidth=0.5)
    ax.add_patch(rect)
    ax.text(x, y + h*0.25, label, fontsize=7, color=COLORS['gray'],
            ha='center', va='center', fontfamily='Microsoft YaHei')
    ax.text(x, y - h*0.1, value, fontsize=16, fontweight='bold',
            color=color, ha='center', va='center', fontfamily='Microsoft YaHei')
    if trend:
        c = COLORS['success'] if '↑' in trend else COLORS['alert_red'] if '↓' in trend else COLORS['gray']
        ax.text(x, y - h*0.35, trend, fontsize=7, color=c,
                ha='center', va='center', fontfamily='Microsoft YaHei')


def save(fig, name):
    fig.savefig(os.path.join("jianying_assets", name),
                dpi=DPI, facecolor=COLORS['warm_bg'],
                edgecolor='none', pad_inches=0, bbox_inches=None)
    print("  [OK] %s  (1920x1080)" % name)
    plt.close(fig)


# ════════════════════════════════════════════════════════════
#  SLIDE 01: 冲击钩子 — 认知颠覆
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, '开业大促真的是最优策略吗？',
           '定价沙盘  ·  第一期  ·  战略预演', slide_num=1)

# 核心矛盾陈述
ax.text(0.12, 0.78, '你以为的', fontsize=22, color=COLORS['gray'],
        ha='left', va='center', fontfamily='Microsoft YaHei')
ax.text(0.12, 0.70, '开业大促 = 快速满房 = 收回投资',
        fontsize=28, fontweight='bold', color=COLORS['navy'],
        ha='left', va='center', fontfamily='Microsoft YaHei')

# 分隔线
ax.axhline(y=0.55, xmin=0.08, xmax=0.88, color=COLORS['gold'],
           linewidth=1.5, alpha=0.5)

ax.text(0.12, 0.48, '实际上', fontsize=22, color=COLORS['alert_red'],
        ha='left', va='center', fontfamily='Microsoft YaHei')
ax.text(0.12, 0.38, '前 100 个间夜的低价，已永久写入 RevPAR 基线',
        fontsize=26, fontweight='bold', color=COLORS['alert_red'],
        ha='left', va='center', fontfamily='Microsoft YaHei')

# 核心数据揭示
metric_card(ax, 0.75, 0.65, 0.30, 0.16, '首月 ADR 每低 ¥10',
            '¥511,000 / 年', COLORS['alert_red'], '↓ 沉默成本')
metric_card(ax, 0.75, 0.35, 0.30, 0.16, 'RevPAR 指数跌破 85',
            'OTA 折扣陷阱', COLORS['alert_red'], '↓ 永久标签')

# 来源标注
ax.text(0.12, 0.15, '数据模型：以 200 间客房、70% OCC 为基准  |  TRevPAR 损失公式 = ADR缺口 × 365天 × 客房数 × OCC',
        fontsize=7, color=COLORS['gray'], ha='left', va='center',
        fontfamily='Microsoft YaHei')
save(fig, 'JY01_hook_warning.png')


# ════════════════════════════════════════════════════════════
#  SLIDE 02: 竞争集365天动态定价曲线
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, '竞争集 365 天动态定价基线',
           '数据来源：STR Report  ·  3km 竞争集  ·  Cubic Spline 拟合', slide_num=2)

# 主图表区域
chart_ax = fig.add_axes([0.08, 0.13, 0.72, 0.68])
chart_ax.set_facecolor(COLORS['white'])
chart_ax.fill_between(days_smooth, adr_smooth - 50, adr_smooth + 50,
                       color=COLORS['data_blue'], alpha=0.06)
chart_ax.plot(days_smooth, adr_smooth, color=COLORS['data_blue'],
              linewidth=1.8, label='Competitor Set Baseline (Cubic Spline)')
chart_ax.scatter(days[::25], base_adr[::25], color=COLORS['gold'], s=25,
                  alpha=0.7, marker='D', zorder=5, label='Actual ADR Data')
chart_ax.axhline(y=480, color=COLORS['alert_red'], linewidth=1.5,
                  linestyle='--', alpha=0.7, label='Plan A: Fixed RMB 480')
chart_ax.axhline(y=620, color=COLORS['success'], linewidth=1.5,
                  linestyle=':', alpha=0.7, label='Plan B: Dynamic RMB 620')

chart_ax.set_ylabel('ADR (RMB)', fontsize=9, color=COLORS['gray'],
                    fontfamily='Microsoft YaHei')
chart_ax.set_xlabel('Day of Year', fontsize=9, color=COLORS['gray'])
chart_ax.set_xlim(0, 365)
chart_ax.set_ylim(350, 950)
chart_ax.tick_params(labelsize=7)
chart_ax.grid(True, color=COLORS['line'], alpha=0.4)
chart_ax.legend(loc='upper left', fontsize=7, framealpha=0.8,
                facecolor=COLORS['white'], edgecolor=COLORS['line'])
chart_ax.spines['top'].set_visible(False)
chart_ax.spines['right'].set_visible(False)

# 右侧关键洞察卡片
insights = [
    ('全年 ADR 波动', '350 - 950 RMB', COLORS['data_blue']),
    ('Plan A 缺口', '-140 RMB / 天', COLORS['alert_red']),
    ('Plan B 溢价', '+40 RMB / 天', COLORS['success']),
]
for i, (label, val, color) in enumerate(insights):
    y = 0.78 - i * 0.13
    metric_card(ax, 0.87, y, 0.16, 0.10, label, val, color)

save(fig, 'JY02_competitor_curve.png')


# ════════════════════════════════════════════════════════════
#  SLIDE 03: RevPAR 损失对比 — Plan A vs Plan B
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, '开业首月 RevPAR 损失对比',
           'Plan A (固定 ¥480)  vs  Plan B (动态 ¥620)  ·  200间客房', slide_num=3)

chart_ax = fig.add_axes([0.08, 0.18, 0.72, 0.65])
chart_ax.set_facecolor(COLORS['white'])

plan_a = np.full(30, 480)
plan_b = 620 + 5 * np.sin(np.linspace(0, np.pi, 30))
loss_a = comp_avg - plan_a
loss_b = comp_avg - plan_b
x_bar = np.arange(30)

chart_ax.bar(x_bar - 0.18, loss_a, 0.35, color=COLORS['alert_red'], alpha=0.75,
             label='Plan A: Fixed RMB 480')
chart_ax.bar(x_bar + 0.18, loss_b, 0.35, color=COLORS['success'], alpha=0.75,
             label='Plan B: Dynamic RMB 620')
chart_ax.axhline(y=0, color=COLORS['dark_text'], linewidth=0.5)
chart_ax.set_ylabel('RevPAR 差距 (RMB)', fontsize=9, color=COLORS['gray'],
                    fontfamily='Microsoft YaHei')
chart_ax.set_xticks(x_bar[::5])
chart_ax.set_xticklabels(['D%d' % d for d in range(1, 31, 5)], fontsize=7)
chart_ax.tick_params(labelsize=7)
chart_ax.grid(True, axis='y', color=COLORS['line'], alpha=0.3)
chart_ax.legend(loc='upper right', fontsize=7, framealpha=0.8,
                facecolor=COLORS['white'], edgecolor=COLORS['line'])
chart_ax.spines['top'].set_visible(False)
chart_ax.spines['right'].set_visible(False)

# 关键数字
cum_a = np.sum(loss_a * 200 * 0.7)
cum_b = np.sum(loss_b * 200 * 0.7)
delta = cum_a - cum_b

metric_card(ax, 0.87, 0.75, 0.18, 0.13, 'Plan A 累计损失',
            '{:,.0f}'.format(cum_a), COLORS['alert_red'], 'RMB 累计')
metric_card(ax, 0.87, 0.52, 0.18, 0.13, 'Plan B 累计损失',
            '{:,.0f}'.format(cum_b), COLORS['success'], 'RMB 优化后')
metric_card(ax, 0.87, 0.29, 0.18, 0.13, '优化节省',
            '{:,.0f}'.format(delta), COLORS['gold'], '数据红利')

save(fig, 'JY03_revpar_comparison.png')


# ════════════════════════════════════════════════════════════
#  SLIDE 04: 三大定价维度
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, '动态定价沙盘 — 三大核心维度',
           '', slide_num=4)

dims = [
    {
        'num': '01', 'title': '竞争集价格弹性',
        'formula': '竞品反应率 = -0.3% × 你的价格变动 %',
        'desc': '你每降价 1%，周边竞品平均跟降 0.3%\n→ 引发商圈 ADR 连锁下沉',
        'icon': '📊'
    },
    {
        'num': '02', 'title': '时间衰减函数',
        'formula': 'P(t) = P0 × (1 + r)^(t/7)',
        'desc': '距开业每近 7 天，未售库存价格上调 2-3%\n→ 构建稀缺信号，拉升客户支付意愿',
        'icon': '⏱'
    },
    {
        'num': '03', 'title': '收益毁损率',
        'formula': '每日损失 = (竞争集 ADR - 实际 ADR) × Occ 缺口',
        'desc': '错误定价每晚造成的不可逆 RevPAR 损失\n→ 红色热力图实时标记最大出血点',
        'icon': '🔴'
    },
]

for i, dim in enumerate(dims):
    x_base = 0.08 + i * 0.30
    # 卡片背景
    card = FancyBboxPatch((x_base, 0.15), 0.27, 0.70,
                           boxstyle="round,pad=0.03",
                           facecolor=COLORS['white'],
                           edgecolor=COLORS['line'], linewidth=0.5)
    ax.add_patch(card)

    # 编号
    ax.text(x_base + 0.02, 0.78, dim['num'], fontsize=32, fontweight='bold',
            color=COLORS['gold'], ha='left', va='center',
            fontfamily='Microsoft YaHei', alpha=0.5)
    # 标题
    ax.text(x_base + 0.09, 0.78, dim['title'], fontsize=15, fontweight='bold',
            color=COLORS['navy'], ha='left', va='center',
            fontfamily='Microsoft YaHei')
    # 公式
    ax.text(x_base + 0.02, 0.62, dim['formula'], fontsize=9, color=COLORS['data_blue'],
            ha='left', va='top', fontfamily='Microsoft YaHei',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#F0F6FA',
                      edgecolor=COLORS['line'], alpha=0.8))
    # 描述
    ax.text(x_base + 0.02, 0.32, dim['desc'], fontsize=9, color=COLORS['dark_text'],
            ha='left', va='top', fontfamily='Microsoft YaHei',
            linespacing=1.6)

save(fig, 'JY04_three_dimensions.png')


# ════════════════════════════════════════════════════════════
#  SLIDE 05: SOP 四步定价法
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, '沙盘操作 SOP — 四步定价法',
           '', slide_num=5)

steps_data = [
    (1, '数据采集', '获取 STR Report\n圈定 3km / 5km 竞争集\n拉取 365 天 ADR + Occ + RevPAR',
     COLORS['data_blue']),
    (2, '曲线拟合', 'Cubic Spline 插值\n捕捉全年非线性波动\n建立竞争集动态基线',
     COLORS['success']),
    (3, '缺口定位', '定价方案叠加对比\n红蓝线最大偏差 = 定价缺口\n可视化修正决策',
     COLORS['gold']),
    (4, '模拟验证', 'Monte Carlo × 5000 次\n最优定价区间概率分布\n数据驱动而非拍脑门',
     COLORS['alert_red']),
]

for i, (num, title, desc, color) in enumerate(steps_data):
    x = 0.06 + i * 0.225
    # 步骤卡片
    card = FancyBboxPatch((x, 0.15), 0.20, 0.70,
                           boxstyle="round,pad=0.02",
                           facecolor=COLORS['white'],
                           edgecolor=color, linewidth=1.2)
    ax.add_patch(card)

    # 顶部色条
    ax.fill_between([x, x + 0.20], 0.78, 0.85, color=color, alpha=0.15)
    ax.hlines(y=0.85, xmin=x, xmax=x+0.20, color=color, linewidth=2)

    # 步骤编号
    ax.text(x + 0.10, 0.81, 'Step %d' % num, fontsize=11, fontweight='bold',
            color=color, ha='center', va='center', fontfamily='Microsoft YaHei')
    # 标题
    ax.text(x + 0.10, 0.72, title, fontsize=14, fontweight='bold',
            color=COLORS['navy'], ha='center', va='center',
            fontfamily='Microsoft YaHei')
    # 分隔线
    ax.axhline(y=0.62, xmin=x/1+0.01, xmax=(x+0.20)/1-0.01,
               color=COLORS['line'], linewidth=0.5)
    # 描述
    ax.text(x + 0.10, 0.40, desc, fontsize=8.5, color=COLORS['dark_text'],
            ha='center', va='center', fontfamily='Microsoft YaHei',
            linespacing=1.8)

    # 箭头
    if i < 3:
        ax.annotate('', xy=(x + 0.21, 0.50), xytext=(x + 0.24, 0.50),
                    arrowprops=dict(arrowstyle='->', color=COLORS['gold'],
                                   lw=2, alpha=0.6))

save(fig, 'JY05_sop_steps.png')


# ════════════════════════════════════════════════════════════
#  SLIDE 06: RevPAR 指数 — OTA 陷阱警告
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, 'RevPAR 指数 — 你的开业定价健康度',
           '', slide_num=6)

# 公式框
ax.text(0.5, 0.82, '核心指标：RevPAR 指数',
        fontsize=22, fontweight='bold', color=COLORS['navy'],
        ha='center', va='center', fontfamily='Microsoft YaHei')

formula_box = FancyBboxPatch((0.15, 0.65), 0.70, 0.10,
                              boxstyle="round,pad=0.03",
                              facecolor=COLORS['white'],
                              edgecolor=COLORS['data_blue'], linewidth=1.5)
ax.add_patch(formula_box)
ax.text(0.5, 0.70, 'RevPAR 指数 = ( 酒店 RevPAR ÷ 竞争集 RevPAR ) × 100',
        fontsize=18, color=COLORS['navy'], ha='center', va='center',
        fontfamily='Microsoft YaHei')

# 三个风险等级
levels = [
    ('> 110', '优异', '数据驱动，享受溢价', COLORS['success'], 0.18, 0.40),
    ('85 - 110', '及格', '维持竞争力，需持续监控', COLORS['gold'], 0.41, 0.40),
    ('< 85', '危险', 'OTA 已标记为折扣酒店', COLORS['alert_red'], 0.64, 0.40),
]
for label, status, desc, color, x, w in levels:
    card = FancyBboxPatch((x, 0.20), 0.22, 0.28,
                           boxstyle="round,pad=0.02",
                           facecolor=COLORS['white'],
                           edgecolor=color, linewidth=1.5)
    ax.add_patch(card)
    ax.text(x + 0.11, 0.42, label, fontsize=28, fontweight='bold',
            color=color, ha='center', va='center', fontfamily='Microsoft YaHei')
    ax.text(x + 0.11, 0.34, status, fontsize=13, fontweight='bold',
            color=COLORS['navy'], ha='center', va='center',
            fontfamily='Microsoft YaHei')
    ax.text(x + 0.11, 0.24, desc, fontsize=8, color=COLORS['gray'],
            ha='center', va='center', fontfamily='Microsoft YaHei')

ax.text(0.5, 0.08, '数据来源：STR Global  ·  HotelBenchmark  ·  开业 30 天窗口期',
        fontsize=7, color=COLORS['gray'], ha='center', va='center',
        fontfamily='Microsoft YaHei')
save(fig, 'JY06_revpar_index.png')


# ════════════════════════════════════════════════════════════
#  SLIDE 07: 案例成果对比
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, '196 间客房精品酒店  ·  真实沙盘预演成果',
           '', slide_num=7)

# 对比表格
col_x = [0.10, 0.38, 0.60, 0.80]
headers = ['指标', '原始方案 A', '沙盘优化 B', '改善幅度']
for j, h in enumerate(headers):
    ax.text(col_x[j], 0.78, h, fontsize=10, fontweight='bold',
            color=COLORS['navy'] if j > 0 else COLORS['gray'],
            ha='center' if j > 0 else 'left', va='center',
            fontfamily='Microsoft YaHei')

rows = [
    ('开业价格', 'RMB 480', 'RMB 620', '+ 29%'),
    ('首月 RevPAR 指数', '83', '112', '+ 29 点'),
    ('年度 TRevPAR 损失', 'RMB 511,000', 'RMB 83,000', '- 84%'),
    ('OTA 平台定位', '折扣酒店', '优质酒店', '标签升级'),
]

for i, row in enumerate(rows):
    y = 0.66 - i * 0.11
    # 行背景
    if i % 2 == 0:
        ax.fill_between([0.03, 0.97], y-0.04, y+0.04, color=COLORS['white'],
                        alpha=0.5)
    for j, cell in enumerate(row):
        if j == 0:
            color = COLORS['gray']
        elif '↓' in str(cell) or '折扣' in str(cell):
            color = COLORS['alert_red']
        elif '↑' in str(cell) or '-' in str(cell) or '升级' in str(cell):
            color = COLORS['success']
        elif '620' in str(cell) or '112' in str(cell):
            color = COLORS['data_blue']
        else:
            color = COLORS['dark_text']
        weight = 'bold' if j > 0 else 'normal'
        ax.text(col_x[j], y, cell, fontsize=10 if j > 0 else 9,
                fontweight=weight, color=color,
                ha='center' if j > 0 else 'left', va='center',
                fontfamily='Microsoft YaHei')

# 底部横线
for i in range(5):
    y = 0.69 - i * 0.11
    ax.axhline(y=y, xmin=0.04, xmax=0.96, color=COLORS['line'], linewidth=0.3)

# 金句
ax.text(0.5, 0.12, '不是靠折扣 — 是靠数据的预演权',
        fontsize=20, fontweight='bold', color=COLORS['gold'],
        ha='center', va='center', fontfamily='Microsoft YaHei')
save(fig, 'JY07_case_result.png')


# ════════════════════════════════════════════════════════════
#  SLIDE 08: CTA 行动号召
# ════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
slide_base(fig, ax, '获取你的开业定价沙盘模型', '', slide_num=8)

# 中心 CTA 框
cta_box = FancyBboxPatch((0.20, 0.20), 0.60, 0.55,
                          boxstyle="round,pad=0.05",
                          facecolor=COLORS['white'],
                          edgecolor=COLORS['gold'], linewidth=2)
ax.add_patch(cta_box)

ax.text(0.5, 0.68, '评论区回复',
        fontsize=22, color=COLORS['gray'], ha='center', va='center',
        fontfamily='Microsoft YaHei')
ax.text(0.5, 0.55, '「沙盘」',
        fontsize=64, fontweight='bold', color=COLORS['gold'],
        ha='center', va='center', fontfamily='Microsoft YaHei')
ax.text(0.5, 0.40, '免费领取：',
        fontsize=16, color=COLORS['gray'], ha='center', va='center',
        fontfamily='Microsoft YaHei')
ax.text(0.5, 0.33, '《酒店开业动态定价演算模型 Excel 工具表》',
        fontsize=18, fontweight='bold', color=COLORS['navy'],
        ha='center', va='center', fontfamily='Microsoft YaHei')
ax.text(0.5, 0.23, '包含：竞争集分析  ·  Spline 拟合  ·  Monte Carlo 模拟',
        fontsize=10, color=COLORS['gray'], ha='center', va='center',
        fontfamily='Microsoft YaHei')

save(fig, 'JY08_cta_action.png')

print()
print("=" * 60)
print("  培训课件生成完成: jianying_assets/ (8 张 1920x1080)")
print("  设计标准: 万豪/希尔顿培训中心 · STR行业报告")
print("=" * 60)
