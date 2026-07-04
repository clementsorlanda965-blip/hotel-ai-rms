# E:\工作AI — AI 智能体工作空间

## 语言规则（强制）
- **AI 的所有回答、分析、报告、对话必须使用中文**
- 代码注释和变量名可以用英文，但解释性文字必须中文
- 任何情况下不得用英文回复，除非用户明确要求

## 用户画像
- 中文用户，沟通语言：中文
- 酒店行业从业者 + 短视频/影视解说创作者
- 技术能力强，自主管理 AI agent 工具链（Cowork、Claude Code、OpenCode）
- 偏好：高效直接，批量任务全自动执行，不需要中途确认，全部完成后一次性汇报

## 工作目录结构
```
E:\工作AI\
├── .opencode\skills\              # 41 个技能（/command 指令）
├── HTML文件\                      # 归档的独立HTML网页文件
├── DOCX文件\                      # 归档的独立DOCX文档（已有分类的docx保留原处）
│
├── JianyingPro Drafts\            # 剪映专业版草稿文件（短视频项目）
├── JianyingPro Presets\           # 剪映预设配置
├── JianyingPro Materials\         # 剪映素材库
│
├── 酒店管理\                      # 酒店行业全部文件
│   ├── 会议纪要\                  #   会议纪要文档
│   ├── 数据分析\                  #   酒店BI报表、GOP分析、竞对分析
│   └── 证照文件\                  #   特种行业许可证等证照资料
│
├── 视频制作\                      # 视频中间文件（音频/临时视频/配图）
│   └── 中间文件\                  #   旧管线中间文件归档
├── 产出文案\                      # 最终视频解说文案
├── 原始文稿\                      # 原始素材/剧本
├── 剪映素材\                      # 剪映用到的图片素材
│
├── 代码脚本\                      # 独立Python脚本
├── 工具脚本\                      # 辅助工具脚本合集
│
├── 配置设置\                      # YAML/JSON配置文件
├── 文档资料\                      # Markdown使用指南/说明文档
│
├── 工具软件\                      # 第三方工具（ComfyUI、ffmpeg等）
│   ├── chrome-headless-shell\
│   ├── claude-ai-zh\
│   └── claude-skills\
│
├── charts\                        # 图表动效（视频用动画帧）
├── models\                        # AI模型文件
├── output\                        # 旧视频管线输出（保留兼容）
├── outputs\                       # 新管线输出（frames/audio/subtitles/video/html）
├── scripts\                       # 系统工具脚本
├── tools\                         # 大型工具包
│
├── 临时文件\                      # OCR文本、日志等临时文件
└── CLAUDE.md                      # 本文件——项目上下文
```

## 全局规则

### 🚨 永久禁止：不要 pip install notebooklm-py
COWORK 工作区的代理（localhost:3128）会拦截 PyPI 连接。
notebooklm-py 已安装在系统 Python 中，用 `python "C:\Users\周通\nblm.py"` 调用。
**任何情况下都不要尝试 pip install notebooklm-py、nlm、notebooklm-mcp 等包。**

### 🚨 永久禁止：不要用 shell 工具重启 DeepSeek 代理
- 在 shell tool 内用 `wmic process call create` 重启代理会把它**绑进 shell 的 job object**
- shell tool 退出后，job object 内的进程会被 SIGHUP 杀掉（日志可见 "got SIGHUP, refusing to die"）
- 即使写了信号处理函数，Windows 后续仍会强制终止 job object 内的所有进程
- **代理只能通过以下两种方式启动：**
  1. **注册表自启**（explorer.exe 启动，不在 job object 内）
  2. **`Start-Process -WindowStyle Hidden`**（PowerShell，验证可存活 11+ 小时）
- **禁止使用**：`wmic process call create "node ..."`、`Start-Process -NoNewWindow`、或任何在 shell tool 内直接 spawn 的方式
- 确保代理脱离 job object 的标准方法：`start /B` 使 node 成为 wmic/cmd 的孙进程

### 工作方式
- 批量任务全自动执行，不要中途停下来确认
- 一次性说明要求后全部执行完毕再汇报
- 所有输出文件保存到 E:\工作AI，不留 C 盘

