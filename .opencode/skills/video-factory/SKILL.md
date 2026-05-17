---
name: video-factory
description: 短视频全自动生成——选题、脚本、AI配图、配音、字幕、BGM、合成。一句主题出片。支持影视解说、知识科普、商品种草等类型。输入"做视频""生成视频""短视频"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Grep Glob WebFetch
metadata:
  audience: short-video-creator
  language: zh-CN
---

## 强制规则
**所有文字输出必须是中文。** 脚本、字幕、旁白——全部中文。

输入主题 → 输出完整视频。流程：选题→脚本→AI配图→配音→字幕→BGM→合成。

## 管线

> **🔗 全自动路由**：说"做视频""一键出片"会自动触发 **video-producer Agent**，它串联 content-writer（脚本）→ image-generator（配图/封面）→ audio-tts（配音）→ speech-recognition（字幕）→ 本 skill（合成）。本 skill 也可独立调用各环节。

```
选题推荐(3选1) → [确认]选题方向 → LLM脚本(7-12镜头) → [确认]脚本内容 → AI生图(SD-Turbo/CPU文字卡) → [确认]配图效果 → TTS配音 → 字幕(智能断句) → BGM(情绪匹配) → [确认]开始合成 → 合成(强制对齐时长)
```

### 检查点说明

每个 `[确认]` 标记处暂停并询问用户：

| 检查点 | 触发时机 | 确认内容 | 跳过条件 |
|--------|---------|---------|---------|
| 选题方向 | 生成3个角度后 | "推荐角度A/B/C，请选择或输入自定义主题" | 用户直接指定选题 |
| 脚本内容 | 生成脚本后 | 展示脚本摘要(镜头数/时长/情绪)，确认是否调整 | 用户提供现成脚本 |
| 配图效果 | 生成关键帧后 | 展示首帧缩略图，确认风格是否满意 | 使用文字卡片方案 |
| 开始合成 | 所有资产就绪 | 汇总配音时长/画面数/BGM风格，用户确认后合成 | 用户在开始时跳过确认 |

## 流程速查

| 环节 | 输入 | 工具/代码 | 输出 | 检查点 |
|------|------|----------|------|-------|
| 选题+脚本 | 用户主题 → 3角度 → 用户选择 | LLM脚本生成 | `output/script.json` | [确认]选题方向+脚本内容 |
| AI画面 | `script.json` | SD-Turbo / PIL文字卡 | `output/frames/scene_XX.png` | [确认]配图效果 |
| 配音+字幕 | `script.json`旁白文本 | edge-tts / gTTS | `output/voiceover.mp3` + `output/subtitles.json` | — |
| SRT字幕 | `subtitles.json` | 格式转换 | `output/subtitles.srt` | — |
| BGM | `script.json`情绪字段 | 正弦波合成 | `output/bgm.wav` | — |
| 合成 | 画面+配音+字幕+BGM | moviepy | `output/final.mp4` | [确认]开始合成 |

## 环节一：选题 + 脚本

用户给主题后，推荐3个爆款角度。用户选一个后，生成 `output/script.json`：

```python
import json, os
os.makedirs('output', exist_ok=True)

# Agent根据选题动态生成
SCRIPT = [
    {"id":0,"start":0.0,"end":3.0,
     "visual":"英文画面描述","narration":"中文旁白",
     "subtitle":"≤8字字幕","emotion":"hook",
     "camera":{"lens":"35mm","aperture":"f/4","style":"digital"}},
    # ... 7-12个镜头
]
with open('output/script.json','w',encoding='utf-8') as f:
    json.dump(SCRIPT, f, ensure_ascii=False, indent=2)
```

## 环节二：AI画面

> **🔗 可选替代**：本环节的 AI 生图可替换为 **image-generator** 技能（ComfyUI 主力 + PIL 降级），支持更丰富的模型选择和批量处理。画面输出为 `outputs/frames/scene_XX.png`，格式兼容后续合成。

引擎优先级：GPU可用→SD-Turbo。不可用→CPU文字卡片。

