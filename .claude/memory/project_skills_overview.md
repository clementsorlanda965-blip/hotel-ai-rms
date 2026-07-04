---
name: skills-overview
description: E:\工作AI 项目中全部 39 个 OpenCode 技能的完整索引，按分类组织
metadata: 
  node_type: memory
  type: project
  originSessionId: 486c4ec6-5be6-4d82-bcfd-8d3a15d935c5
---

# 工作AI 全部技能索引（共 40 个技能）

项目路径: E:\工作AI\.opencode\skills\

## 视频生产链（6个）

### video-factory — 短视频全自动生成
- **触发**: "做视频""生成视频""短视频"
- **功能**: 完整管线：选题→脚本→配图→TTS配音→字幕→BGM→合成 MP4
- **产出**: output/final.mp4

### audio-tts — TTS 语音合成配音
- **触发**: "配音""TTS""语音合成""朗读"
- **功能**: edge-tts（微软免费40+音色）和 ChatTTS（情感丰富需GPU）双引擎
- **产出**: MP3/WAV 到 outputs/audio/

### speech-recognition — 语音识别与字幕生成
- **触发**: "语音识别""字幕生成""ASR"
- **功能**: FunASR 模型，支持标准识别/时间轴对齐/批量处理
- **产出**: SRT 字幕到 outputs/subtitles/

### content-writer — AI 文案写作与脚本优化
- **触发**: "写文案""优化脚本""口播""标题"
- **功能**: 脚本润色/标题生成/封面文案/口播改写，贴合抖音/B站/小红书
- **产出**: outputs/script.json

### image-generator — AI 图片与海报封面生成
- **触发**: "生图""海报""封面""AI绘图"
- **功能**: ComfyUI 扩散模型主力，CPU降级 PIL 文字卡片
- **产出**: PNG/JPG 到 outputs/images/

### data-collector — 数据采集 Agent
- **触发**: "采集""爬取""抓数据""监控价格"
- **功能**: Firecrawl 引擎，五阶段管线：需求→采集→清洗→输出→监控
- **产出**: JSON/Excel 到 outputs/

### jianying-editor-skill — 剪映 AI 自动化剪辑
- **触发**: 自动化视频剪辑、生成草稿
- **功能**: JyWrapper API，素材导入/字幕/滤镜/特效/转场/关键帧/TTS/录屏/模板克隆
- **产出**: MP4/SRT/剪映项目草稿
- **路径**: E:\工作AI\jianying-editor-skill\SKILL.md

## 酒店经营链（4个）

### fb-cost-control — 餐饮成本核算
- **触发**: "成本核算""菜品成本""食品成本率""毛利分析""菜单工程"
- **功能**: 食谱成本卡/成本率分析/毛利排序/理论vs实际差异/菜单工程波士顿矩阵/采购比价
- **产出**: .xlsx 到 outputs/（6个Sheet：成本卡/成本率/毛利分析/差异分析/菜单工程/采购比价）

### hotel-bi — 酒店 BI 报表
- **触发**: "RevPAR""ADR""GOP""酒店报表""经营分析"
- **功能**: 日/周/月度经营分析，自动计算指标，含图表+条件格式
- **产出**: .xlsx 到 outputs/

### hotel-docs — 酒店管理文档
- **触发**: "SOP""会议纪要""合同""培训手册"
- **功能**: 自动生成各类酒店管理文档，全中文输出
- **产出**: 结构化 Word 文档

### web-scraper — 网页数据采集
- **触发**: "抓取""爬虫""竞品""OTA价格"
- **功能**: Firecrawl 引擎，单页/批量/搜索/结构化提取
- **产出**: JSON/Excel 到 outputs/

## 文档与演示（6个）

### presentation — PPT 演示全系列
- **触发**: "PPT""演示""幻灯片""汇报""答辩"
- **功能**: 6种输出模式，26种设计风格，14家企业品牌色
- **产出**: PPTX 到 outputs/pptx/

### mind-map — 思维导图生成
- **触发**: "思维导图""脑图""流程图""组织架构"
- **功能**: Mermaid 格式：mindmap/flowchart/graph/gantt/鱼骨图
- **产出**: .md 文件到 docs/

