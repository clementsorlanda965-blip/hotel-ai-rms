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

## 异常处理
| 场景 | 处理方式 |
|------|---------|
| 文件不存在（编辑模式） | 提示后切换新建模式 |
| 缺少python-docx库 | 自动 `pip install python-docx` |
| 文档>100页 | 拆分为 `_part1/_part2` 多文件 |
| 图片路径无效 | 跳过并记录到 `missing_images.txt` |
| 中文路径读写失败 | `os.path.abspath()` 转绝对路径重试 |

## 工作流程

### Step 1: 确认需求
输入用户描述 → 确定文档类型/格式/路径 → ⚠ **确认后继续**

### Step 2: 初始化文档
`from docx import Document` → 新建 `Document()` 或打开 `Document("路径.docx")`

### Step 3: 内容填充
- 标题 `add_heading` / 段落 `add_paragraph` + `add_run` / 表格 `add_table` / 图片 `add_picture`
- 格式: `run.font.size=Pt(12)`, `.color.rgb=RGBColor(r,g,b)`, `.bold=True`
- 替换: 遍历段落 `.text.replace('旧','新')`
- 页眉页脚: `doc.sections[0].header.paragraphs[0].text`

### Step 4: 排版
页边距 `Cm(2.5)` / 对齐 `CENTER` / 行距 `1.5` / 页码 → ⚠ **展示确认后保存**

### Step 5: 保存+打开
`doc.save("outputs/docx/{文件名}.docx")` → `os.startfile(路径)` → ⚠ **询问是否满意**

## 批量操作
- **合并**: 循环读取 → `add_page_break()` + 合并
- **模板填充**: `{{占位符}}` → `.replace`
- **批量替换**: 遍历段落+表格cell
