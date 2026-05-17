---
name: frontend-design
description: 前端界面设计——生成独特专业的Web UI，包括网站、仪表盘、落地页、React组件、HTML/CSS。输入"前端""网页""界面""UI""网站"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write Glob
metadata:
  language: zh-CN
---
## 做什么
生成前端界面代码。拒绝千篇一律的AI设计风格。
## 强制规则

**所有文字输出必须是中文。**

**海报/图片需求必须输出PNG/JPG图片格式。** 用Python PIL直接渲染，禁止输出HTML网页。输出后自动打开图片。

## 输出格式
- 海报/宣传图：PNG图片（Python PIL渲染，1080x1920）
- 单页HTML：Web页面预览
- React组件：JSX/TSX代码
- 原生CSS：无框架样式
## 设计原则
- 独特：不用通用模板，每次创造不同设计
- 专业：符合行业标准，不花哨
- 可用：响应式、可访问、性能好
## 流程
1. **理解需求** — 确认4项：页面类型（落地页/仪表盘/后台/官网）、目标用户（B端/C端/内部）、主色调偏好（如蓝色商务/暖色生活/深色科技）、参考风格（极简/玻璃态/粗野主义）
2. **设计布局** — 文字描述页面结构，规格：导航区标题+链接/Hero区标题+副标题+CTA按钮/内容区卡片网格/底部联系方式，每区标注预期元素
3. **选择配色和字体** — 主色1+辅色1+中性色2共4色，标注16进制色值；字体选Inter/系统无衬线/等宽，HTML用font-family stack
4. **生成代码** — 单页HTML用Tailwind CDN行内样式；React组件默认export+CSS modules；复杂图表用ECharts CDN；判断需求后选择最合适的方案
5. **输出可预览的文件** — HTML保存到outputs/html/并自动打开预览；组件代码返回代码块
