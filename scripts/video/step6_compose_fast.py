# =============================================
# step6_compose_fast.py - 视频流水线第6步：视频合成 (FFmpeg版)
# 使用 FFmpeg 进行 Ken Burns 效果 + ASS 字幕 + 音频混合
# 比 moviepy 版更快，适合最终生产版本
# 输出: outputs/video/daming_ep1.mp4
# =============================================
import json, os, subprocess

# FFmpeg 可执行文件路径
FFMPEG = r'C:\Users\周通\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
os.chdir(r'E:\工作AI')

with open('output/script.json', 'r', encoding='utf-8') as f:
    scenes = json.load(f)

# Get audio duration
r = subprocess.run([FFMPEG, '-i', 'output/voiceover.mp3'], capture_output=True, text=True)
for line in r.stderr.split('\n'):
    if 'Duration' in line:
        audio_dur = line.split('Duration: ')[1].split(',')[0]
        h, m, s = audio_dur.split(':')
        audio_secs = float(h)*3600 + float(m)*60 + float(s)
        break

script_total = scenes[-1]['end']
scale_factor = audio_secs / script_total
print(f'Audio: {audio_secs:.1f}s  Script: {script_total:.0f}s  Scale: {scale_factor:.2f}x')

W, H = 720, 1280
os.makedirs('output/segments', exist_ok=True)

# ===== STEP 1: Generate segments with Ken Burns zoom =====
print('[1/3] Generating video segments (Ken Burns zoom)...')
concat_lines = []
for i, s in enumerate(scenes):
    fp = f'output/frames/scene_{i:02d}.png'
    dur = (s['end'] - s['start']) * scale_factor
    out = f'output/segments/seg_{i:02d}.mp4'
    total_frames = max(1, int(dur * 24))
    cmd = [
        FFMPEG, '-y', '-loop', '1', '-i', fp,
        '-vf', f'zoompan=z=min(1.04\\,1+0.04*on/{total_frames}):d={total_frames}:s={W}x{H}:fps=24',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '20',
        '-t', f'{dur:.2f}', '-pix_fmt', 'yuv420p', '-an', out
    ]
    subprocess.run(cmd, capture_output=True)
    concat_lines.append(f"file '{os.path.abspath(out).replace(chr(92),'/')}'")
    print(f'  [{i+1}/{len(scenes)}] {dur:.1f}s')

# ===== STEP 2: Concat =====
print('[2/3] Concatenating...')
concat_file = 'output/concat_video.txt'
with open(concat_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(concat_lines))

video_no_audio = 'output/video_no_audio.mp4'
subprocess.run([
    FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
    '-c', 'copy', video_no_audio
], capture_output=True)

# ===== STEP 3: Final compose with ASS subs + audio =====
print('[3/3] Composing with ASS subtitles + audio...')

bgm_path = 'output/bgm.wav'
out_path = 'outputs/video/daming_ep1.mp4'
os.makedirs('outputs/video', exist_ok=True)

final_cmd = [
    FFMPEG, '-y',
    '-i', video_no_audio,
    '-i', 'output/voiceover.mp3',
    '-i', bgm_path,
    '-filter_complex',
    '[1:a]adelay=0|0[a1];[2:a]adelay=0|0,volume=0.20[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[amix]',
    '-map', '0:v',
    '-map', '[amix]',
    '-vf', 'ass=f=output/subtitles.ass:original_size=720x1280',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-c:a', 'aac', '-b:a', '128k',
    '-r', '24', '-pix_fmt', 'yuv420p',
    '-shortest',
    out_path
]

print('  Encoding (24fps, CRF 18)...')
result = subprocess.run(final_cmd, capture_output=True, text=True)
if result.returncode == 0:
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    dur_secs = audio_secs
    print(f'\n完成! {out_path}')
    print(f'  时长: {dur_secs:.1f}s | 分辨率: {W}x{H} | 帧率: 24fps')
    print(f'  大小: {size_mb:.1f} MB')
else:
    print('FAILED')
    print(result.stderr[-1000:])
