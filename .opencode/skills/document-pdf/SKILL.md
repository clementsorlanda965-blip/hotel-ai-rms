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

1. **确认需求**：操作类型、输入路径、输出格式 → **用户确认**
2. **选择工具**：按操作对照表选对应库及脚本
3. **执行操作**：运行脚本处理PDF，捕获输出和错误
4. **输出文件**：保存到 `outputs/`，打开预览 → **用户预览确认**
5. **确认结果**：满意则告知路径结束；需调整则回到步骤1，最多3轮
6. 异常触发时 → **询问用户是否接受降级方案**

## 检查点

| 时机 | 检查内容 | 用户操作 |
|------|---------|---------|
| 需求确认后 | 操作类型、路径、格式 | 确认/修改 |
| 文件生成后 | 预览效果 | 确认/调整 |
| 异常触发 | 降级方案 | 接受/拒绝 |
| 3轮调整后 | 是否继续 | 继续/收工 |

## 操作对照表

| 操作 | 库 | 输入→输出 |
|------|----|-----------|
| 合并/拆分 | pypdf | 多PDF→单PDF / 单PDF→多PDF |
| 提取文字 | pdfplumber | PDF→TXT/CSV |
| 提取图片 | pypdf | PDF→图片文件 |
| OCR | pytesseract+pypdf | 扫描件→可搜索PDF/TXT |
| 加密/水印 | pypdf+reportlab | PDF+参数→加密/带水印PDF |
| 转Word | pdf2docx | PDF→DOCX |
| 转图片 | pdf2image | PDF→PNG/JPEG |

## 异常处理

- 文件不存在 → 列出目录下PDF供选择
- 库未安装 → `pip install <库名>`，失败则提示手动安装
- PDF已加密无密码 → 询问密码，否则跳过
- OCR中文差 → 指定 `lang=chi_sim+chi_tra`
- 混入非PDF → 过滤后提示用户确认
- 输出已存在 → 询问覆盖/重命名/跳过

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
