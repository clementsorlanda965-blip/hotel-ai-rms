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
import os

audio_path = "outputs/audio/voiceover.mp3"

if not os.path.exists(audio_path):
    raise FileNotFoundError(f"音频文件不存在: {audio_path}")

model = AutoModel(
    model="iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn",
    vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    punc_model="iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727",
)

result = model.generate(input=audio_path)
# result[0]["text"] → 完整识别文本（str）
# result[0]["timestamp"] → 逐句时间戳（list of [start, end]）
```

### 4. 输出 SRT 格式

SRT规范：序号从1开始，时间轴格式 `HH:MM:SS,mmm --> HH:MM:SS,mmm`，每段字幕不超过42个中文字符。

```python
def write_srt(segments, output_path="outputs/subtitles/subtitles.srt"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = seg["start"]  # 秒
            end = seg["end"]
            text = seg["text"].strip()
            f.write(f"{i}\n")
            f.write(f"{fmt_time(start)} --> {fmt_time(end)}\n")
            f.write(f"{text}\n\n")

def fmt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
```

示例SRT输出：
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

## 异常与边界条件

| 场景 | 触发条件 | 处理动作 |
|------|---------|---------|
| 输入文件不存在 | 路径无效或文件缺失 | 提示用户检查路径，退出并输出错误信息 |
| 格式不支持 | 非音频格式/编码异常 | 尝试用 ffmpeg 转码为 WAV，失败则报错退出 |
| ffmpeg 缺失 | 系统未安装 ffmpeg | 自动切换 torchaudio 加载，若 torchaudio 也失败则提示用户安装 |
| 音频为空/损坏 | 文件存在但无法解码 | 返回"音频内容为空，请检查文件"，终止处理 |
| 模型下载失败 | 网络/缓存问题导致模型加载中断 | 自动切换 openai-whisper small 模型降级 |
| GPU 显存不足 | CUDA OOM | 自动切换 CPU 模式重试，速度降低但功能正常 |
| 长音频OOM | >30分钟音频内存溢出 | 自动分段（每段10分钟），逐段识别后合并 |
| 批量中途失败 | 批量处理中某一文件出错 | 跳过该文件，记录错误日志，继续处理剩余文件 |

## 降级策略
FunASR 模型下载失败时，自动切换至 `openai-whisper`（已随 FunASR 安装）：
```python
import whisper
model = whisper.load_model("small")
result = model.transcribe("audio.mp3")
```
GPU 显存不足时自动回退 CPU 模式：
```python
import whisper
model = whisper.load_model("small", device="cpu")
result = model.transcribe("audio.mp3")
```
