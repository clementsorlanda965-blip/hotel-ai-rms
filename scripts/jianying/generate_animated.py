# ============================================================
#  专业级数据动画 — 酒店集团培训课件标准
#  先逐帧渲染PNG，再用ffmpeg合成1920x1080 MP4
# ============================================================
import os, sys, subprocess, shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline

# ── 设计系统 ──
COLORS = {
    'navy':      '#0B1D3A',
    'gold':      '#C5A35A',
    'data_blue': '#2E86AB',
    'alert_red': '#C0392B',
    'success':   '#0E7C7B',
    'warm_bg':   '#F2EFE9',
    'white':     '#FAFAFA',
    'dark_text': '#1A1A2E',
    'gray':      '#6B7280',
    'line':      '#D1D5DB',
}

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

# Data
days_365 = np.arange(1, 366)
base_adr = 580 + 60 * np.sin(2 * np.pi * days_365 / 365) + np.random.normal(0, 25, 365)
base_adr[days_365 == 100] += 200; base_adr[days_365 == 250] += 180
cs = CubicSpline(days_365, base_adr, bc_type='natural')
days_smooth = np.linspace(1, 365, 1000)
adr_smooth = cs(days_smooth)

# ffmpeg
FFMPEG = None
for c in [os.path.join(os.environ.get('LOCALAPPDATA',''), r'JianyingPro\Apps\10.5.0.13988\ffmpeg.exe'),
          'ffmpeg', 'ffmpeg.exe']:
    try: subprocess.run([c, '-version'], capture_output=True, timeout=5); FFMPEG = c; break
    except: pass
print('[ffmpeg] %s' % (FFMPEG or 'NOT FOUND'))

BASE = 'charts/animated'
os.makedirs(BASE, exist_ok=True)
W, H, DPI = 1920, 1080, 120

def frames_to_mp4(frame_dir, output, fps=24):
    if not FFMPEG: return
    for codec in ['libx264', 'mpeg4']:
        cmd = [FFMPEG, '-y', '-framerate', str(fps),
               '-i', os.path.join(frame_dir, 'frame_%04d.png'),
               '-c:v', codec, '-pix_fmt', 'yuv420p']
        if codec == 'libx264':
            cmd += ['-profile:v', 'baseline', '-crf', '23', '-b:v', '3000k']
        else:
            cmd += ['-q:v', '3']
        cmd.append(output)
        try:
            subprocess.run(cmd, capture_output=True, timeout=180, check=True)
            print('  -> %s (%s)' % (os.path.basename(output), codec))
            return
        except: pass


def brand_header(fig, ax, title, subtitle=''):
    """统一品牌头部"""
    ax.fill_between([0, 1], 0.935, 1.0, color=COLORS['navy'])
    ax.axhline(y=0.935, color=COLORS['navy'], linewidth=3)
    ax.text(0.06, 0.965, title, fontsize=16, fontweight='bold',
            color='white', ha='left', va='center', fontfamily='Microsoft YaHei')
    if subtitle:
        ax.text(0.06, 0.945, subtitle, fontsize=7, color='#8899BB',
                ha='left', va='center', fontfamily='Microsoft YaHei')
    ax.axvline(x=0.98, ymin=0.06, ymax=0.93, color=COLORS['gold'],
               linewidth=0.8, alpha=0.3)
    ax.text(0.94, 0.025, 'Hotel Pricing Sandbox', fontsize=6,
            color=COLORS['gray'], ha='right', va='center')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')


# ════════════════════════════════════════════════════════════
#  ANIM 01: 竞争集曲线实时绘制
# ════════════════════════════════════════════════════════════
print('[1/3] Competitor Curve Animation')
frame_dir = os.path.join(BASE, 'anim01')
if os.path.exists(frame_dir): shutil.rmtree(frame_dir)
os.makedirs(frame_dir)

for f in range(100):
    idx = max(1, int((f + 1) * 10))
    x_data = days_smooth[:idx]; y_data = adr_smooth[:idx]
    current_day = max(x_data)

    fig, ax = plt.subplots(figsize=(W/DPI, H/DPI), facecolor=COLORS['warm_bg'])
    ax.set_facecolor(COLORS['white'])
    ax.set_xlim(0, 365); ax.set_ylim(350, 950)
    ax.set_ylabel('ADR (RMB)', fontsize=9, color=COLORS['gray'])
    ax.fill_between(days_smooth[:idx], adr_smooth[:idx]-50, adr_smooth[:idx]+50,
                    color=COLORS['data_blue'], alpha=0.04)
    ax.plot(x_data, y_data, color=COLORS['data_blue'], linewidth=2)
    mask = days_365 <= current_day
    if np.any(mask):
        ax.scatter(days_365[mask][::3], base_adr[mask][::3],
                   color=COLORS['gold'], s=12, alpha=0.5, marker='D', zorder=5)
    ax.axhline(y=480, color=COLORS['alert_red'], linewidth=1, linestyle='--', alpha=0.5)
    ax.axhline(y=620, color=COLORS['success'], linewidth=1, linestyle=':', alpha=0.5)
    ax.grid(True, color=COLORS['line'], alpha=0.3)
    ax.tick_params(labelsize=7)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    brand_header(fig, ax, '竞争集 365 天动态定价基线',
                 'Cubic Spline 拟合  |  Day %d/365  |  %d%% Complete' % (int(current_day), int(current_day/365*100)))

    fig.savefig(os.path.join(frame_dir, 'frame_%04d.png' % f),
                dpi=DPI, facecolor=COLORS['warm_bg'], edgecolor='none')
    plt.close(fig)
    if f % 25 == 0: print('  frame %d/100' % f)

frames_to_mp4(frame_dir, os.path.join(BASE, '01_competitor_curve.mp4'))


