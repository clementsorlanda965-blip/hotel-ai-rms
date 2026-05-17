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

| 步骤 | 输入 | 工具/操作 | 输出 |
|------|------|-----------|------|
| 1. 需求确认 | 用户原始需求（文本+风格要求） | 检查点 Step0：展示引擎+音色候选给用户确认 | 确认后的需求规格 |
| 2. 文本预处理 | 确认后的原始文本 | 按标点分段（。！？为界，12字/段优先），过滤空段/纯标点段 | 配音序列（分段列表） |
| 3. 参数配置 | 配音序列+用户风格偏好 | 选引擎(edge-tts/ChatTTS) → 选音色 → 设语速(+10%)/音调(-2Hz) | 配音参数配置单 |
| 4. 语音生成 | 配音序列+参数配置 | 检查点Step2音色确认 → 调用 engine.generate(seq, params) → 检查点Step3输出前确认 | 输出文件到 `outputs/audio/` |
| 5. 集成输出 | 配音文件+原始脚本 | 按 `outputs/script.json` 镜头编号对应命名，生成字幕时间轴 | `outputs/audio/scene_XX.mp3` + `outputs/subtitles.json` |

### 配音参数推荐值

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| rate | `+10%` | 语速稍微加快，适合短视频节奏 |
| pitch | `-2Hz` | 音调微降，更沉稳 |
| voice | 按场景选 | 见引擎选择音色表 |

### 输出规范
- 格式：MP3（edge-tts）/ WAV（ChatTTS）
- 路径：`outputs/audio/voiceover.mp3`
- 采样率：16000Hz（edge-tts）/ 24000Hz（ChatTTS）
- 文件名：有多个配音时按镜头编号命名 `outputs/audio/scene_01.mp3`

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

## 边界条件处理

| # | 场景 | 处理方式 |
|---|------|----------|
| 1 | 网络不可用（edge-tts 需联网） | 提示用户检查网络连接，提供重试选项；如有本地缓存则用缓存 |
| 2 | FFmpeg 未安装（ChatTTS 保存 WAV 需依赖） | 自动检测 → 提示安装命令 `pip install soundfile` 或手动安装 FFmpeg |
| 3 | 输入文本为空或纯英文 | 提示"请输入中文文本"，要求用户提供有效内容 |
| 4 | 输出目录 `outputs/audio/` 不存在或不可写 | 自动创建目录；若权限不足则报错并提示手动创建 |
| 5 | 长文本自动分段后某段生成失败 | 跳过失败段，继续生成其余段，最后汇总汇报成功/失败段编号 |
| 6 | 指定的音色 ID 不存在/接口返回错误 | 自动回退到默认音色 `zh-CN-YunxiNeural` 并提示用户 |
| 7 | 用户文本超过 2000 字 | 询问是否截取前 2000 字或分批处理，避免单次请求超时 |
| 8 | 文本已生成过配音（缓存碰撞） | 检测 `outputs/audio/` 下同名文件，询问是否覆盖 |

## 注意事项
1. edge-tts 需要网络连接，首次使用自动选择可用微软节点
2. ChatTTS 首次需下载模型（~2GB），存放于本地 models 目录
3. 长文本（>500字）自动分段，逐段生成后拼接
4. 配音时长自动计算，写入 script.json 的 start/end 字段
