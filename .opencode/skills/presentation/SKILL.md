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

## 输出模式优先级
用户要PPT/课件/培训材料 → python-pptx 生成.pptx（优先）
用户要动画/网页展示   → HTML动画
用户要MARP/Markdown   → MARP模式
其他需求（快速原型）   → HTML单页

## 模式选择
| 模式 | 触发词 | 输出 |
|------|--------|------|
| 原生PPTX（⭐优先） | pptx、课件、培训 | python-pptx生成.pptx |
| HTML动画 | 动画、网页展示 | HTML单文件+CSS动画 |
| 企业品牌 | 公司、品牌配色 | 自动匹配14家公司品牌色 |
| 学术答辩 | 答辩、论文 | 行动标题+论证结构 |
| MARP | marp、markdown | Markdown转幻灯片 |

## 企业品牌色
阿里#FF6A00 腾讯#0052D9 字节#3370FF 华为#CF0A2C 小米#FF6900
京东#E2231A 美团#2FB846 B站#FB7299 知乎#0066FF

## 强制规则
所有输出必须是中文。优先输出PPTX（python-pptx）。
输出到 outputs/pptx/，文件名 {主题}_v{版本}.pptx

## 实现指引

### PPTX生成
```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
# 标题页
slide = prs.slides.add_slide(prs.slide_layouts[6])
title = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(2))
tf = title.text_frame
tf.text = "中文标题"
tf.paragraphs[0].alignment = PP_ALIGN.CENTER
# 演讲者备注
notes_slide = slide.notes_slide
notes_slide.notes_text_frame.text = "此处为演讲备注"
prs.save("outputs/pptx/主题_v1.pptx")
```

### 26种风格
麦肯锡/BCG/苹果/谷歌/微软/腾讯/阿里/字节/华为/小米/极简/暗黑/渐变/霓虹/赛博/学术/杂志/书本/漫画/手绘/治愈/复古/奢华/清新/工业/商务

## 工作流
1. 问用户：什么内容？什么风格？什么场景？
2. 生成中文大纲（标题+各页要点），用户确认
3. 按优先级规则选输出格式，生成文件
4. 打开预览，问用户是否需要调整（最多3轮）

## 检查点
| 时机 | 检查内容 |
|------|---------|
| 大纲生成后 | 标题层级、页码分配、内容覆盖 |
| 文件生成后 | 预览效果、中文完整性 |
| 异常触发时 | 降级方案选择 |

## 异常处理
| 场景 | 处理方式 |
|------|---------|
| python-pptx未安装 | pip install python-pptx，失败降级HTML |
| 中文字体缺失 | 使用fallback字体（SimHei/微软雅黑） |
| 内容超长 | 自动拆分多页 |
| 脚本异常 | 捕获错误重试，超3次转降级 |

## 资源参考
- python-pptx: https://python-pptx.readthedocs.io/
- 输出路径: PPTX→outputs/pptx/ | HTML→outputs/html/
