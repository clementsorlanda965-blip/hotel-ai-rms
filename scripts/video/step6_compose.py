# =============================================
# step6_compose.py - 视频流水线第6步：视频合成 (moviepy版)
# 将帧图片 + 配音 + BGM + 关键词高亮字幕合成为最终 MP4
# 输出: output/ep1_v2.mp4, outputs/video/daming_ep1.mp4
# =============================================
from moviepy import (
    ImageClip, AudioFileClip, ColorClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips, VideoClip
)
from PIL import Image, ImageDraw, ImageFont
import json, os, platform, math

# Font
FONT_PATH = None
if platform.system() == 'Windows':
    for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
        if os.path.exists(fp):
            FONT_PATH = fp
            break
if not FONT_PATH:
    raise RuntimeError('No CJK font found')

# Load data
with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)
with open('output/subtitles.json', 'r', encoding='utf-8') as f:
    subtitles = json.load(f)

# Audio
voiceover = AudioFileClip('output/voiceover.mp3')
audio_duration = voiceover.duration
script_duration = scenes[-1]['end']
scale = audio_duration / script_duration
print(f'  配音 {audio_duration:.1f}s / 脚本 {script_duration:.0f}s -> 缩放 {scale:.2f}')

W, H = 720, 1280

def make_subtitle_pil(text, keywords, frame_size=(720, 1280)):
    """Render subtitle text with keywords in yellow using PIL"""
    font = ImageFont.truetype(FONT_PATH, 36)
    font_bold = ImageFont.truetype(FONT_PATH, 36)

    # Split text at keyword boundaries
    segments = []
    remaining = text
    while remaining:
        best_pos = len(remaining)
        best_kw = None
        for kw in keywords:
            pos = remaining.find(kw)
            if pos != -1 and pos < best_pos:
                best_pos = pos
                best_kw = kw
        if best_kw is not None and best_pos < len(remaining):
            if best_pos > 0:
                segments.append((remaining[:best_pos], False))
            segments.append((best_kw, True))
            remaining = remaining[best_pos + len(best_kw):]
        else:
            segments.append((remaining, False))
            remaining = ''

    # Measure total width
    total_w = 0
    for seg_text, is_kw in segments:
        bbox = font.getbbox(seg_text)
        total_w += (bbox[2] - bbox[0])

    # Background bar
    bar_w = min(total_w + 60, frame_size[0] - 80)
    padding_x = 20
    bar_h = 60
    bar_x = (frame_size[0] - bar_w) // 2
    bar_y = int(frame_size[1] * 0.78)

    # Create overlay image
    overlay = Image.new('RGBA', frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Draw background bar
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=10,
        fill=(0, 0, 0, 160)
    )

    # Draw highlighted bar at bottom of subtitle for emphasis
    draw.rounded_rectangle(
        [bar_x + 4, bar_y + bar_h - 4, bar_x + bar_w - 4, bar_y + bar_h - 2],
        radius=2,
        fill=(255, 215, 0, 100)
    )

    # Draw text segments
    cur_x = bar_x + padding_x
    text_y = bar_y + (bar_h - 40) // 2
    for seg_text, is_kw in segments:
        bbox = font.getbbox(seg_text)
        seg_w = bbox[2] - bbox[0]
        color = (255, 215, 0, 255) if is_kw else (255, 255, 255, 255)
        draw.text((cur_x, text_y), seg_text, fill=color, font=font)
        cur_x += seg_w

    return overlay

# Build video track with crossfade
print('  构建视频轨道...')
frame_clips = []
for i, scene in enumerate(scenes):
    dur = (scene['end'] - scene['start']) * scale
    fp = f'output/frames/scene_{i:02d}.png'
    if not os.path.exists(fp):
        clip = ColorClip(size=(W, H), color=(14, 14, 18)).with_duration(dur)
    else:
        # Ken Burns subtle zoom
        d = dur
        clip = (ImageClip(fp)
                .with_duration(dur)
                .resized((W, H))
                .resized(lambda t, dur=d: 1.0 + 0.04 * t / dur))
    frame_clips.append(clip)

# Apply crossfade
video = concatenate_videoclips(frame_clips)
print(f'  视频轨道: {len(frame_clips)} 镜头, {video.duration:.1f}s')

# Audio track
bgm_path = None
for p in ['output/bgm.wav', 'output/bgm.mp3']:
    if os.path.exists(p):
        bgm_path = p
        break

if bgm_path:
    bgm = AudioFileClip(bgm_path)
    if bgm.duration < video.duration:
        from moviepy import concatenate_audioclips
        n_loops = int(video.duration / bgm.duration) + 2
        bgm = concatenate_audioclips([bgm] * n_loops)
    bgm = bgm.with_duration(video.duration).with_volume_scaled(0.20)
else:
    bgm = voiceover.with_volume_scaled(0)

audio_final = CompositeAudioClip([voiceover, bgm])
print(f'  音频: 旁白 + BGM')

# Subtitle track with yellow keywords
print('  渲染字幕 (关键词标黄)...')
subtitle_clips = []
overlay_dir = 'output/sub_overlays'
os.makedirs(overlay_dir, exist_ok=True)

for idx, sub in enumerate(subtitles):
    dur = sub['end'] - sub['start']
    if dur < 0.3:
        continue

    img = make_subtitle_pil(sub['text'], sub.get('keywords', []), (W, H))
    overlay_path = os.path.join(overlay_dir, f'sub_{idx:04d}.png')
    img.save(overlay_path)

    clip = (ImageClip(overlay_path)
            .with_duration(dur)
            .with_position(('center', 'center'))
            .with_start(sub['start'])
            .with_end(sub['end']))
    subtitle_clips.append(clip)

print(f'  字幕: {len(subtitle_clips)} 条 (含关键词标黄)')

# Composite
final = CompositeVideoClip([video] + subtitle_clips, size=(W, H))
final = final.with_audio(audio_final)

# Encode
print('  编码中 (24fps, CRF 18)...')
output_path = 'output/ep1_v2.mp4'
final.write_videofile(
    output_path,
    codec='libx264',
    audio_codec='aac',
    preset='medium',
    fps=24,
    bitrate='3000k',
    threads=4
)

# Copy to outputs
import shutil
final_output = 'outputs/video/daming_ep1.mp4'
os.makedirs('outputs/video', exist_ok=True)
shutil.copy2(output_path, final_output)

size_mb = os.path.getsize(final_output) / (1024 * 1024)
print(f'\n[6/6] 完成!')
print(f'  {final_output}')
print(f'  时长: {video.duration:.1f}s | 分辨率: {W}x{H} | 帧率: 24fps')
print(f'  大小: {size_mb:.1f} MB')

voiceover.close()
final.close()
for c in frame_clips:
    c.close()
