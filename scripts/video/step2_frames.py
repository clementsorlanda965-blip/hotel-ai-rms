# =============================================
# step2_frames.py - 视频流水线第2步：画面生成
# 输入: output/script.json
# 输出: output/frames/scene_*.png (10张 1080×1920 竖屏帧)
# 使用 PIL 渲染文字卡片，含渐变背景+装饰元素+字幕+情绪标签
# =============================================
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json, os, platform, math, random

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

os.makedirs('output/frames', exist_ok=True)

# Font
FONT_PATH = None
FONT_INDEX = 0
if platform.system() == 'Windows':
    for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/msyhbd.ttc']:
        if os.path.exists(fp):
            FONT_PATH = fp
            break
if not FONT_PATH:
    raise RuntimeError('No CJK font found')

W, H = 1080, 1920
TOTAL = len(scenes)

# Scene-specific background palettes
PALETTES = [
    # (gradient_top, gradient_bot, accent, decor_color, mood_text)
    # Scene 0: Blood hook
    ((40, 5, 5), (10, 2, 2), (220, 40, 40), (180, 80, 80), "#blood"),
    # Scene 1: Winter mystery
    ((5, 10, 25), (15, 20, 35), (60, 100, 160), (100, 130, 180), "#winter"),
    # Scene 2: Temple fire
    ((35, 15, 5), (15, 5, 2), (200, 100, 30), (160, 120, 50), "#fire"),
    # Scene 3: Imperial court
    ((40, 20, 5), (20, 10, 2), (180, 140, 30), (140, 110, 40), "#gold"),
    # Scene 4: Execution
    ((45, 5, 5), (15, 2, 2), (200, 30, 30), (150, 80, 80), "#blood2"),
    # Scene 5: Political intrigue
    ((5, 15, 25), (10, 20, 30), (80, 120, 160), (100, 140, 180), "#intrigue"),
    # Scene 6: Wisdom
    ((10, 10, 20), (20, 15, 30), (100, 80, 140), (130, 110, 160), "#ink"),
    # Scene 7: Imperial power
    ((30, 5, 5), (10, 2, 2), (180, 130, 20), (140, 100, 30), "#power"),
    # Scene 8: Reflection
    ((5, 5, 15), (15, 10, 25), (60, 60, 100), (100, 100, 140), "#shadow"),
    # Scene 9: Dawn
    ((15, 10, 5), (25, 20, 10), (200, 150, 60), (160, 130, 80), "#dawn"),
]

def draw_circle_pattern(draw, cx, cy, r, color, alpha=30):
    """Draw decorative semi-transparent circles (像水墨/月轮)"""
    for i in range(3):
        rr = r + i * 25
        for x in range(cx - rr, cx + rr):
            for y in range(cy - rr, cy + rr):
                dx, dy = x - cx, y - cy
                if dx*dx + dy*dy <= rr*rr and 0 <= x < W and 0 <= y < H:
                    dist = math.sqrt(dx*dx + dy*dy) / rr
                    a = int((1 - dist) * alpha * (0.5 + 0.5 * (1 - i/3)))
                    if a > 5:
                        px = draw.im.getpixel((x, y))
                        new_px = tuple(
                            min(255, int(c + (color[c_idx] - c) * a / 255))
                            for c_idx, c in enumerate(px[:3])
                        )
                        draw.point((x, y), fill=new_px)

