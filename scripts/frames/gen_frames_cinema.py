from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json, os, platform, random, math

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

os.makedirs('output/frames', exist_ok=True)

# Font
FONT_PATH = None
IDX = 0
if platform.system() == 'Windows':
    for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc']:
        if os.path.exists(fp):
            FONT_PATH = fp
            break
if not FONT_PATH:
    raise RuntimeError('No font')

W, H = 1080, 1920
TOTAL = len(scenes)

# Cinematic color palette per emotion (dark film style)
EMOTION_PALETTE = {
    'hook':    {'bg': (8, 10, 18),   'accent': (180, 40, 40),   'text': (240, 235, 225)},
    '共鸣':    {'bg': (12, 15, 25),  'accent': (60, 120, 200),   'text': (220, 225, 235)},
    '冲突':    {'bg': (15, 12, 12),  'accent': (220, 140, 30),   'text': (235, 225, 210)},
    '亢奋':    {'bg': (10, 12, 20),  'accent': (240, 180, 20),   'text': (240, 235, 220)},
    '转折':    {'bg': (14, 18, 22),  'accent': (80, 200, 160),   'text': (225, 235, 230)},
    '顿悟':    {'bg': (18, 14, 24),  'accent': (160, 120, 220),  'text': (235, 230, 245)},
    '激励':    {'bg': (12, 15, 22),  'accent': (200, 160, 60),   'text': (240, 235, 220)},
    '行动':    {'bg': (10, 15, 12),  'accent': (60, 200, 100),   'text': (230, 240, 225)},
}

def add_film_grain(img, intensity=8):
    """Add subtle film grain"""
    import numpy as np
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-intensity, intensity+1, arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

def add_vignette(img, strength=0.4):
    """Add dark vignette effect"""
    import numpy as np
    arr = np.array(img, dtype=np.float64)
    h, w = arr.shape[:2]
    cx, cy = w/2, h/2
    max_dist = math.sqrt(cx**2 + cy**2)
    for y in range(h):
        for x in range(0, w, 4):  # Every 4 pixels for speed
            dist = math.sqrt((x-cx)**2 + (y-cy)**2)
            factor = 1 - (dist/max_dist) * strength
            factor = max(0.3, factor)
            arr[y, x:x+4] *= factor
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def draw_chinese_pattern(draw, img_w, img_h, color, alpha=30):
    """Draw subtle cloud/dragon pattern borders"""
    color_with_alpha = tuple(min(255, c + alpha) for c in color)
    # Top decorative line
    for x in range(0, img_w, 3):
        y = 80 + int(15 * math.sin(x / 80))
        if 0 <= y < img_h:
            draw.point((x, y), fill=color_with_alpha)
    # Bottom decorative line
    for x in range(0, img_w, 3):
        y = img_h - 200 + int(15 * math.sin(x / 80 + 1))
        if 0 <= y < img_h:
            draw.point((x, y), fill=color_with_alpha)

