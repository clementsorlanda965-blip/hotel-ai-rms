# =============================================
# compose_fixed.py - 修复版视频合成工具 (moviepy)
# 强制音频时长锁定，解决画面和配音不同步问题
# =============================================
from moviepy import (
    ImageClip, AudioFileClip, TextClip, ColorClip,
    CompositeVideoClip, CompositeAudioClip, concatenate_videoclips
)
import json, os, platform, math

# Font
FONT_PATH = None
if platform.system() == 'Windows':
    for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
        if os.path.exists(fp):
            FONT_PATH = fp
            break
if not FONT_PATH:
    raise RuntimeError('No CJK font')

# Load data
with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)
with open('output/subtitles.json', 'r', encoding='utf-8') as f:
    subtitles = json.load(f)

W, H = 720, 1280

# === STEP 1: Get audio duration (VIDEO MUST match this) ===
voiceover = AudioFileClip('output/voiceover.mp3')
AUDIO_DURATION = voiceover.duration
script_dur = scenes[-1]['end']
scale = AUDIO_DURATION / script_dur
print(f'音频={AUDIO_DURATION:.1f}s | 脚本={script_dur:.0f}s | 缩放={scale:.3f}')

# === STEP 2: Build frame track (strictly = AUDIO_DURATION) ===
frame_clips = []
elapsed = 0.0

for i, scene in enumerate(scenes):
    # Duration of this scene AFTER scaling
    dur = (scene['end'] - scene['start']) * scale
    # Clamp to ensure we never exceed audio
    if elapsed + dur > AUDIO_DURATION:
        dur = max(0.1, AUDIO_DURATION - elapsed)
    
    fp = f'output/frames/scene_{i:02d}.png'
    if elapsed >= AUDIO_DURATION:
        break  # Don't add scenes past audio duration
    
    if os.path.exists(fp):
        d = dur
        clip = (ImageClip(fp)
                .with_duration(dur)
                .resized((W, H))
                .resized(lambda t, d2=d: 1.0 + 0.03 * t / d2))
    else:
        clip = ColorClip(size=(W, H), color=(14, 14, 18)).with_duration(dur)
    
    elapsed += dur
    frame_clips.append(clip)

video = concatenate_videoclips(frame_clips)
# FORCE exact duration
video = video.with_duration(AUDIO_DURATION)
print(f'画面: {len(frame_clips)}镜头, {video.duration:.1f}s (必须={AUDIO_DURATION:.1f}s)')

# === STEP 3: Audio (BGM trimmed to match) ===
bgm_path = None
for p in ['output/bgm.wav', 'output/bgm.mp3']:
    if os.path.exists(p):
        bgm_path = p
        break

# Create silent BGM if not found (avoids duration stretching)
if bgm_path:
    bgm = AudioFileClip(bgm_path).with_duration(AUDIO_DURATION).with_volume_scaled(0.15)
else:
    # Silent audio of exact length
    from moviepy import AudioClip
    bgm = voiceover.with_volume_scaled(0).with_duration(AUDIO_DURATION)

# Composite audio — ensure voiceover + trimmed BGM
audio = CompositeAudioClip([
    voiceover,
    bgm.with_duration(AUDIO_DURATION)
])

print(f'音频: 旁白{AUDIO_DURATION:.1f}s + BGM')

# === STEP 4: Subtitles (only within audio duration) ===
subtitle_clips = []
for sub in subtitles:
    if sub['start'] >= AUDIO_DURATION:
        break  # Past audio end, skip
    end = min(sub['end'], AUDIO_DURATION)
    dur = end - sub['start']
    if dur < 0.3:
        continue

    bar = (ColorClip(size=(int(W * 0.88), 56), color=(0, 0, 0))
           .with_opacity(0.35)
           .with_position(('center', int(H * 0.77)))
           .with_start(sub['start'])
           .with_end(end))
    subtitle_clips.append(bar)

    txt = (TextClip(text=sub['text'], font_size=34, color='white',
                    stroke_color='black', stroke_width=2.5,
                    font=FONT_PATH, method='label')
           .with_position(('center', int(H * 0.79)))
           .with_start(sub['start'])
           .with_end(end))
    subtitle_clips.append(txt)

print(f'字幕: {len(subtitle_clips)//2}条')

# === STEP 5: Final composite (duration locked to audio) ===
final = CompositeVideoClip([video] + subtitle_clips, size=(W, H))
final = final.with_duration(AUDIO_DURATION)  # DOUBLE lock
final = final.with_audio(audio)

final.write_videofile(
    'output/final.mp4',
    codec='libx264',
    audio_codec='aac',
    preset='ultrafast',
    fps=20,
    bitrate='1500k',
    threads=4
)

print(f'\n[6/8] 完成: output/final.mp4 ({AUDIO_DURATION:.1f}s)')

voiceover.close()
final.close()
for c in frame_clips:
    c.close()
