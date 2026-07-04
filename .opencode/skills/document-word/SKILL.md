---
name: document-word
description: Word文档全操作——创建、读取、编辑、格式化.docx文件。目录、标题、页眉页脚、表格、图片、批注。输入"word""docx""文档""手册""报告"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write
metadata:
  language: zh-CN
---

## 做什么
创建、读取、编辑、格式化 Word 文档(.docx)。支持目录、多级标题、表格、图片、页眉页脚、批注、模板替换。

## 强制规则
**所有输出必须是中文。** 文档内容、页眉页脚、图表标注全部中文。
**优先输出 .docx 格式。** 保存到 `outputs/docx/`，文件名 `{文档名}_v{版本}.docx`。

## 工作流程

### Step 1: 确认需求
输入用户描述 → 确定文档类型/格式/路径。

### Step 2: 初始化文档
```python
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
doc = Document()
```

### Step 3: 内容填充
**标题与段落**
```python
doc.add_heading("一级标题", level=1)
p = doc.add_paragraph()
run = p.add_run("正文内容")
run.font.size = Pt(12)
run.font.bold = True
```

**表格**
```python
table = doc.add_table(rows=5, cols=4, style="Light Grid Accent 1")
for i, row in enumerate(table.rows):
    for j, cell in enumerate(row.cells):
        cell.text = f"第{i+1}行 第{j+1}列"
```

**模板替换**
```python
for p in doc.paragraphs:
    if "{{占位符}}" in p.text:
        p.text = p.text.replace("{{占位符}}", "替换内容")
```

### Step 4: 排版
```python
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
```

### Step 5: 保存
```python
doc.save("outputs/docx/文档_v1.docx")
```

## 批量操作
- 合并文档: 循环读取 → add_page_break() + 逐元素复制
- 模板批量替换: 遍历段落+表格cell → replace

## 异常处理
| 场景 | 处理方式 |
|------|---------|
| 缺少python-docx | pip install python-docx --break-system-packages |
| 文档>100页 | 拆分为 _part1/_part2 多文件 |
| 中文路径失败 | os.path.abspath() 转绝对路径重试 |

## 资源参考
- python-docx: https://python-docx.readthedocs.io/
- 输出路径: outputs/docx/