### document-excel — Excel 表格操作
- **触发**: "excel""表格""公式""图表""xlsx"
- **功能**: openpyxl 全操作：公式/图表/格式化/数据验证/透视表
- **产出**: .xlsx 到 outputs/

### document-word — Word 文档全操作
- **触发**: "word""docx""文档""手册""报告"
- **功能**: python-docx 全操作：标题/段落/表格/图片/页眉页脚/目录
- **产出**: .docx 到 outputs/docx/

### document-pdf — PDF 处理
- **触发**: "pdf""合并""拆分""OCR"
- **功能**: pypdf/pdfplumber/pytesseract，合并/拆分/提取/OCR/加密/转换
- **产出**: 到 outputs/

### frontend-design — 前端界面设计
- **触发**: "前端""网页""界面""UI""网站"
- **功能**: 单页HTML/React组件/PIL海报，反AI模板化
- **产出**: HTML/PNG 到 outputs/html/ 或 outputs/images/

## 开发工具链（5个）

### code-doctor — 代码诊断修复 Agent
- **触发**: "修bug""调试""检查代码""代码审查"
- **功能**: 五阶段：诊断→TDD测试→修复→重构→审查
- **产出**: 结构化修复摘要+测试结果

### test-driven-development — TDD 测试驱动开发
- **触发**: 实现功能/修复 bug/重构时
- **功能**: 红→绿→重构循环，铁律：没先写失败测试就没有生产代码
- **产出**: 代码+对应测试用例

### systematic-debugging — 系统化调试
- **触发**: 遇到 bug/测试失败/性能问题
- **功能**: 四阶段：根因调查→模式分析→假设测试→实施修复
- **产出**: 根因分析报告+修复代码

### code-refactor — 代码精简重构
- **触发**: "精简代码""重构""优化代码"
- **功能**: 不改行为前提下删除冗余/合并重复/改善命名/减少嵌套
- **产出**: 重构后代码+修改摘要

### requesting-code-review — 代码审查请求
- **触发**: "代码审查""review"
- **功能**: 6步标准化流程：git SHA→确认范围→独立子代理审查→分级展示→修复→确认
- **产出**: 审查报告(Critical/Important/Minor)+修复代码

## 元能力（5个）

### brainstorming — 头脑风暴与设计探索
- **触发**: "头脑风暴""设计方案""创意构思"
- **功能**: 结构化对话→设计方案→2-3种方案权衡→设计文档，HARD-GATE: 批准前不写代码
- **产出**: 设计文档到 docs/superpowers/specs/

### writing-plans — 编写实施计划
- **触发**: "制定计划""实施方案""规划步骤"
- **功能**: 2-5分钟粒度的详尽实施计划，含代码示例+精确命令
- **产出**: 计划文档到 docs/plans/

### dispatching-parallel-agents — 并行任务派发
- **触发**: "并行""多任务""同时处理"
- **功能**: 独立任务分派给多个子代理并行执行
- **产出**: 各子代理修复摘要+集成变更

### skill-manager — 技能管理
- **触发**: "创建技能""搜索技能""安装技能"
- **功能**: 技能全生命周期：创建/搜索GitHub生态/安装/合规检查
- **产出**: SKILL.md 文件

### verification-before-completion — 完成前验证
- **触发**: "验证""检查""确认完成""自检"
- **功能**: 铁律：无验证证据不得声称完成，禁止模糊表述
- **产出**: 带证据的完成声明

## 高级开发流程（9个）

### subagent-driven-development — 子代理驱动开发
- **触发**: "子代理""并行开发""多代理"
- **功能**: 计划拆解→独立子代理执行→两阶段审查（规格+代码质量）
- **产出**: 经过双重审查的完整代码

### ralph-cycle — Ralph 开发循环
- **触发**: "ralph""自动开发""开发循环"
- **功能**: 需求→任务列表→逐任务编码→测试→自动修复→git提交
- **产出**: 完整自动化开发交付

### executing-plans — 执行实施计划
- **触发**: "执行计划""实施方案"
- **功能**: 加载计划→审阅完整性→逐步执行→检查点确认→阻塞停询
- **产出**: 按计划逐步执行成果+完成摘要

