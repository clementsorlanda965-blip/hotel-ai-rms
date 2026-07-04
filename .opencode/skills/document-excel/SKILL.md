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
**所有输出必须是中文。** 表头、数据标签、图表标注全部中文。
输出到 `outputs/xlsx/`，文件名 `{主题}_v{版本}.xlsx`。

## 工作流程
1. 理解需求 — 确认数据类型、输出目标、是否需要透视筛选
2. 准备数据 — 从用户输入/Read读取源数据；无数据则新建工作表
3. 生成Excel — 按需执行写入/公式/图表/格式化/分析操作
4. 保存输出 — 保存为 .xlsx，打开预览，用户确认

## 核心操作

### 写入数据
```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule, DataBarRule
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "数据"
data = [["产品","销量","单价"],["A",100,50],["B",200,45],["C",150,55]]
for row in data:
    ws.append(row)
```

### 公式
```python
ws["C2"] = "=B2*50"                         # 乘法
ws["D2"] = "=IF(B2>100,"达标","待改进")"    # IF条件
ws["E2"] = "=SUM(B2:B10)"                   # SUM
ws["F2"] = "=AVERAGE(B2:B10)"               # AVERAGE
ws["G2"] = "=VLOOKUP(A2,Sheet2!A:B,2,FALSE)"# VLOOKUP
ws["H2"] = "=IFERROR(B2/C2,0)"              # 除零保护
```

### 图表
```python
chart = BarChart()
chart.title = "销量对比"
chart.y_axis.title = "数量"
data_ref = Reference(ws, min_col=2, min_row=1, max_row=10)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=10)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
chart.width = 18; chart.height = 12
ws.add_chart(chart, "E5")
```

图表类型：柱状图(BarChart) / 折线图(LineChart) / 饼图(PieChart) / 散点图(ScatterChart)

### 格式化
```python
header_font = Font(bold=True, size=12, color="FFFFFF")
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
for cell in ws[1]:
    cell.font = header_font
    cell.fill = header_fill
ws.freeze_panes = "A2"  # 冻结首行
# 条件格式：低于60标红
ws.conditional_formatting.add("B2:B20",
    CellIsRule(operator="lessThan", formula=["60"],
              fill=PatternFill(bgColor="FFC7CE"),
              font=Font(color="9C0006")))
# 自动列宽
for col in ws.columns:
    max_len = max(len(str(cell.value or "")) for cell in col)
    ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 3
```

### 多工作表
```python
ws2 = wb.create_sheet(title="分析")
ws3 = wb.create_sheet(title="图表", index=0)
```

### 透视表（pandas）
```python
import pandas as pd
df = pd.read_excel("data.xlsx")
pivot = pd.pivot_table(df, values="金额", index="类别", columns="月份", aggfunc="sum")
pivot.to_excel("pivot.xlsx", sheet_name="透视表")
```

## 异常处理
| 场景 | 处理方式 |
|------|---------|
| 缺少openpyxl | pip install openpyxl --break-system-packages |
| 公式循环引用 | 用IFERROR包装，标注给用户 |
| 超大文件 | 分拆为多个工作表 |
| CSV编码 | 指定 encoding="utf-8-sig" |

## 资源参考
- openpyxl文档: https://openpyxl.readthedocs.io/
- pandas: https://pandas.pydata.org/
- 行业特化: hotel-bi（酒店BI）/ fb-cost-control（餐饮成本）