```python
from diffusers import AutoPipelineForText2Image
from PIL import Image
import torch, json, os

with open('output/script.json','r',encoding='utf-8') as f:
    scenes = json.load(f)
os.makedirs('output/frames', exist_ok=True)

use_gpu = torch.cuda.is_available()
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sd-turbo",
    torch_dtype=torch.float16 if use_gpu else torch.float32,
    variant="fp16"
)
if use_gpu: pipe = pipe.to("cuda")

# 摄影机参数增强
CAM = {"8mm":"ultra wide 8mm", "14mm":"wide 14mm", "24mm":"24mm cinematic",
       "35mm":"35mm natural", "50mm":"50mm portrait", "85mm":"85mm tight"}
APT = {"f/1.4":"f/1.4 shallow bokeh", "f/4":"f/4 balanced", "f/11":"f/11 deep focus"}
FILM = {"70mm_film":"70mm IMAX epic","16mm_film":"16mm vintage grain",
        "anamorphic":"anamorphic flares","digital":"clean digital"}

for i, s in enumerate(scenes):
    cam = s.get('camera',{})
    prompt = f"{s['visual']}, {CAM.get(cam.get('lens','35mm'),'')}, {APT.get(cam.get('aperture','f/4'),'')}, {FILM.get(cam.get('style','digital'),'')}, 4K photorealistic"
    img = pipe(prompt=prompt, width=512, height=912, num_inference_steps=2, guidance_scale=0.0).images[0]
    img.resize((1080,1920), Image.LANCZOS).save(f'output/frames/scene_{i:02d}.png')
    print(f'  [{i+1}/{len(scenes)}] {s["subtitle"]}')
```

**CPU降级方案：**
```python
from PIL import Image, ImageDraw, ImageFont
import platform
FONT = None
if platform.system()=='Windows':
    for f in ['C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf']:
        if os.path.exists(f): FONT=f; break
if not FONT: raise RuntimeError('无中文字体')

for i, s in enumerate(scenes):
    img = Image.new('RGB',(1080,1920),(14,14,18))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 68)
    bbox = d.textbbox((0,0), s['subtitle'], font=font)
    d.text(((1080-bbox[2]+bbox[0])//2, 800), s['subtitle'], fill=(255,255,255), font=font)
    font2 = ImageFont.truetype(FONT, 34)
    bbox2 = d.textbbox((0,0), s['narration'][:40], font=font2)
    d.text(((1080-bbox2[2]+bbox2[0])//2, 1000), s['narration'][:40], fill=(170,175,200), font=font2)
    img.save(f'output/frames/scene_{i:02d}.png')
```

## 环节三：配音 + 字幕

> **🔗 可选替代**：本环节的 TTS 配音可替换为 **audio-tts** 技能（双引擎 edge-tts/ChatTTS，自动择优）。音频输出为 `outputs/audio/voiceover.mp3`，格式兼容本流程后续环节。

```python
import edge_tts, asyncio, json, re
from moviepy import AudioFileClip

with open('output/script.json','r',encoding='utf-8') as f:
    scenes = json.load(f)
text = '\n'.join(s['narration'] for s in scenes)

async def tts():
    c = edge_tts.Communicate(text=text, voice='zh-CN-YunxiNeural', rate='+10%', pitch='-2Hz')
    await c.save('output/voiceover.mp3')
asyncio.run(tts())

audio = AudioFileClip('output/voiceover.mp3')
dur = audio.duration; audio.close()

# 智能断句
def split(text):
    parts = re.split(r'(?<=[。！？])', text)
    result = []
    for p in parts:
        p = p.strip()
        if not p: continue
        if len(p) <= 12: result.append(p)
        else:
            sub = re.split(r'(?<=[，、；：])', p)
            cur = ''
            for s in sub:
                if len(cur)+len(s) <= 12: cur += s
                else:
                    if cur: result.append(cur.strip())
                    cur = s
            if cur: result.append(cur.strip())
    return result

subs = []
total = sum(len(s['narration']) for s in scenes)
t = 0.0
for s in scenes:
    sd = (len(s['narration'])/total)*dur
    segs = split(s['narration'])
    seg_d = sd/len(segs) if segs else 0
    for j, seg in enumerate(segs):
        ss = t+j*seg_d
        se = ss+max(seg_d,0.4)
        subs.append({'text':seg,'start':round(ss,2),'end':round(min(se,t+sd),2)})
    t += sd
if subs: subs[-1]['end'] = round(dur,2)

with open('output/subtitles.json','w',encoding='utf-8') as f:
    json.dump(subs, f, ensure_ascii=False, indent=2)
print(f'配音:{dur:.1f}s 字幕:{len(subs)}条 语速:{total/dur:.1f}字/秒')
```

## 环节四：SRT字幕（可选）

> **🔗 可选替代**：本环节可替换为 **speech-recognition** 技能（FunASR 高精度语音识别），直接从配音音频生成带字级时间轴的 SRT 字幕。也适用于为已有视频补字幕的场景。

```python
import json
with open('output/subtitles.json','r',encoding='utf-8') as f:
    subs = json.load(f)
def st(s):
    h,m = int(s//3600),int((s%3600)//60)
    sec,ms = int(s%60),int((s%1)*1000)
    return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'
with open('output/subtitles.srt','w',encoding='utf-8') as f:
    for i,sub in enumerate(subs,1):
        f.write(f'{i}\n{st(sub["start"])} --> {st(sub["end"])}\n{sub["text"]}\n\n')
```

