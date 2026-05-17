---
name: presentation
description: PPT演示全系列——支持HTML动画、企业品牌、学术答辩、MARP、可编辑拖拽、原生PPTX。26种风格，14家公司品牌自动匹配。输入"PPT""演示""幻灯片""汇报""答辩"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write Glob
metadata:
  language: zh-CN
---

## 做什么

输入内容和需求，输出幻灯片。支持多种输出格式和风格。

## 模式选择

| 模式 | 触发词 | 输出 |
|------|--------|------|
| HTML动画 | 动画、网页展示、炫酷 | HTML单文件，CSS动画 |
| 企业品牌 | 公司、品牌、企业PPT | 自动匹配14家公司品牌色 |
| 学术答辩 | 答辩、论文、学术、基金 | 行动标题+论证结构 |
| MARP | marp、markdown、md | Markdown转幻灯片 |
| 可编辑 | 拖拽、在线编辑 | HTML拖拽编辑器 |
| 原生PPTX | pptx、pptx文件、编辑PPT | pptxgenjs生成 |

## 风格速查

26种风格：麦肯锡/BCG/苹果/谷歌/微软/腾讯/阿里/字节/华为/小米/极简/暗黑/渐变/霓虹/赛博/学术/杂志/书本/漫画/手绘/治愈/复古/奢华/清新/工业/商务

## 企业品牌色

阿里#FF6A00 腾讯#0052D9 字节#3370FF 华为#CF0A2C 小米#FF6900 京东#E2231A 美团#2FB846 拼多多#E02E24 百度#2932E1 网易#C4132E B站#FB7299 知乎#0066FF 快手#FF4906 特斯拉#E82127

## 强制规则

**所有文字输出必须是中文。** 封面、标题、正文、图表标注、页脚——全部中文。禁止输出英文PPT。

**图片必须输出图片格式(png/jpg)，禁止输出HTML网页。**

**优先输出PPTX格式。** 用户要"PPT""课件""培训材料"时，默认使用 python-pptx 生成 .pptx 文件。

**输出路径规则：** 文件保存到 `outputs/pptx/`（PPTX）或 `outputs/html/`（HTML），文件名 `{主题}_v{版本}.pptx`

## 实现指引

**PPTX 生成 (python-pptx)：**
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
prs = Presentation()
prs.slide_width  = Inches(13.333)  # 16:9
prs.slide_height = Inches(7.5)
# 添加标题页
slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白版式
slide.shapes.title.text = "中文标题"
prs.save("outputs/pptx/主题.pptx")
```

**HTML 输出：** 生成独立 HTML 文件，CSS 内联，无外部依赖。保存到 `outputs/html/`

**品牌色使用格式：** 取企业品牌色值，直接写入 PPTX/HTML 的主题色定义中

## 异常处理

- python-pptx 未安装 → 自动 `pip install python-pptx`，失败则降级 HTML 输出
- 中文字体缺失 → 使用 fallback 字体（SimHei/微软雅黑），生成前提示用户确认
- 内容超长超出幻灯片容量 → 自动拆分多页或精简文字，展示预览供用户确认
- 风格参数无效或拼写错误 → 匹配最接近风格，提示用户确认
- 生成脚本执行异常 → 捕获错误信息重试，超3次转降级方案并告知用户

## 工作流

1. 问用户：什么内容？什么风格？什么场景？
2. 生成结构——中文大纲（标题+各页要点），展示给用户确认 → **用户确认后进入步骤3**
3. 生成文件——优先PPTX(python-pptx)，次选HTML，均需中文内容
4. 输出文件并打开 → **询问用户是否需要调整**
5. 如需调整：回到步骤2或3修改，最多3轮；超限则建议用户重新开始
6. 用户确认满意后，告知文件保存路径

## 检查点

| 时机 | 检查内容 | 用户操作 |
|------|---------|---------|
| 大纲生成后 | 标题层级、页码分配、内容覆盖 | 确认/修改 |
| 文件生成后 | 预览效果、中文完整性 | 确认/调整 |
| 异常触发时 | 降级方案选择 | 确认是否接受 |
| 3轮调整后 | 是否继续迭代 | 决定继续/收工
