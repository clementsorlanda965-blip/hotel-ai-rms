---
name: video-factory
description: 短视频合成引擎——BGM生成 + 视频合成。接收各子环节产出的中间文件，自动对齐时长、混合音轨、输出成品MP4。输入"合成视频""做视频""合成""最后合成""出片"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Grep Glob WebFetch
metadata:
  audience: short-video-creator
  language: zh-CN
---

## 强制规则
**所有文字输出必须是中文。** 脚本、字幕、旁白——全部中文。

输入各子环节产出 → 输出成品视频。本 skill 负责**BGM生成 + 最终合成**，不负责脚本/配图/配音/字幕生成——这些由对应子技能完成。

## 管线编排

本技能是整个视频管线的最后一段。完整管线调用顺序：

```
用户主题
  → content-writer（脚本） → outputs/script.json
  → [可选] humanizer-zh（去AI味） → 润色后 script.json
  → image-generator（配图） → outputs/frames/scene_XX.png
  → audio-tts（配音） → outputs/audio/voiceover.mp3
  → speech-recognition（字幕） → outputs/subtitles/subtitles.srt
  → ★ video-factory（BGM + 合成） → outputs/video/final.mp4
```

### 输入文件约定

| 文件 | 来源技能 | 路径 | 必需 |
|------|---------|------|------|
| 脚本JSON | content-writer | `outputs/script.json` | 是 |
| 镜头配图 | image-generator | `outputs/frames/scene_XX.png` | 推荐（无则黑底） |
| 配音音频 | audio-tts | `outputs/audio/voiceover.mp3` | 是 |
| 字幕文件 | speech-recognition | `outputs/subtitles/subtitles.srt` | 推荐（无则自动生成） |
| BGM | 本环节生成 | `outputs/bgm.wav` | 可选（无则纯配音） |

### script.json 格式（必需字段）

```json
[
  {
    "id": 0,
    "start": 0.0,
    "end": 3.0,
    "visual": "画面描述",
    "narration": "旁白文本",
    "subtitle": "字幕≤8字",
    "emotion": "hook"
  }
]
```

使用标准7-12镜/分钟结构，`emotion` 字段用于BGM情绪匹配。

## 环节一：BGM生成

根据脚本情绪字段生成匹配背景音乐（纯正弦波合成，无需模型文件）：

```python
import json, numpy as np, wave, os
with open('outputs/script.json','r',encoding='utf-8') as f:
    scenes = json.load(f)
bpm_map = {'hook':60,'共鸣':75,'冲突':110,'亢奋':120,'转折':90,'顿悟':80,'激励':100,'行动':105}
bpm = bpm_map.get(scenes[0].get('emotion','hook'),95)
total = scenes[-1]['end']+2
sr = 44100
samples = int(total*sr)
audio = np.zeros(samples, dtype=np.float64)
bi = 60.0/bpm
for beat in np.arange(0,total,bi*2):
    start = int(beat*sr)
    end = min(start+int(0.15*sr), samples)
    bt = np.arange(end-start,dtype=np.float64)/sr
    audio[start:end] += np.sin(2*np.pi*55*bt)*np.exp(-bt*25)*0.5
noise = np.random.randn(samples).astype(np.float64)*0.02
audio = (audio+noise)/np.max(np.abs(audio+noise))*0.6
with wave.open('outputs/bgm.wav','w') as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
    wf.writeframes((audio*32767).astype(np.int16).tobytes())
print(f'BGM: bpm={bpm}')
```

BGM生成后，自动归入合成环节使用。如果已有BGM文件则跳过。

## 环节二：视频合成

读取各子环节的中间文件，合成最终MP4：

