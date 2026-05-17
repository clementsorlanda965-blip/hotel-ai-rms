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
处理Word文档(.docx)。创建、读取、编辑、格式化。
## 强制规则
**所有文字输出必须是中文。** 用户是中文用户，所有生成的Word文档内容必须是中文。
**优先输出.docx格式文件。**
## 工作流程

### Step 1: 确认需求
- **输入**: 用户自然语言描述（"帮我写一份合同"、"打开报告.docx改标题"、"生成会议纪要"）
- **动作**: 明确文档类型（新建/编辑/读取）、格式要求（模板/自由）、输出路径
- **输出**: 任务确认清单（文档类型、操作模式、文件路径）

### Step 2: 初始化文档
- **工具**: `python-docx`（`from docx import Document`）
- **输入**: 模式选择
  - 新建: `Document()` 创建空白文档
  - 编辑: `Document("路径/文件.docx")` 打开已有文档
- **输出**: `doc` 对象就绪

### Step 3: 内容填充/编辑
- **标题**: `doc.add_heading('一级标题', level=1)`
- **段落**: `doc.add_paragraph('正文')` → `p.add_run('加粗').bold = True`
- **表格**: `doc.add_table(rows=3, cols=3)` → 遍历 `table.cell(r,c).text`
- **图片**: `doc.add_picture('图片.png', width=Inches(4))`
- **替换**: 遍历 `paragraphs` 用 `text.replace('旧','新')`
- **格式**: `run.font.size = Pt(12)`, `run.font.color.rgb = RGBColor(255,0,0)`
- **页眉页脚**: `doc.sections[0].header.paragraphs[0].text`
- **输出**: 填充完毕的 `doc` 对象

### Step 4: 排版与格式化
- **页边距**: `section.top_margin = Cm(2.5)`
- **段落对齐**: `paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER`
- **行距**: `paragraph.paragraph_format.line_spacing = 1.5`
- **页码**: 添加页脚 + 字段代码
- **输出**: 格式化完成的 `doc` 对象

### Step 5: 保存并输出
- **保存**: `doc.save(output_path)`
- **路径**: 文件路径用双引号包裹（兼容中文路径）
- **输出**: `outputs/docx/{文件名}_{时间}.docx`

### Step 6: 打开预览
- **自动打开**: 生成后立即调用 `os.startfile(output_path)` 打开
- **大文档**: 分页处理，超过50页建议拆分

## 批量操作
- **合并文档**: 循环读取多个docx → `target.add_page_break()` + 合并元素
- **模板填充**: 用占位符 `{{名称}}` → `text.replace('{{名称}}', '值')`
- **批量替换**: 遍历 `doc.paragraphs` + `doc.tables` 所有cell

## Python 示例
```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
doc = Document()
doc.add_heading('项目可行性研究报告', 0)
p = doc.add_paragraph('正文内容')
run = p.add_run('加粗文字')
run.bold = True
doc.add_table(rows=3, cols=3)
doc.save('outputs/docx/output.docx')
import os; os.startfile('outputs/docx/output.docx')
```