### 🚨 强制：禁止重复回复（Anti-Loop）
- **禁止复述历史答案**：回答每条消息前先检查最近3轮对话。若用户重复提问，只回一句："刚才已回答过，答案不变。"
- **禁止追加追问**：回答完毕即止，不追加"好的老板""还有其他事吗""有需要再找我"等收尾话。
- **禁止纠正 Meta 反馈**：用户批评回复方式时只改不改解释，不分析原因、不道歉、不给改进方案。

### 📁 CLAUDE输出分类保存规则（所有版本强制遵守）

所有 Claude Code / Claude Web / Agent 生成的**任何文件**，必须按以下规则保存到 `E:\工作AI` 对应子目录，严禁随意堆放根目录或 C 盘。

#### 分类总表

| 输出类型 | 目标目录 | 适用场景 |
|---------|---------|---------|
| **视频成品 MP4** | `outputs/video/` | video-factory 合成的最终视频 |
| **视频中间帧** | `outputs/frames/` | 合成用的图片帧序列 |
| **音频配音** | `outputs/audio/` | TTS/edge-tts/ChatTTS 生成的配音 |
| **字幕文件** | `outputs/subtitles/` | 语音识别输出的 SRT/ASS |
| **配图/封面** | `outputs/images/` | image-generator 生成的配图 |
| **图表动画** | `charts/` | charts 管线生成的动画帧 |
| **PPT 文件** | `outputs/pptx/` | presentation 技能生成的 PPTX/HTML |
| **HTML 页面** | `outputs/html/` | frontend-design 生成的独立网页 |
| **脚本输出** | `outputs/scripts/` | 管线运行中产生的中间脚本 |
| **Hyperframes** | `outputs/hyperframes/` | 超帧动画文件 |
| | | |
| **解说文案** | `产出文案/` | content-writer/humanizer-zh 最终文案 |
| **原始文稿/剧本** | `原始文稿/` | 原始素材、剧本、参考资料 |
| **视频中间文件** | `视频制作/中间文件/` | 非最终的多媒体中间文件 |
| | | |
| **Python 脚本** | `代码脚本/` | Claude 生成的独立 .py 文件 |
| **工具脚本** | `工具脚本/` | 辅助批处理/Shell/PowerShell 脚本 |
| | | |
| **Word 文档** | `DOCX文件/` | document-word 生成的 .docx |
| **Excel 报表** | 按项目：酒店类→`酒店管理/数据分析/`，其他→`文档资料/` | document-excel 生成的 .xlsx |
| **PDF 文件** | `文档资料/` 或按项目子目录 | document-pdf 处理的 PDF |
| **Markdown 文档** | `文档资料/` | 指南、报告、说明文档 |
| **思维导图** | `文档资料/` | mind-map 生成的 Mermaid/PlantUML |
| **JSON/YAML/TOML** | `配置设置/` | 配置文件、技能配置、API 配置 |
| | | |
| **酒店-会议纪要** | `酒店管理/会议纪要/` | 酒店会议记录 |
| **酒店-数据分析** | `酒店管理/数据分析/` | BI 报表、GOP、RevPAR、竞对分析 |
| **酒店-证照文件** | `酒店管理/证照文件/` | 许可证、合同等法律文件 |
| **酒店-其他文档** | `酒店管理/` | hotel-docs 生成的其他酒店文档 |
| | | |
| **临时文件** | `临时文件/` | OCR 文本、日志、调试输出、缓存（定期清理） |
| **下载文件** | `临时文件/` | 从网络下载的素材（下载后移入对应目录） |

#### 执行规则

1. **任何生成文件必须指定完整路径**：`E:\工作AI\分类子目录\文件名.扩展名`
   - 禁止：只写文件名（默认存 C 盘 当前目录）
   - 允许：`E:\工作AI\产出文案\大明王朝解说_第1期.md`
   - 允许：`E:\工作AI\outputs/video/大明王朝解说_第1期.mp4`