```python
from moviepy import *
import json, os, platform

FONT = None
if platform.system()=='Windows':
    for f in ['C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf']:
        if os.path.exists(f): FONT=f; break

with open('outputs/script.json','r',encoding='utf-8') as f:
    scenes = json.load(f)

# 读取字幕（优先SRT格式，降级JSON）
subs_path = 'outputs/subtitles/subtitles.srt'
subs_json_path = 'outputs/subtitles.json'
subs = []
if os.path.exists(subs_path):
    import re
    with open(subs_path,'r',encoding='utf-8') as f:
        raw = f.read()
    for block in raw.strip().split('\n\n'):
        lines = block.split('\n')
        if len(lines) >= 3:
            time_match = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', lines[1])
            if time_match:
                def ts(s):
                    h,m,rest = s.split(':')
                    sec,ms = rest.split(',')
                    return int(h)*3600+int(m)*60+int(sec)+int(ms)/1000
                subs.append({'text':lines[2],'start':ts(time_match.group(1)),'end':ts(time_match.group(2))})
elif os.path.exists(subs_json_path):
    with open(subs_json_path,'r',encoding='utf-8') as f:
        subs = json.load(f)

W,H = 720,1280
voice_path = 'outputs/audio/voiceover.mp3'
if not os.path.exists(voice_path):
    voice_path = 'outputs/voiceover.mp3'  # 兼容旧路径
voice = AudioFileClip(voice_path)
AUDIO_DUR = voice.duration

# 计算画面缩放比例（配音时长 vs 脚本时长）
script_end = scenes[-1]['end'] if scenes else AUDIO_DUR
scale = AUDIO_DUR / script_end if script_end > 0 else 1.0

clips = []; elapsed = 0.0
for i,s in enumerate(scenes):
    dur = (s['end']-s['start'])*scale
    if elapsed+dur > AUDIO_DUR: dur = max(0.1, AUDIO_DUR-elapsed)
    fp = f'outputs/frames/scene_{i:02d}.png'
    # 兼容旧路径
    if not os.path.exists(fp):
        fp2 = f'output/frames/scene_{i:02d}.png'
        if os.path.exists(fp2): fp = fp2
    if elapsed >= AUDIO_DUR: break
    if os.path.exists(fp):
        clip = ImageClip(fp).with_duration(dur).resized((W,H)).resized(lambda t,d2=dur:1.0+0.03*t/d2)
    else:
        clip = ColorClip(size=(W,H),color=(14,14,18)).with_duration(dur)
    elapsed += dur; clips.append(clip)

video = concatenate_videoclips(clips).with_duration(AUDIO_DUR)

# BGM
bgm_path = 'outputs/bgm.wav'
bgm = AudioFileClip(bgm_path).with_duration(AUDIO_DUR).with_volume_scaled(0.15) if os.path.exists(bgm_path) else voice.with_volume_scaled(0)
audio = CompositeAudioClip([voice, bgm])

# 字幕叠加
sub_clips = []
for sub in subs:
    if sub['start'] >= AUDIO_DUR: break
    end = min(sub['end'], AUDIO_DUR)
    if end-sub['start'] < 0.3: continue
    bar = ColorClip(size=(int(W*0.88),56),color=(0,0,0)).with_opacity(0.35).with_position(('center',int(H*0.77))).with_start(sub['start']).with_end(end)
    txt = TextClip(text=sub['text'],font_size=34,color='white',stroke_color='black',stroke_width=2.5,font=FONT,method='label').with_position(('center',int(H*0.79))).with_start(sub['start']).with_end(end)
    sub_clips.extend([bar,txt])

os.makedirs('outputs/video', exist_ok=True)
final = CompositeVideoClip([video]+sub_clips, size=(W,H)).with_duration(AUDIO_DUR).with_audio(audio)
final.write_videofile('outputs/video/final.mp4', codec='libx264', audio_codec='aac', preset='ultrafast', fps=20, bitrate='1500k', threads=4)
print(f'完成 outputs/video/final.mp4 ({AUDIO_DUR:.1f}s)')
voice.close(); final.close()
for c in clips: c.close()
```

## 注意事项

- 视频时长强制等于配音时长，不留空白
- 字幕优先从SRT读取，降级到JSON
- GPU不可用时由 image-generator 处理，本环节不直接调用模型
- 所有环节通过 outputs/ 目录下的中间文件通信
- **本 skill 不负责脚本/配图/配音生成**——调用前确保各子环节已产出对应文件

## 异常处理

| 异常场景 | 表现 | 处理方式 |
|---------|------|---------|
| script.json 缺失 | `FileNotFoundError` | 自动生成含3个占位镜头的默认脚本，提示"脚本文件未找到，已自动创建默认脚本" |
| 配音文件不存在 | 无配音 | 跳过配音环节，仅输出画面+静音视频，提示"配音文件不存在，已切换静音模式" |
| FFmpeg未安装 | `FileNotFoundError: ffmpeg` | 提示"FFmpeg未安装，请执行：`winget install ffmpeg` 或 `choco install ffmpeg`" |
| 磁盘空间不足 | `OSError: No space left` | 提示清理outputs目录，建议保留>500MB空闲空间 |
| moviepy导入失败 | `ModuleNotFoundError: moviepy` | 提示"请执行：`pip install moviepy[all]`" |
| BGM文件不存在 | 无背景音乐 | 自动生成默认BGM（使用场景默认BPM=95），提示"已自动生成BGM" |
| 无配图文件 | 所有帧文件缺失 | 使用纯黑底+字幕模式，提示"配图文件未找到，已切换纯文字模式" |

## 与 Agents 集成

```
video-producer → 单视频生产管线（完整串联各子技能）
content-studio → 批量视频生产（矩阵内容）
```

两个 Agent 均调用本 skill 作为最后合成环节。本 skill 不直接对接用户选题，由上层 Agent 或 content-writer 负责。