def draw_sakura(draw, x, y, size, color):
    """Draw simple decorative petal"""
    for i in range(5):
        angle = i * 72 - 90
        px = x + int(math.cos(math.radians(angle)) * size)
        py = y + int(math.sin(math.radians(angle)) * size)
        draw.ellipse([px-size//2, py-size//4, px+size//2, py+size//4],
                     fill=(color[0], color[1], color[2], 40))

for idx, scene in enumerate(scenes):
    palette = PALETTES[idx]
    img = Image.new('RGB', (W, H), palette[0])
    draw = ImageDraw.Draw(img, 'RGBA')
    pixels = img.load()

    # Vertical gradient background
    for y in range(H):
        ratio = y / H
        r = int(palette[0][0] * (1 - ratio) + palette[1][0] * ratio)
        g = int(palette[0][1] * (1 - ratio) + palette[1][1] * ratio)
        b = int(palette[0][2] * (1 - ratio) + palette[1][2] * ratio)
        for x in range(W):
            pixels[x, y] = (r, g, b)

    # Decorative circles (moon/sun effect)
    draw_circle_pattern(ImageDraw.Draw(img, 'RGBA'),
                         W//3, H//4, 180, palette[2], 25)
    draw_circle_pattern(ImageDraw.Draw(img, 'RGBA'),
                         W*2//3, H*3//4, 120, palette[3], 18)

    # Horizontal lines (ancient scroll effect)
    for i in range(3):
        ly = H // 3 + i * (H // 6)
        for x in range(W):
            brightness = max(0, min(255, pixels[x, ly][0] + 8))
            pixels[x, ly] = (brightness, brightness, brightness)

    # Decorative border — thin rectangle frame
    border_color = palette[2]
    margin = 60
    draw.rectangle([margin, margin, W-margin, H-margin],
                   outline=(border_color[0], border_color[1], border_color[2], 50), width=2)

    # Corner ornaments
    for cx, cy in [(margin+5, margin+5), (W-margin-5, margin+5),
                   (margin+5, H-margin-5), (W-margin-5, H-margin-5)]:
        draw.ellipse([cx-8, cy-8, cx+8, cy+8],
                     fill=(border_color[0], border_color[1], border_color[2], 80))

    # Scene number — top right
    font_sm = ImageFont.truetype(FONT_PATH, 28, index=FONT_INDEX)
    draw.text((W - 180, 90), f'{idx+1:02d} / {TOTAL:02d}',
              fill=(180, 180, 200, 120), font=font_sm)

    # Main title — large centered with shadow
    title = scene.get('subtitle', '')
    font_title = ImageFont.truetype(FONT_PATH, 72, index=FONT_INDEX)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (W - tw) // 2, H // 3 - 30

    # Multi-layer text: shadow → glow → main
    for ox, oy in [(4, 4), (3, 3), (2, 2), (0, 0)]:
        layer = (0, 0, 0, 60) if ox > 0 else (255, 255, 255, 255)
        draw.text((tx + ox, ty + oy), title, fill=layer, font=font_title)

    # Emotion tag — bottom of title
    emotion = scene.get('emotion', '')
    if emotion:
        emo_colors = {
            'hook': (255, 80, 80), '悬念': (100, 180, 255), '冲突': (255, 180, 50),
            '亢奋': (255, 200, 50), '转折': (100, 255, 200), '顿悟': (200, 150, 255),
            '梗慨': (180, 100, 180), '共鸣': (100, 200, 220), '激励': (80, 255, 120)
        }
        ec = emo_colors.get(emotion, (150, 150, 150))
        font_tag = ImageFont.truetype(FONT_PATH, 34, index=FONT_INDEX)
        tag_text = f'# {emotion}'
        bbox2 = draw.textbbox((0, 0), tag_text, font=font_tag)
        lw = bbox2[2] - bbox2[0]
        draw.text(((W - lw)//2, ty + th + 30), tag_text,
                  fill=(ec[0], ec[1], ec[2], 200), font=font_tag)

    # Narration excerpt — lower section
    narration = scene.get('narration', '')
    font_sub = ImageFont.truetype(FONT_PATH, 32, index=FONT_INDEX)
    lines = []
    cur = ''
    for ch in narration:
        cur += ch
        if len(cur) >= 18 or ch in '。！？':
            lines.append(cur)
            cur = ''
    if cur:
        lines.append(cur)

    y_off = H * 2 // 3 - len(lines) * 25
    for line in lines[:4]:
        bbox3 = draw.textbbox((0, 0), line, font=font_sub)
        lw = bbox3[2] - bbox3[0]
        draw.text(((W - lw)//2 + 2, y_off + 2), line, fill=(0, 0, 0, 60), font=font_sub)
        draw.text(((W - lw)//2, y_off), line, fill=(180, 185, 210, 220), font=font_sub)
        y_off += 50

    # Progress dots bottom
    dot_y, spacing = H - 140, 36
    max_dots = min(TOTAL, 7)
    start_x = (W - (max_dots - 1) * spacing) // 2
    for d in range(max_dots):
        cx2 = start_x + d * spacing
        if d == idx:
            for r in range(7, 2, -1):
                a = int(40 * (r - 2) / 5)
                draw.ellipse([cx2 - r, dot_y - r, cx2 + r, dot_y + r],
                             fill=(255, 215, 0, a))
            draw.ellipse([cx2 - 6, dot_y - 6, cx2 + 6, dot_y + 6],
                         fill=(255, 215, 0))
        else:
            draw.ellipse([cx2 - 5, dot_y - 5, cx2 + 5, dot_y + 5],
                         fill=(60, 60, 70, 150))

    # Duration label
    dur = scene['end'] - scene['start']
    dur_text = f'{dur:.0f}s'
    font_dur = ImageFont.truetype(FONT_PATH, 22, index=FONT_INDEX)
    bbox4 = draw.textbbox((0, 0), dur_text, font=font_dur)
    dw = bbox4[2] - bbox4[0]
    draw.text(((W - dw)//2, H - 90), dur_text, fill=(100, 100, 120, 120), font=font_dur)

    img.save(f'output/frames/scene_{idx:02d}.png')
    print(f'  [{idx+1}/{TOTAL}] {title[:25]}')

print(f'\n[2/6] 画面生成完成: output/frames/ ({TOTAL} 张)')