### finishing-a-development-branch — 开发分支收尾
- **触发**: "完成开发""提交代码""合并分支"
- **功能**: 验证测试→检测工作空间→4选项（合并/PR/保留/丢弃）
- **产出**: 合并完成或 PR 创建或分支清理

### using-git-worktrees — Git 工作树隔离
- **触发**: "工作树""隔离开发""worktree"
- **功能**: 创建隔离 git worktree→安装依赖→基线测试
- **产出**: 隔离开发空间

### receiving-code-review — 接收代码审查反馈
- **触发**: "审查反馈""代码评审意见"
- **功能**: 阅读反馈→复述需求→验证→技术评估→逐项实施+测试
- **产出**: 经过验证的代码修改

### prompt-optimizer — 提示词优化
- **触发**: "优化提示词""改写prompt"
- **功能**: 清洗垃圾词/模糊→具体/补上下文/按需翻译
- **产出**: 优化后的清晰 prompt

### darwin-skill — 达尔文技能优化
- **触发**: "优化skill""skill评分""达尔文"
- **功能**: 8维评估量表+hill-climbing算法+git版本控制迭代优化
- **产出**: 优化后SKILL.md+results.tsv+成果卡片PNG

### writing-skills — 编写技能文件
- **触发**: "创建技能""编写skill""编辑技能"
- **功能**: TDD方式编写SKILL.md：RED基线测试→GREEN最小文档→REFACTOR反理性化
- **产出**: 经过TDD验证的SKILL.md

## UI/UX 设计（2个）

### impeccable — 卓越前端设计
- **触发**: 前端设计/重塑/审查/打磨/动画/颜色/排版/布局
- **功能**: 22个命令式子功能（Build/Evaluate/Refine/Enhance/Fix），OKLCH颜色体系
- **产出**: 生产级前端代码+设计系统文档

### ui-ux-pro-max — UI/UX 专业设计
- **触发**: "UI设计""UX设计""界面设计""交互设计"
- **功能**: 67种风格+96种配色+57种字体+99条UX指南+13个技术栈
- **产出**: 完整设计系统+UI代码

## 系统增强（3个）

### using-superpowers — 超级能力使用指南
- **触发**: 每次对话作为元技能自动触发
- **功能**: 技能路由中心，1%可能即调用，优先级：用户指令>技能规则>系统提示
- **产出**: 正确路由到对应技能

### ruflo-automation — Ruflo 后台自动化
- **触发**: "后台监控""无人值守""自动化""ruflo""swarm"
- **功能**: 记忆持久化/后台Worker/Autopilot/Swarm/模型路由降本/浏览器自动化
- **产出**: 持久化记忆+监控Worker+无人值守结果

## 新增: NotebookLM 集成 (nlm-skill)

| 项目 | 内容 |
|------|------|
| **Skill 路径** | `.opencode/skills/nlm-skill/` |
| **CLI 安装** | `pip install notebooklm-mcp-cli`（已安装 v0.6.10） |
| **MCP 配置** | `opencode.json` 中已添加 notebooklm MCP 服务 |
| **登录脚本** | `scripts/manual_nlm_login.py`（Win11 手动cookie提取） |
| **账号** | clementsorlanda965@gmail.com |
| **凭证位置** | `C:\Users\周通\.notebooklm-mcp-cli\profiles\default\` |
| **已有笔记本** | 餐饮标准(174源)、酒店学习(99源)、个人成长(72源) |
| **能力** | Audio Overview / 思维导图 / 幻灯片 / 报告 / 测验 / 问答 |
| **登录方式** | `python scripts/manual_nlm_login.py`（因 Win11 Issue#181 不能用 `nlm login`）|
| **注意事项** | 会话约 20 分钟过期，需重新运行登录脚本 |

## 自动路由规则
- **说具体操作**（配音/生成封面/抓数据）→ 直接触发对应 Skill
- **说复杂目标**（做一期视频/竞品分析/批量生产）→ 自动路由到对应 Agent，Agent 内部串联多个 Skill
