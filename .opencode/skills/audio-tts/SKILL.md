---
name: audio-tts
description: >-
  TTS语音合成配音——双引擎驱动：edge-tts（微软免费云端，40+中文音色，零延迟）和 ChatTTS（本地高质量生成式语音，情感丰富）。
  自动分段、多音色可选、语速/音调可调。输出MP3到 outputs/audio/。
  输入"配音""TTS""语音合成""文本转语音""朗读""文字转音频"时触发。
  所有文字输出为中文。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write
metadata:
  language: zh-CN
  audience: short-video-creator
---

## 强制规则
所有文字输出必须是中文。配音文本必须是中文。输出音频文件到 `outputs/audio/` 目录。

## 做什么
将中文文本转为自然语音，支持影视解说、旁白配音、文章朗读等场景。双引擎自动适配：快速场景用 edge-tts，高质量场景用 ChatTTS。

## 检查点

### Step 0: 需求确认
向用户确认：文本长度、期望风格（沉稳/活泼/大气/情感）、是否需要分镜多段配音。用户确认后再进入引擎选择。

### Step 2: 音色确认
选好音色后展示给用户确认，提供 2-3 个候选供挑选。

### Step 3: 输出前确认
生成前展示：引擎、音色、语速、音调、输出文件路径，用户确认后再执行生成。

## 引擎选择

| 场景 | 引擎 | 特点 | 调用方式 |
|------|------|------|----------|
| 短视频配音、快速预览 | **edge-tts** | 免费、云端、40+中文音色、无需GPU | `import edge_tts` |
| 电影级旁白、情感表达 | **ChatTTS** | 本地生成、情感细腻、需GPU | `import ChatTTS` |

### edge-tts 推荐音色

| 音色ID | 风格 | 适用场景 |
|--------|------|----------|
| `zh-CN-YunxiNeural` | 男声、沉稳 | 历史解说、纪录片 |
| `zh-CN-YunyangNeural` | 男声、新闻 | 资讯播报 |
| `zh-CN-XiaoxiaoNeural` | 女声、温柔 | 情感故事 |
| `zh-CN-XiaoyiNeural` | 女声、活泼 | 种草带货 |
| `zh-CN-YunjianNeural` | 男声、大气 | 企业宣传 |

## 工作流

### 1. 文本预处理
```
输入文本 → 按标点分段（。！？为界，12字内优先）→ 生成配音序列
```

### 2. 配音参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| rate | `+10%` | 语速稍微加快，适合短视频节奏 |
| pitch | `-2Hz` | 音调微降，更沉稳 |
| voice | 按场景选 | 见上表 |

### 3. 输出规范
- 格式：MP3（edge-tts）/ WAV（ChatTTS）
- 路径：`outputs/audio/voiceover.mp3`
- 采样率：16000Hz（edge-tts）/ 24000Hz（ChatTTS）
- 文件名：有多个配音时按镜头编号命名 `outputs/audio/scene_01.mp3`

### 4. 与 video-factory 集成
直接替代环节三的配音部分。输出文件名与 `script.json` 中的镜头编号对应：
```
outputs/script.json  →  读取旁白文字
outputs/audio/voiceover.mp3  →  输出配音文件
outputs/subtitles.json  →  同时输出字幕时间轴（配合 speech-recognition 技能）
```

## 代码骨架

### edge-tts 快速调用
```python
import asyncio, edge_tts

async def tts_edge(text, output_path, voice="zh-CN-YunxiNeural"):
    comm = edge_tts.Communicate(text, voice, rate="+10%", pitch="-2Hz")
    await comm.save(output_path)

asyncio.run(tts_edge("这段文字需要配音", "outputs/audio/voiceover.mp3"))
```

### ChatTTS 本地生成
```python
import torch, ChatTTS
from ChatTTS import Chat

chat = Chat()
chat.load(source="local")
wavs = chat.infer(["这段文字需要配音"], use_decoder=True)
# wavs[0] 是 numpy array，用 soundfile 保存
import soundfile as sf
sf.write("outputs/audio/voiceover.wav", wavs[0], 24000)
```

## 降级策略
ChatTTS 不可用时（无GPU/模型未下载）自动回退到 edge-tts，保证配音流程不中断。

## 注意事项
1. edge-tts 需要网络连接，首次使用自动选择可用微软节点
2. ChatTTS 首次需下载模型（~2GB），存放于本地 models 目录
3. 长文本（>500字）自动分段，逐段生成后拼接
4. 配音时长自动计算，写入 script.json 的 start/end 字段