# ════════════════════════════════════════════════════════════
#  ANIM 02: RevPAR 损失对比柱状图
# ════════════════════════════════════════════════════════════
print('[2/3] RevPAR Loss Battle')
frame_dir = os.path.join(BASE, 'anim02')
if os.path.exists(frame_dir): shutil.rmtree(frame_dir)
os.makedirs(frame_dir)

comp_avg = np.mean(base_adr[:30])
loss_a = comp_avg - np.full(30, 480)
loss_b = comp_avg - (620 + 5 * np.sin(np.linspace(0, np.pi, 30)))
y_max = max(np.max(loss_a), np.max(loss_b)) + 20

for f in range(30):
    n = f + 1
    fig, ax = plt.subplots(figsize=(W/DPI, H/DPI), facecolor=COLORS['warm_bg'])
    ax.set_facecolor(COLORS['white'])
    ax.set_xlim(-0.8, 29.8); ax.set_ylim(-10, y_max)
    ax.set_ylabel('RevPAR Gap (RMB)', fontsize=9, color=COLORS['gray'])
    ax.grid(True, axis='y', color=COLORS['line'], alpha=0.3)
    ax.tick_params(labelsize=7)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    x_pos = np.arange(n); w = 0.35
    ax.bar(x_pos - w/2, loss_a[:n], w, color=COLORS['alert_red'], alpha=0.8)
    ax.bar(x_pos + w/2, loss_b[:n], w, color=COLORS['success'], alpha=0.8)

    cum_a = np.sum(loss_a[:n] * 200 * 0.7)
    cum_b = np.sum(loss_b[:n] * 200 * 0.7)
    delta = cum_a - cum_b

    brand_header(fig, ax, '开业首月 RevPAR 损失追踪',
                 'Day %d/30  |  Plan A vs Plan B  |  Saved: RMB {:,.0f}' .format(delta))

    fig.savefig(os.path.join(frame_dir, 'frame_%04d.png' % f),
                dpi=DPI, facecolor=COLORS['warm_bg'], edgecolor='none')
    plt.close(fig)
    if f % 5 == 0: print('  frame %d/30' % f)

frames_to_mp4(frame_dir, os.path.join(BASE, '02_revpar_loss.mp4'))


# ════════════════════════════════════════════════════════════
#  ANIM 03: Monte Carlo 概率分布
# ════════════════════════════════════════════════════════════
print('[3/3] Monte Carlo Convergence')
frame_dir = os.path.join(BASE, 'anim03')
if os.path.exists(frame_dir): shutil.rmtree(frame_dir)
os.makedirs(frame_dir)

np.random.seed(42)
mc_prices = np.random.normal(620, 60, 5000)
mc_demand = 1 - 0.3 * ((mc_prices - 620) / 620)
mc_occ = np.clip(mc_demand * 0.72 + np.random.normal(0, 0.05, 5000), 0, 1)
mc_index = 100 * (mc_prices * mc_occ) / (620 * 0.72)

for f in range(50):
    n = (f + 1) * 100
    data = mc_index[:n]

    fig, ax = plt.subplots(figsize=(W/DPI, H/DPI), facecolor=COLORS['warm_bg'])
    ax.set_facecolor(COLORS['white'])
    ax.set_xlim(60, 140); ax.set_ylim(0, 250)
    ax.set_xlabel('RevPAR Index', fontsize=9, color=COLORS['gray'])
    ax.set_ylabel('Frequency', fontsize=9, color=COLORS['gray'])
    ax.grid(True, axis='y', color=COLORS['line'], alpha=0.3)
    ax.tick_params(labelsize=7)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # Threshold lines
    ax.axvline(x=85, color=COLORS['alert_red'], linewidth=2, linestyle='--', alpha=0.6)
    ax.axvline(x=112, color=COLORS['success'], linewidth=2, linestyle=':', alpha=0.6)

    # Histogram with gradient color based on index range
    bins = np.linspace(60, 140, 51)
    counts, _ = np.histogram(data, bins=bins)
    colors_hist = []
    for b in bins[:-1]:
        if b < 85: colors_hist.append(COLORS['alert_red'])
        elif b < 112: colors_hist.append(COLORS['gold'])
        else: colors_hist.append(COLORS['success'])
    ax.bar(bins[:-1], counts, width=np.diff(bins), color=colors_hist,
           alpha=0.5, edgecolor='white', linewidth=0.3)

    above_112 = np.sum(data >= 112) / n * 100
    below_85 = np.sum(data <= 85) / n * 100
    median_val = np.median(data)

    brand_header(fig, ax, 'Monte Carlo 模拟  |  RevPAR 指数概率分布',
                 '%d/5000 Iterations  |  Median: %.1f  |  P(>112)=%.1f%%' % (n, median_val, above_112))

    # Risk annotation
    ax.text(85, 230, 'OTA Discount\nTrap (< 85)', fontsize=7, color=COLORS['alert_red'],
            ha='right', va='top', fontfamily='Microsoft YaHei')
    ax.text(112, 230, 'Target\n(> 112)', fontsize=7, color=COLORS['success'],
            ha='left', va='top', fontfamily='Microsoft YaHei')

    fig.savefig(os.path.join(frame_dir, 'frame_%04d.png' % f),
                dpi=DPI, facecolor=COLORS['warm_bg'], edgecolor='none')
    plt.close(fig)
    if f % 10 == 0: print('  frame %d/50' % f)

frames_to_mp4(frame_dir, os.path.join(BASE, '03_monte_carlo.mp4'))

print()
print('=' * 60)
print('  3 Professional MP4 Animations Generated')
print('  Style: Hotel Training Deck  ·  1920x1080')
print('=' * 60)
