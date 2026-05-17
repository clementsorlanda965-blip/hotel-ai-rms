---
name: frontend-design
description: 前端界面设计——生成Web UI（网站/仪表盘/落地页/React组件/HTML/CSS）。输入"前端""网页""界面""UI""网站"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write Glob
metadata:
  language: zh-CN
---
## 做什么
生成前端界面代码。拒绝千篇一律的AI设计风格。

## 输出格式
- 海报/宣传图：PNG图片（Python PIL渲染，1080x1920），用PIL直接渲染
- 单页HTML / React组件(JSX) / 原生CSS

## 设计原则
- 独特：不用通用模板 | 专业：符合行业标准 | 可用：响应式

## 流程
1. **理解需求** — 确认4项：页面类型（落地页/仪表盘/后台/官网）、目标用户、主色调、参考风格（极简/玻璃态/粗野主义）
2. **设计布局** — 文字描述导航/Hero区(标题+CTA按钮)/内容区(卡片网格)/底部
3. **配色字体** — 主色1+辅色1+中性色2标16进制值；字体Inter/系统无衬线
4. **确认设计** — 展示布局/配色方案给用户，让用户确认后再编码
5. **生成代码** — 单页HTML用Tailwind CDN；React default export+CSS modules；图表用ECharts
6. **输出** — HTML存outputs/html/并自动打开；组件返回代码块

## 异常处理
- **需求模糊** → 默认轻量单页HTML（Tailwind CDN，白底黑字）
- **库不可用** → 降级CSS图形，纯HTML
- **输出失败** → 返回代码块，提示手动保存