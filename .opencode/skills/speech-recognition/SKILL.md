---
name: speech-recognition
description: >-
  语音识别与字幕生成——基于阿里达摩院 FunASR，支持中文语音转文字、自动标点、时间轴对齐、SRT字幕输出。
  输入"语音识别""音频转文字""字幕生成""字幕提取""ASR""识别字幕"时触发。
  所有文字输出为中文。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write
metadata:
  language: zh-CN
  audience: short-video-creator
---

## 强制规则
所有文字输出必须是中文。字幕文本必须是中文。输出 SRT 字幕文件到 `outputs/subtitles/` 目录。

## 做什么
将音频/视频中的语音转为文字，生成带时间轴的 SRT 字幕文件。用于从录音/视频中提取旁白文字、为已有视频补字幕、将音频素材转为可用文本。

## 模式选择

| 模式 | 输入 | 输出 | 适用场景 |
|------|------|------|----------|
| **标准识别** | 音频文件(.wav/.mp3) | SRT字幕 + 纯文本 | 为视频补字幕 |
| **时间轴对齐** | 音频 + 已知文本 | 字级时间轴 SRT | 已有文字，只需卡时间点 |
| **批量处理** | 多个音频文件 | 批量 SRT | 系列视频字幕 |

## 检查点（用户确认）

执行前必须暂停并询问用户，确认后再继续：

| # | 触发时机 | 确认内容 | 用户操作 |
|---|---------|---------|---------|
| 1 | 首次模型下载前 | "即将下载 FunASR 模型（约1GB），是否继续？" | 是/否 — 否则退出或降级 |
| 2 | 批量处理多个音频前 | "即将处理 {N} 个音频文件，生成 {N} 个 SRT，是否继续？" | 是/否 — 否则退出 |
| 3 | 长音频（>30分钟）处理前 | "当前音频超过30分钟，耗时较长，是否继续？" | 是/否 — 否则退出 |

## 工作流

### 1. 音频准备
```
视频文件 → 提取音频(ffmpeg) → 16000Hz 单声道 WAV → FunASR
```

若无 ffmpeg，torchaudio 可直接加载常见音频格式。

### 2. 模型选择

| 模型 | 特点 | 速度 |
|------|------|------|
| `iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn` | 标准中文ASR，含VAD+标点 | 快 |
| `iic/speech_paraformer-large_asr_nat-zh-cn` | 纯ASR，无VAD | 最快 |
| `iic/speech_seaco_paraformer_large_asr_nat-zh-cn` | 高精度，热词增强 | 中 |

### 3. 用户确认模型 → 加载
引用检查点1，确认后执行：
```python
from funasr import AutoModel

model = AutoModel(
    model="iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn",
    vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    punc_model="iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727",
)

result = model.generate(input="outputs/audio/voiceover.mp3")
# result[0]["text"] → 完整识别文本
# result[0]["timestamp"] → 逐句时间戳
```

### 4. 输出 SRT 格式
```
1
00:00:01,200 --> 00:00:03,500
大明王朝是中国历史上

2
00:00:03,600 --> 00:00:06,800
最后一个汉人建立的封建王朝
```

输出路径：`outputs/subtitles/subtitles.srt`

### 5. 与 video-factory 集成
可直接替代环节四的 SRT 字幕生成，或作为独立环节为已有视频补字幕：
```
音频 → speech-recognition → outputs/subtitles/subtitles.srt → video-factory合成
```

## 降级策略
FunASR 模型下载失败时，使用 `openai-whisper`（已随 FunASR 安装）作为降级方案：
```python
import whisper
model = whisper.load_model("small")
result = model.transcribe("audio.mp3")
```

## 注意事项
1. 音频质量决定识别率：建议 16kHz、无背景噪音
2. 首次使用会自动下载模型（~1GB），存放于本地缓存
3. 长音频（>30分钟）自动分段识别，避免内存溢出
4. 生成的字幕自动做中文标点归一化（全角统一）