2. **不存在的子目录先创建再写入**：使用 `mkdir -p "E:\工作AI\xxx"`（PowerShell: `New-Item -ItemType Directory -Force`）
3. **中间过程文件不遗留 C 盘**：Bash/Python 等临时生成的文件，运行完毕后自动清理或移到 E:\工作AI 对应目录
4. **项目专属输出另建子目录**：单个项目产生多个同类型文件时，在对应分类下建项目子目录
   - 例：`酒店管理/数据分析/2026年5月/`、`产出文案/大明王朝/`
5. **不确定分类时优先问用户**，不要自作主张放根目录

### 回复要求
1. 直接给结论，不要前置解释和铺垫。
2. 不要复述用户的问题，不要说"好的"、"明白了"、"让我来..."这类引导词。
3. 区分大小事项，简单问题一句话回答，复杂问题才展开。
4. 客观陈述事实和方案，不要"很棒的问题"、"非常聪明"这类捧场。
5. **答完即停，禁止追加废话**——给出答案后立刻结束，不得追加"好的老板"、"还有其他事吗"、"需要进一步帮助吗"等收尾客套。答案本身就是回复的终点。
6. 不确定就直接停下来问，不要瞎猜。

### 技能调用
- 在 Claude Code 交互模式中输入 `/命令` 直接调用技能
- 在命令行用 `claude -p "指令" --dangerously-skip-permissions` 全自动模式
- Agent 通过触发词自动启动，无需输入命令

## 所有指令清单（41个技能 + 内置命令）

### 内置命令（Claude Code 原生）

| 命令 | 中文注释 |
|------|---------|
| `/help` | 查看帮助信息 |
| `/clear` | 清除当前对话历史 |
| `/resume` | 恢复之前的会话 |
| `/login` | 登录 Claude 账号 |
| `/logout` | 退出登录 |
| `/init` | 初始化当前目录的 CLAUDE.md 项目文档 |
| `/review` | 审查一个 Pull Request |
| `/security-review` | 对待变更代码进行安全审查 |
| `/doctor` | 检查 Claude Code 更新器健康状态 |
| `/agents` | 管理后台运行的 Agent |
| `/ultrareview` | 启动云端多 Agent 代码审查 |

### 🎬 视频创作（6个）

| 命令 | 中文注释 |
|------|---------|
| `/video-factory` | **短视频合成引擎**——把配图+配音+字幕合成为最终 MP4，自动生成 BGM 和对齐时长 |
| `/content-writer` | **AI 文案写作**——脚本润色、爆款标题生成、封面文案、口播稿改写，专为影视解说设计 |
| `/humanizer-zh` | **中文去AI味**——检测并消除 24 种 AI 写作模式，让文案像人类自然书写 |
| `/image-generator` | **AI 配图/封面生成**——主力 ComfyUI 引擎，无 GPU 时自动降级 PIL 文字卡片 |
| `/audio-tts` | **TTS 语音合成配音**——edge-tts + ChatTTS 双引擎，40+ 中文音色可选 |
| `/speech-recognition` | **语音识别转字幕**——基于 FunASR，自动标点、时间轴对齐、输出 SRT |

### 🏨 酒店行业（3个）

| 命令 | 中文注释 |
|------|---------|
| `/hotel-docs` | **酒店管理文档生成**——SOP 标准操作流程、会议纪要、合同协议、培训手册、客诉记录 |
| `/hotel-bi` | **酒店 BI 报表**——一键生成 RevPAR/ADR/OCC/GOP 分析 Excel，含公式图表条件格式 |
| `/fb-cost-control` | **餐饮成本核算**——食谱成本卡、成本率分析、菜单工程波士顿矩阵、采购比价 |

### 📄 文档办公（5个）

| 命令 | 中文注释 |
|------|---------|
| `/document-word` | **Word 文档操作**——创建/读取/编辑/格式化 .docx，支持目录/表格/页眉页脚/模板替换 |
| `/document-excel` | **Excel 表格操作**——数据分析/公式计算/图表生成/格式化，支持 xlsx/csv/tsv |
| `/document-pdf` | **PDF 处理**——合并/拆分/文字提取/OCR识别/加密解密/水印/格式转换 |
| `/presentation` | **PPT 演示生成**——支持 HTML 动画、企业品牌、学术答辩、原生 PPTX，26种风格 |
| `/mind-map` | **思维导图生成**——转为 Mermaid/PlantUML 格式的流程图、组织架构图、时间线 |

