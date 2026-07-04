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
生成前端界面代码（HTML / React / CSS / 海报图）。拒绝千篇一律的AI设计风格，注重独特性、专业性、响应式可用性。

## 工作流程

### Step 1: 理解需求
确认以下4项信息：
- **页面类型** — 落地页 / 仪表盘 / 后台管理 / 官网 / 海报
- **目标用户** — 如：酒店住客、企业客户、普通消费者
- **主色调** — 用户指定或留空自动选择
- **参考风格** — 极简 / 玻璃态 / 粗野主义 / 用户描述

> 如果用户输入模糊（仅说"做个页面"），执行默认流程：轻量单页HTML，Tailwind CDN，白底黑字，居中布局。

### Step 2: 设计布局
用文字描述页面结构，包含以下区域：
- **导航** — 顶部导航栏（Logo + 菜单项）
- **Hero区** — 主标题 + 副标题 + CTA按钮
- **内容区** — 卡片网格 / 功能展示 / 数据面板
- **底部** — 页脚（版权 / 链接）

```
示例布局描述：
"上方固定导航栏（深色半透明背景），Hero区全屏渐变背景+居中标题+按钮，
 内容区3列卡片网格展示核心功能，底部简约版权声明"
```

### Step 3: 选择技术栈
根据复杂度决定技术栈：

| 场景 | 技术选型 | 说明 |
|------|----------|------|
| 单页落地页 | Tailwind CSS CDN + 原生JS | 零配置，快速交付 |
| 中型仪表盘 | Alpine.js / htmx + Tailwind | 轻量响应式 |
| 复杂交互 | React + Vite + Tailwind | 组件化开发 |
| 静态展示 | 纯CSS Grid/Flexbox | 无依赖 |

### Step 4: 编码实现
按照以下顺序编写：

```html
<!-- 骨架结构 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>页面标题</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    .animate-fade-in { animation: fadeIn 0.6s ease-out; }
  </style>
</head>
<body>
  <!-- 导航栏 / Hero / 内容区 / 页脚 -->
  <script>/* 交互逻辑 */</script>
</body>
</html>
```

编码原则：
- 移动端优先，使用 sm/md/lg 断点
- 所有交互元素需有 hover / focus / active 状态
- 色彩使用 CSS 变量统一管理
- 动画使用 CSS @keyframes

### Step 5: 微调与验证
- [ ] 页面在不同宽度（375px / 768px / 1440px）下布局正常
- [ ] 所有链接和按钮悬停状态可见
- [ ] 中文字体使用系统字体栈
- [ ] 无控制台报错
- [ ] 语义化 HTML 标签

## 设计质量准则

| 维度 | 要求 | 反例 |
|------|------|------|
| 独特性 | 有视觉亮点 | 纯白背景默认字体 |
| 响应式 | 三断点适配 | 移动端溢出 |
| 性能 | 首屏 < 1s | 未使用的库 |
| 色彩 | 符合 WCAG AA | 浅灰底+白字 |

## 边界条件

| 场景 | 处理方式 |
|------|----------|
| 用户说"随便" | 默认极简风格，深蓝主色，Tailwind CDN 单页 |
| 用户提供设计稿 | 像素级还原，标注无法精确还原的部分 |
| 需要后端数据 | 用 mock 数据，标注替换位置 |
| 用户要求加动效 | 纯 CSS，不引入 GSAP 等重型库 |

## 资源参考
- Tailwind: https://tailwindcss.com/docs
- 配色: https://coolors.co
- 图标: https://heroicons.com / https://lucide.dev

## 产出格式
默认保存为单文件 HTML，所有 CSS/JS 内联或 CDN 引用，方便直接双击预览。
