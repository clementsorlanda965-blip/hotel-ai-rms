---
name: document-excel
description: Excel表格操作——数据分析、公式计算、图表生成、格式化。支持xlsx/xlsm/csv/tsv。输入"excel""表格""数据""公式""图表""xlsx"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write
metadata:
  language: zh-CN
---
## 强制规则
**所有文字输出必须是中文。** 表头、数据标签、图表标注全部中文。

## 工作流程
1. **理解需求** — 确认数据类型（新表/已有数据分析）、输出目标（报表/图表/公式）、是否透视筛选
2. **准备数据** — 从用户输入或Read工具读取源数据；若无则新建工作表定义列头
3. **选择操作** — 按需执行以下项：
   - 写入数据：填充单元格/行列/工作表
   - 公式：SUM/AVERAGE/VLOOKUP/IF/INDEX-MATCH
   - 图表：柱状图/折线图/饼图/散点图
   - 格式化：合并单元格/条件格式/冻结窗格/数据验证
   - 分析：排序/筛选/透视表
4. **确认操作** — 展示选定的操作和预览给用户，确认后再生成
5. **生成文件** — 用openpyxl构建Workbook，应用所有操作，保存为`.xlsx`
6. **输出** — 文件写入outputs/目录，自动打开预览
## 异常处理
- **数据源空** → 新建空表
- **公式无效** → IFERROR包装
- **保存失败** → 返回代码块
## Python 示例
```python
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws['A1'] = '名称'
ws['B1'] = '数量'
ws['A2'] = '产品A'
ws['B2'] = 100
ws['B3'] = '=SUM(B2:B2)'
wb.save('output.xlsx')
```