### 💻 代码开发（11个）

| 命令 | 中文注释 |
|------|---------|
| `/code-doctor` | **代码诊断修复**——定位根因→写测试→修复→重构→审查→验证，全链路 |
| `/code-refactor` | **代码精简重构**——优化结构、提高可读性、降低复杂度，不改行为 |
| `/test-driven-development` | **测试驱动开发**——先写测试再写代码，红-绿-重构循环 |
| `/systematic-debugging` | **系统化调试**——遇到 bug 先定位根因，再提修复方案 |
| `/requesting-code-review` | **请求代码审查**——合目前验证代码质量和需求满足度 |
| `/receiving-code-review` | **接收审查反馈**——强调技术严谨性与独立验证，不盲目接受 |
| `/subagent-driven-development` | **子代理并行开发**——同时执行多个独立任务的实施计划 |
| `/ralph-cycle` | **Ralph 开发循环**——从需求到代码到测试到部署的完整自动化循环 |
| `/writing-plans` | **编写实施计划**——执行多步骤任务前先制定详细计划与检查点 |
| `/executing-plans` | **执行实施计划**——按编写好的计划逐步执行并阶段性审查 |

### 🕸️ 数据采集（2个）

| 命令 | 中文注释 |
|------|---------|
| `/web-scraper` | **网页数据采集**——基于 Firecrawl 引擎，支持单页/批量/结构化提取/搜索采集 |
| `/data-collector` | **数据采集 Agent**——抓取→结构化清洗→JSON/Excel 输出，整合 web-scraper + document-excel |

### 🎨 设计（3个）

| 命令 | 中文注释 |
|------|---------|
| `/frontend-design` | **前端界面设计**——生成 Web UI（网站/仪表盘/落地页/React组件/HTML/CSS） |
| `/ui-ux-pro-max` | **UI/UX 专业设计**——带可搜索设计数据库，提供设计参考与交互设计指导 |
| `/impeccable` | **像素级打磨**——设计审核/润色/动画/配色/排版等全方位 UI 优化 |

### ⚡ 元技能与自动化（12个）

| 命令 | 中文注释 |
|------|---------|
| `/brainstorming` | **头脑风暴**——创意工作前探索用户意图、需求与设计方案 |
| `/darwin-skill` | **达尔文技能自优化**——8维度评估打分，hill-climbing 自动优化+git版本控制 |
| `/writing-skills` | **编写技能文件**——创建新技能、编辑现有技能、部署前验证是否符合规范 |
| `/skill-manager` | **技能管理**——搜索/安装/管理/评估优化技能，访问 skills.sh 生态 |
| `/prompt-optimizer` | **提示词优化**——自动清洗垃圾词、翻译英文、补必要缺失，不画蛇添足 |
| `/dispatching-parallel-agents` | **并行任务派发**——2个以上互不依赖的独立任务时，最大化并行执行效率 |
| `/verification-before-completion` | **完成前验证**——宣称完成或修复前必须运行验证命令确认输出 |
| `/using-git-worktrees` | **Git 工作树隔离**——用 git worktree 创建独立工作环境开发新功能 |
| `/finishing-a-development-branch` | **分支收尾**——完成且测试通过后，提供合并/提PR/清理等结构化选项 |
| `/using-superpowers` | **超级能力指南**——元技能，指导发现和使用各项技能，优先调用 |
| `/planning-with-files-zh` | **文件规划系统**——Manus 风格的持久化 Markdown 规划，创建 task_plan.md/findings.md/progress.md，支持 /clear 后自动恢复会话上下文 |
| `/ruflo-automation` | **Ruflo 后台自动化**——蜂巢+记忆+Worker+Autopilot 实现无人值守工作流 |
| `/notebooklm` | **NotebookLM 深度研究**——上传文档、提问分析、生成音频/幻灯片/思维导图/抽认卡。**COWORK 环境无需 pip install**，用 `python "C:\Users\周通\nblm.py"` 调用 |

## NotebookLM 使用注意事项（COWORK 区域）

