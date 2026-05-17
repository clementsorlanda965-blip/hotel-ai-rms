---
name: image-generator
description: >-
  AI图片与海报封面生成——主力引擎 ComfyUI（模块化扩散模型）搭配 PIL CPU降级方案。
  支持视频封面、海报、配图、缩略图。输出PNG/JPG到 outputs/images/。
  输入"生图""海报""封面""配图""AI绘图""做图""生成图片""缩略图"时触发。
  所有文字输出为中文。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write
metadata:
  language: zh-CN
  audience: short-video-creator
---

## 强制规则
所有文字输出必须是中文。图片必须是PNG/JPG图片格式，用Python PIL直接渲染，禁止输出HTML网页当图片。输出到 `outputs/images/` 目录。

## 做什么
根据文字描述生成图片，用于视频封面、内容配图、海报缩略图。ComfyUI 主力生成高质感图片，PIL 降级方案确保无GPU也能产出可用画面。

## 引擎选择

| 引擎 | 适用场景 | 依赖 | 输出质量 |
|------|----------|------|----------|
| **ComfyUI** | 正式封面、高质量海报 | GPU + 模型文件 | ★★★★★ |
| **PIL 降级** | 快速预览、CPU兜底 | 无额外依赖 | ★★★ |

## 检查点（用户确认）

执行前必须暂停并询问用户，确认后再继续：

| # | 触发时机 | 确认内容 | 用户操作 |
|---|---------|---------|---------|
| 1 | 首次 ComfyUI 模型下载前 | "即将下载模型（SD1.5约4GB / SDXL约7GB），是否继续？" | 是/否 — 否则切 PIL 降级 |
| 2 | ComfyUI 生图前 | "即将调用 GPU 生成图片，耗时约10-60秒，是否继续？" | 是/否 — 否则切 PIL 降级 |
| 3 | 批量生成 N 张配图前 | "即将生成 {N} 张配图序列，预计耗时 {N×30}秒，是否继续？" | 是/否 — 否则退出 |

## 工作流

### 1. 封面/海报生成
```
用户描述 → 增强为英文Prompt → ComfyUI生图 → 叠加中文标题 → 输出PNG
```

或 CPU 降级（引用检查点1-2，用户拒绝时切换）：
```
用户描述 → PIL文字卡片（深色背景+大字标题+副标题） → 输出PNG
```

### 2. 尺寸规范

| 平台 | 尺寸 | 用途 |
|------|------|------|
| 抖音/快手 | 1080×1920 (9:16) | 竖屏视频封面 |
| B站/YouTube | 1280×720 (16:9) | 横屏视频封面 |
| 小红书 | 1080×1440 (3:4) | 图文封面 |

### 3. ComfyUI 调用方式
ComfyUI 位于 `tools/ComfyUI/`，通过 API 调用（引用检查点2）：
```python
import json, urllib.request

def comfy_generate(prompt, width=512, height=912):
    url = "http://127.0.0.1:8188/prompt"
    payload = {
        "prompt": {},  # 使用默认工作流
        "client_id": "opencode"
    }
    # 注入 prompt 到工作流... （具体节点因工作流而异）
```

首次使用需手动启动 ComfyUI：
```
python tools/ComfyUI/main.py
```
然后通过浏览器 http://127.0.0.1:8188 配置工作流，后续 API 调用自动化。

### 4. PIL 降级方案（CPU可用）
```python
from PIL import Image, ImageDraw, ImageFont

def pil_poster(title, subtitle="", size=(1080, 1920)):
    img = Image.new("RGB", size, (14, 14, 18))  # 深色背景
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype("simhei.ttf", 80)
    font_sub = ImageFont.truetype("simhei.ttf", 36)
    draw.text((60, 600), title, fill=(255,255,255), font=font_title)
    draw.text((60, 720), subtitle, fill=(180,180,180), font=font_sub)
    img.save("outputs/images/poster.png")
```

### 5. 与 video-factory 集成
替代环节二的 AI 画面生成：
```
script.json[视觉描述] → image-generator → outputs/frames/scene_XX.png → video-factory合成
```

封面单独生成：
```
视频主题 → image-generator → outputs/images/cover.png
```

## 输出规范
- 格式：PNG（优先）/ JPG
- 路径：`outputs/images/`（单张）或 `outputs/frames/`（视频配图序列）
- 命名：`cover.png`（封面）/ `scene_01.png`（配图序列）
- 色彩空间：RGB

## 异常与边界条件

| 场景 | 触发条件 | 处理动作 |
|------|---------|---------|
| ComfyUI 未启动 | API 调用连接失败 | 提示用户启动 ComfyUI：`python tools/ComfyUI/main.py`，或切 PIL 降级 |
| ComfyUI API 超时 | 生图超过60秒无响应 | 重试1次，仍超时则提示用户检查 GPU 状态，切 PIL 降级 |
| GPU 不可用 | CUDA 未安装/显存不足 | 自动切换 PIL 降级方案，提示"当前无 GPU，使用 CPU 文字卡片模式" |
| 字体文件缺失 | simhei.ttf / msyh.ttc 未找到 | 自动尝试系统备用字体（arial.ttf / noto-sans），均失败则用默认字体 |
| 输出目录不存在 | outputs/images/ 未被创建 | 自动 `os.makedirs` 创建，确保写入路径可用 |
| 磁盘空间不足 | 保存图片时磁盘满 | 提示用户释放空间，输出临时路径到 temp 目录 |
| 图片生成质量差 | PIL 降级输出过于简陋 | 提示用户"建议安装 ComfyUI 以获取更高品质图片" |
