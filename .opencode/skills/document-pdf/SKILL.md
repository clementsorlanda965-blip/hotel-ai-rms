---
name: document-pdf
description: PDF处理——合并、拆分、提取文字/图片、OCR识别、加密解密、添加水印、格式转换。输入"pdf""PDF""合并""拆分""OCR"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write
metadata:
  language: zh-CN
---
## 强制规则
**所有文字输出必须是中文。** 用户是中文用户，生成的PDF文字内容必须是中文。
处理PDF文件：合并、拆分、提取、OCR、加密、转换。
输出路径：`outputs/`，文件名 `{操作}_{输入文件名}_v{版本}.pdf`

## 工作流

1. **确认需求** — 问用户：要做什么操作？输入文件路径？输出格式偏好？
2. **选择工具** — 按操作类型选择对应的Python库和脚本
3. **执行操作** — 运行脚本处理PDF，捕获脚本输出和错误
4. **输出文件** — 保存文件到 `outputs/`，打开文件供用户预览
5. **确认结果** — 询问用户是否满意，不满意则回到步骤1或2调整

## 操作对照表

| 操作 | 库 | 输入 | 输出 |
|------|----|------|------|
| 合并 | pypdf | 多个PDF路径列表 | 单个PDF |
| 拆分 | pypdf | 单个PDF+页数/章节标记 | 多个PDF |
| 提取文字 | pdfplumber | PDF路径 | TXT/CSV |
| 提取图片 | pypdf | PDF路径 | 图片文件 |
| OCR | pytesseract+pypdf | 扫描件PDF | 可搜索PDF/TXT |
| 加密 | pypdf | PDF+密码 | 加密PDF |
| 水印 | pypdf+reportlab | PDF+水印内容 | 带水印PDF |
| 转Word | pdf2docx | PDF | DOCX |
| 转图片 | pdf2image | PDF | PNG/JPEG |

## 实现示例

```python
from pypdf import PdfReader, PdfWriter
# 合并
writer = PdfWriter()
for f in ['a.pdf','b.pdf']:
    reader = PdfReader(f)
    for page in reader.pages: writer.add_page(page)
writer.save('outputs/merged.pdf')
# 提取文字
import pdfplumber
with pdfplumber.open('file.pdf') as pdf:
    text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
```