## 环节五：BGM

```python
import json, numpy as np, wave, os
with open('output/script.json','r',encoding='utf-8') as f:
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
with wave.open('output/bgm.wav','w') as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
    wf.writeframes((audio*32767).astype(np.int16).tobytes())
print(f'BGM: bpm={bpm}')
```

## 环节六：合成

```python
from moviepy import *
import json, os, platform

FONT = None
if platform.system()=='Windows':
    for f in ['C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf']:
        if os.path.exists(f): FONT=f; break

with open('output/script.json','r',encoding='utf-8') as f:
    scenes = json.load(f)
with open('output/subtitles.json','r',encoding='utf-8') as f:
    subs = json.load(f)

W,H = 720,1280
voice = AudioFileClip('output/voiceover.mp3')
AUDIO_DUR = voice.duration
scale = AUDIO_DUR / scenes[-1]['end']

clips = []; elapsed = 0.0
for i,s in enumerate(scenes):
    dur = (s['end']-s['start'])*scale
    if elapsed+dur > AUDIO_DUR: dur = max(0.1, AUDIO_DUR-elapsed)
    fp = f'output/frames/scene_{i:02d}.png'
    if elapsed >= AUDIO_DUR: break
    if os.path.exists(fp):
        d = dur
        clip = ImageClip(fp).with_duration(dur).resized((W,H)).resized(lambda t,d2=d:1.0+0.03*t/d2)
    else:
        clip = ColorClip(size=(W,H),color=(14,14,18)).with_duration(dur)
    elapsed += dur; clips.append(clip)

video = concatenate_videoclips(clips).with_duration(AUDIO_DUR)

bgm_path = None
for p in ['output/bgm.wav','output/bgm.mp3']:
    if os.path.exists(p): bgm_path=p; break
bgm = AudioFileClip(bgm_path).with_duration(AUDIO_DUR).with_volume_scaled(0.15) if bgm_path else voice.with_volume_scaled(0)
audio = CompositeAudioClip([voice, bgm])

sub_clips = []
for sub in subs:
    if sub['start'] >= AUDIO_DUR: break
    end = min(sub['end'], AUDIO_DUR)
    if end-sub['start'] < 0.3: continue
    bar = ColorClip(size=(int(W*0.88),56),color=(0,0,0)).with_opacity(0.35).with_position(('center',int(H*0.77))).with_start(sub['start']).with_end(end)
    txt = TextClip(text=sub['text'],font_size=34,color='white',stroke_color='black',stroke_width=2.5,font=FONT,method='label').with_position(('center',int(H*0.79))).with_start(sub['start']).with_end(end)
    sub_clips.extend([bar,txt])

final = CompositeVideoClip([video]+sub_clips, size=(W,H)).with_duration(AUDIO_DUR).with_audio(audio)
final.write_videofile('output/final.mp4', codec='libx264', audio_codec='aac', preset='ultrafast', fps=20, bitrate='1500k', threads=4)
print(f'完成 output/final.mp4 ({AUDIO_DUR:.1f}s)')
voice.close(); final.close()
for c in clips: c.close()
```

## 注意事项

- 视频时长强制等于配音时长，不留空白
- 字幕按标点智能断句，不用机械切割
- GPU不可用时自动降级为文字卡片
- 所有环节通过 output/ 目录下的JSON文件通信

## 异常处理

| 异常场景 | 表现 | 处理方式 |
|---------|------|---------|
| diffusers下载失败 | `OSError: Can't load tokenizer` | 捕获异常 → 自动降级为CPU文字卡片，提示"SD模型下载失败，已切换文字卡片模式" |
| edge-tts网络不可用 | `ConnectionError: timed out` | 捕获异常 → 使用 `gTTS` 备用引擎（`pip install gtts`），提示"网络TTS不可用，已切换gTTS离线模式" |
| FFmpeg未安装 | `FileNotFoundError: ffmpeg` | 提示"FFmpeg未安装，请执行：`winget install ffmpeg` 或 `choco install ffmpeg`" |
| 磁盘空间不足 | `OSError: No space left` | 提示清理output目录，建议保留>500MB空闲空间 |
| script.json缺失 | `FileNotFoundError` | 自动生成含3个占位镜头的默认脚本，提示"脚本文件未找到，已自动创建默认脚本" |
| moviepy导入失败 | `ModuleNotFoundError: moviepy` | 提示"请执行：`pip install moviepy[all]`" |
| 配音文件生成失败 | 音频为0字节或不存在 | 跳过配音环节，仅输出画面+字幕视频，提示"配音生成失败，已切换静音模式" |