for idx, scene in enumerate(scenes):
    emotion = scene.get('emotion', 'hook')
    pal = EMOTION_PALETTE.get(emotion, EMOTION_PALETTE['hook'])
    
    img = Image.new('RGB', (W, H), pal['bg'])
    draw = ImageDraw.Draw(img)
    
    # 1. Subtle Chinese pattern border
    draw_chinese_pattern(draw, W, H, pal['accent'], alpha=25)
    
    # 2. Top cinematic glow
    for y in range(350):
        ratio = 1 - y / 350
        r = int(pal['bg'][0] + (pal['accent'][0] - pal['bg'][0]) * ratio * 0.3)
        g = int(pal['bg'][1] + (pal['accent'][1] - pal['bg'][1]) * ratio * 0.3)
        b = int(pal['bg'][2] + (pal['accent'][2] - pal['bg'][2]) * ratio * 0.3)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    
    # 3. Horizontal light streak (cinematic anamorphic flare)
    flare_y = int(H * 0.38)
    for dy in range(-80, 80):
        alpha = math.exp(-(dy**2) / 2000) * 0.08
        r = int(pal['accent'][0] * alpha)
        g = int(pal['accent'][1] * alpha)
        b = int(pal['accent'][2] * alpha)
        y_pos = flare_y + dy
        if 0 <= y_pos < H:
            for x in range(W):
                orig = img.getpixel((x, y_pos))
                draw.point((x, y_pos), fill=(
                    min(255, orig[0] + r),
                    min(255, orig[1] + g),
                    min(255, orig[2] + b)
                ))
    
    # 4. Scene number (elegant, small)
    font_sm = ImageFont.truetype(FONT_PATH, 22, index=IDX)
    scene_label = f'SCENE {idx+1:02d}'
    draw.text((80, 80), scene_label, fill=tuple(int(c*0.5) for c in pal['text']), font=font_sm)
    
    # 5. Emblem line divider
    div_y = 130
    div_w = 60
    div_x = 80
    draw.line([(div_x, div_y), (div_x + div_w, div_y)], fill=pal['accent'], width=2)
    
    # 6. Main title (bold, cinematic)
    title = scene.get('subtitle', scene.get('visual', ''))
    font_title = ImageFont.truetype(FONT_PATH, 64, index=IDX)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (W - tw) // 2, int(H * 0.30)
    
    # Title shadow (deep)
    draw.text((tx+4, ty+4), title, fill=(0, 0, 0), font=font_title)
    # Title accent line under
    draw.text((tx, ty), title, fill=pal['accent'], font=font_title)
    
    # 7. Subtitle text (narration excerpt)
    narration = scene.get('narration', '')
    if len(narration) > 50:
        narration = narration[:50] + '...'
    font_sub = ImageFont.truetype(FONT_PATH, 30, index=IDX)
    lines = []
    cur = ''
    for ch in narration:
        if len(cur) < 18:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    
    text_y = int(H * 0.50)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_sub)
        lw = bbox[2] - bbox[0]
        lx = (W - lw) // 2
        draw.text((lx, text_y), line, fill=pal['text'], font=font_sub)
        text_y += 48
    
    # 8. Emotion badge
    tag = f'#{emotion}'
    font_tag = ImageFont.truetype(FONT_PATH, 28, index=IDX)
    bbox = draw.textbbox((0, 0), tag, font=font_tag)
    tw = bbox[2] - bbox[0]
    badge_x = (W - tw) // 2
    badge_y = H - 280
    
    # Badge background pill
    pad = 30
    draw.rounded_rectangle(
        [badge_x - pad, badge_y - 10, badge_x + tw + pad, badge_y + 38],
        radius=20, fill=pal['accent'] + (40,), outline=pal['accent'] + (100,), width=1
    )
    draw.text((badge_x, badge_y), tag, fill=pal['accent'], font=font_tag)
    
    # 9. Progress dots (film reel style)
    dot_y = H - 160
    max_vis = min(TOTAL, 7)
    spacing = 44
    start_x = (W - (max_vis - 1) * spacing) // 2
    for d in range(max_vis):
        cx = start_x + d * spacing
        if d == idx:
            # Current: accent color with glow
            for r in range(10, 5, -1):
                alpha = int(40 * (10-r)/5)
                draw.ellipse([cx-r, dot_y-r, cx+r, dot_y+r], fill=pal['accent'] + (alpha,))
            draw.ellipse([cx-4, dot_y-4, cx+4, dot_y+4], fill=pal['accent'])
        else:
            draw.ellipse([cx-4, dot_y-4, cx+4, dot_y+4], fill=tuple(int(c*0.25) for c in pal['text']))
    
    # 10. Duration stamp
    dur = scene['end'] - scene['start']
    dur_text = f'{dur:.0f}s'
    font_dur = ImageFont.truetype(FONT_PATH, 20, index=IDX)
    bbox = draw.textbbox((0, 0), dur_text, font=font_dur)
    dw = bbox[2] - bbox[0]
    draw.text(((W - dw)//2, H - 95), dur_text, fill=tuple(int(c*0.3) for c in pal['text']), font=font_dur)
    
    # 11. Cinematic letterbox bars
    bar_h = 60
    for y in range(bar_h):
        alpha = 1.0 - y / bar_h
        color = (0, 0, 0, int(180 * alpha))
        draw.line([(0, y), (W, y)], fill=(0, 0, 0))
        draw.line([(0, H-1-y), (W, H-1-y)], fill=(0, 0, 0))
    
    # 12. Film grain + vignette
    img = add_film_grain(img, intensity=6)
    img = add_vignette(img, strength=0.35)
    
    img.save(f'output/frames/scene_{idx:02d}.png')
    print(f'  [{idx+1}/{TOTAL}] {title[:25]}')

print(f'\n[2/8] 影视级画面完成: output/frames/ ({TOTAL} 张)')