**不要 pip install notebooklm-py** — COWORK 环境的代理 localhost:3128 会阻止 PyPI 连接。
该包已安装在系统 Python 中，统一通过以下方式调用：

```bash
python "C:\Users\周通\nblm.py" list
python "C:\Users\周通\nblm.py" ask --notebook-id <id> --question "问题"
python "C:\Users\周通\nblm.py" source list --notebook-id <id>
```

### Agent（自动触发，无需输入命令）

| 触发词 | Agent | 中文注释 |
|--------|-------|---------|
| "做视频""一键出片""全流程视频" | video-producer | **单视频生产**——串联 content-writer→humanizer-zh→image-generator→audio-tts→speech-recognition→video-factory |
| "批量生产""矩阵号""批量做视频" | content-studio | **批量内容工厂**——并行生产多个视频，管理矩阵号内容 |
| "酒店情报""竞品分析""酒店监控" | hotel-analyst | **酒店数据智能**——web-scraper→hotel-bi→hotel-docs 采集分析出报告 |

### 命令行全自动模式

```bash
# 全自动执行一条任务（非交互模式，跑完退出）
claude -p "你的完整指令" --dangerously-skip-permissions --max-budget-usd 5

# 参数说明：
# -p "..."                         # 非交互模式，跑完自动退出
# --dangerously-skip-permissions   # 跳过所有"允许/拒绝"确认弹窗（全自动关键）
# --max-budget-usd N               # 设置费用上限，防止跑飞
# --add-dir E:\工作AI               # 指定工作目录（从 Windows 终端跑时需要）
# --permission-mode bypassPermissions  # 另一种跳过权限的方式
# --allowedTools "Bash Read Write"     # 限制 Claude 可用工具（安全用）
```

示例：
```powershell
# 从 Windows PowerShell 运行
cd E:\工作AI
claude -p "做一期大明王朝解说视频，全自动跑完所有流程" --dangerously-skip-permissions --max-budget-usd 3

# 批量任务
claude -p "批量做5期历史解说视频，主题自选，content-studio模式，全自动" --dangerously-skip-permissions --max-budget-usd 10
```

## 常用工作流

| 场景 | 管线 |
|------|------|
| **短视频制作** | content-writer → humanizer-zh → image-generator → audio-tts → speech-recognition → video-factory |
| **批量矩阵出片** | content-studio Agent（自动并行） |
| **酒店报表** | hotel-bi / document-excel |
| **酒店文档** | hotel-docs / document-word |
| **酒店竞品监控** | web-scraper → hotel-bi → hotel-docs |
| **数据采集** | web-scraper → data-collector → document-excel |
| **代码任务** | code-doctor / code-refactor / systematic-debugging |

## Claude Code 后端配置（DeepSeek V4）

### 架构
```
终端输入 claude → 永久环境变量 ANTHROPIC_BASE_URL=http://127.0.0.1:3206
                → Node.js 代理 (E:\claude-code\proxy.mjs, port 3206)
                → 注入 thinking:{type:"disabled"} (DeepSeek V4 必须关思考模式)
                → api.deepseek.com/anthropic/v1/messages
```

### 核心文件

| 文件 | 作用 | 端口 |
|------|------|------|
| `E:\claude-code\proxy.mjs` | Node.js 代理 v10，注入 thinking=disabled，转发到 DeepSeek | 3206 |
| `E:\claude-code\loop_proxy.cmd` | **循环自愈包装器**——无限 `start /B /WAIT node proxy.mjs` + 5s 重启，死后自动拉起 | - |
| `E:\claude-code\cert.pem` / `cert.key` | 自签名 X.509 证书（`api.anthropic.com` HTTPS 443） | 443 |
| `E:\claude-code\proxy-debug.log` | 运行时日志（心跳/请求/错误） | - |
| `E:\claude-code\start-proxy.ps1` | 代理管理（启/停/健康检查） | - |
| `E:\claude-code\claude.ps1` | PowerShell 启动入口，自动检测代理 | - |
| `E:\claude-code\claude.cmd` | CMD 启动入口（npm 原始版，不动） | - |
| `E:\claude-code\node_modules\@anthropic-ai\claude-code\bin\claude.exe` | Claude Code 本体 | - |
| `桌面\Claude Code.lnk` | 桌面快捷方式 → powershell → claude.ps1 | - |

