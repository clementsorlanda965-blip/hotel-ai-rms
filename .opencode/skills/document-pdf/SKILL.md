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
**所有输出必须是中文。** 生成的PDF文字内容必须是中文。
输出路径：`outputs/pdf/`，文件名 `{操作}_{输入文件名}_v{版本}.pdf`

## 工作流
1. 确认需求：操作类型、输入路径、输出格式 → 用户确认
2. 选择工具：按操作对照表选对应库
3. 执行操作：运行脚本处理PDF
4. 输出文件：保存到 outputs/pdf/ → 打开预览 → 用户确认

## 操作对照表
| 操作 | 库 | 输入→输出 |
|------|----|-----------|
| 合并/拆分 | pypdf.PdfReader/PdfWriter | 多PDF→单PDF / 单→多 |
| 提取文字 | pdfplumber | PDF→TXT/CSV |
| 提取图片 | pypdf | PDF→图片文件 |
| OCR中文 | pytesseract+pdf2image | 扫描件→可搜索PDF |
| 加密/解密 | pypdf | PDF+密码→加密PDF |
| 水印 | pypdf+reportlab | PDF→带水印PDF |
| 转Word | pdf2docx | PDF→DOCX |
| 转图片 | pdf2image | PDF→PNG(逐页) |
| 压缩 | PdfWriter.compress | PDF→小体积PDF |

## 实现示例

### 合并
```python
from pypdf import PdfReader, PdfWriter
writer = PdfWriter()
for f in ["a.pdf", "b.pdf"]:
    for page in PdfReader(f).pages:
        writer.add_page(page)
writer.write("outputs/pdf/merged.pdf")
```

### 提取文字
```python
import pdfplumber
with pdfplumber.open("input.pdf") as pdf:
    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
```

### OCR 中文扫描件
```python
import pytesseract
from pdf2image import convert_from_path
images = convert_from_path("scan.pdf", dpi=300)
text = ""
for img in images:
    text += pytesseract.image_to_string(img, lang="chi_sim+chi_tra") + "\n"
```

### 加密
```python
writer = PdfWriter()
for page in PdfReader("input.pdf").pages:
    writer.add_page(page)
writer.encrypt(user_password="123456")
writer.write("outputs/pdf/encrypted.pdf")
```

## 异常处理
| 场景 | 处理方式 |
|------|---------|
| 文件不存在 | 列出目录下PDF供选择 |
| 库未安装 | pip install <库名> --break-system-packages |
| PDF已加密无密码 | 询问密码，无法解密则跳过 |
| OCR中文差 | 指定 lang=chi_sim+chi_tra，300dpi以上 |
| 输出已存在 | 自动追加版本号 _v2 |

## 资源参考
- pypdf: https://pypdf.readthedocs.io/
- pdfplumber: https://github.com/jsvine/pdfplumber
- pytesseract OCR: https://github.com/madmaze/pytesseract