### 永久环境变量（Windows 用户注册表）

| 变量 | 值 |
|------|-----|
| `ANTHROPIC_BASE_URL` | `http://127.0.0.1:3206` |
| `ANTHROPIC_AUTH_TOKEN` | `sk-2b1524f7492a4ccfab9ee924fc173397` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` |
| `CLAUDE_CODE_EFFORT_LEVEL` | `max` |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `claude-haiku-4-5` |

### 代理自启
- 注册表 `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run\DeepSeekProxy`
- 值：`cmd /c start /B E:\claude-code\loop_proxy.cmd`
- 登录后 explorer.exe 启动 loop → loop 内 `start /B /WAIT node proxy.mjs` → 死后 5s 内自动重启
- **架构层级**：`explorer → cmd /c start /B → loop_proxy.cmd (cmd) → start /B /WAIT → node proxy.mjs`
- 三层嵌套确保 node 是 explorer 的曾孙进程，完全脱离 shell job object

### 排障

| 症状 | 原因 | 修复 |
|------|------|------|
| Claude 连不上 / 超时 | 代理进程挂了 | `node E:\claude-code\proxy.mjs` |
| 返回空内容 | thinking 未禁用 | 确认 proxy.mjs 注入 thinking:disabled |
| 桌面双击闪退 | PS1 中文编码损坏 | 所有脚本已改用纯 ASCII |
| API 没钱了 | DeepSeek 账户余额不足 | 充值后重启代理 |

## Hermes Desktop 弹窗修复

Hermes 启动时会弹两个窗口：`powershell.exe` + `python.exe`（后端主进程）。修复方案：

### 修复方案

**1. python.exe → pythonw.exe**（改 `app.asar`）
- Hermes Electron 源码 `electron/main.cjs` 的 `getVenvPython()` 写死返回 `python.exe`
- 拆包 `app.asar` → 改 `'python.exe'` → `'pythonw.exe'` → 重新打包
- `pythonw.exe` 是 GUI 子系统，启动时无控制台窗口

**2. Electron spawn 全部加 windowsHide: true**（改 `app.asar`）
- `runGit()` — git 操作弹窗
- `spawn('curl', ...)` — 网络请求弹窗
- `spawn(backend.command, ...)` — 后端进程（双保险，pythonw 已经无窗口）
- `runStreamedUpdate()` — 升级脚本弹窗
- `spawn(py, ...)` 卸载 — 卸载脚本弹窗
- `spawn('cmd.exe', ...)` 打开浏览器 — 已有 `windowsHide: true`（原生自带）
- `spawn(runner, ...)` — 已有 `windowsHide: true`（原生自带）
- `spawn(updater, ...)` — 保留 `windowsHide: false`（升级安装器需要UI）

**3. sitecustomize.py 全局补丁（Popen + os.popen 双路拦截）**
- 两个位置各放一份 `sitecustomize.py`（Python 启动时自动加载给 `site` 模块）：
  - `venv\Lib\sitecustomize.py` — 主后端进程
  - `uv\python\...\Lib\sitecustomize.py` — uv 子进程
- 内容：劫持 `subprocess.Popen.__init__` + `os.popen`，对所有 Popen 调用注入 `CREATE_NO_WINDOW` 标志，自动把 `python.exe` 换 `pythonw.exe`

### 两个文件位置

| 文件 | 作用 |
|------|------|
| `C:\Users\周通\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\Lib\sitecustomize.py` | uv Python 的补丁 |
| `C:\Users\周通\AppData\Local\hermes\hermes-agent\venv\Lib\sitecustomize.py` | venv Python 的补丁 |
| `C:\Users\周通\AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked\resources\app.asar` | 修改后的 Electron 包（pythonw） |

### 升级后需重做

如果 Hermes 自更新覆盖了 `app.asar`，需要重新拆包改 `getVenvPython()`。
如果 uv Python 版本升级（新目录），需要在新 Python 的 `Lib/` 也放一份 `sitecustomize.py`。