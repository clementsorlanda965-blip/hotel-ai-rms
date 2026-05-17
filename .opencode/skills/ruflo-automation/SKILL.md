---
name: ruflo-automation
description: >-
  Ruflo后台自动化——利用蜂巢(Swarm)、记忆(AgentDB)、后台Worker、Autopilot实现无人值守的AI工作流。
  支持定时监控、批量任务、跨会话记忆、模型路由降本。输入"后台监控""无人值守""自动化""ruflo""蜂巢""swarm""autopilot"时触发。
  所有文字输出为中文。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write
metadata:
  language: zh-CN
---

## 强制规则
所有文字输出必须是中文。操作本技能需要 Ruflo MCP 已注册（当前环境已就绪）。

## 做什么
将 Ruflo 的后台自动化能力注入当前工作流：记忆持久化、后台 Worker、Autopilot 无人值守、模型路由降本、蜂巢协同。

## 检查点总览（每次操作前必确认）

| # | 操作 | 检查点 | 确认内容 |
|---|------|--------|---------|
| 1 | 存入记忆 | 保存前确认 | key 是否按 `{领域}:{主题}:{日期}` 规范命名？内容是否脱敏？ |
| 2 | 启动 Worker | 派发前确认 | trigger/context/background 参数是否正确？频率是否 ≤1次/时？ |
| 3 | 启用 Autopilot | 启用前确认 | 任务数量是否 >3？异常重试策略是否设置？ |
| 4 | 蜂巢协同 | 初始化前确认 | topology 拓扑结构是否合理？maxAgents 是否 ≤ 可用配额？ |
| 5 | 模型路由 | 路由前确认 | 是否确认任务复杂度与模型强弱匹配？

## 快速启动

| 你说 | 触发 | 效果 |
|------|------|------|
| "记住这个" | `memory_store` | 关键数据跨会话保存 |
| "之前那个..." | `memory_search` | 语义搜索历史 |
| "开始监控" | `hooks_worker-dispatch` | 启动后台 Worker |
| "让它自己跑" | `autopilot_enable` | 无人值守执行 |
| "编队一起做" | `swarm_init` | 多 Agent 蜂巢协同 |

---

## 一、记忆系统（Memory & AgentDB）

### 存入记忆
> **检查点①：** 确认 key 命名规范、内容无敏感信息后再执行。

```python
# 每次重要产出后自动调用
memory_store(
    key="video:大明王朝第3集",
    value="标题: 改稻为桑的阴谋 | 脚本: outputs/script.json | 成品: outputs/video/final.mp4",
    namespace="video-production",
    tags=["大明王朝", "历史解说"]
)
```

### 检索记忆
```python
# 下次做同系列时先查历史
memory_search(
    query="大明王朝解说脚本 历史剧开场方式",
    namespace="video-production",
    smart=True  # 智能扩展+多样性重排
)
```

### 跨会话恢复
```python
# 新会话开始时恢复上下文
agentdb_context-synthesize(query="上次视频做到哪了")
agentdb_session-start(sessionId="video-production-20250516")
```

---

## 二、后台 Worker（12 种触发器）

| Worker | 触发条件 | 你的场景 |
|--------|---------|---------|
| `monitor` | 手动派发 / 定时 | 每日爬取酒店价格 |
| `audit` | 文件变更 | 检测经营数据异常 |
| `optimize` | 手动派发 | 优化脚本性能 |
| `ultralearn` | 任务完成后 | 学习成功模式 |
| `testgaps` | 代码变更 | 找测试覆盖盲区 |

### 创建酒店价格监控 Worker
> **检查点②：** 确认 trigger/context/background 参数无误，监控频率 ≤1次/时。

```python
hooks_worker-dispatch(
    trigger="monitor",
    context="上海外滩商圈五星酒店OTA价格",
    background=True  # 非阻塞
)
```

### 创建异常检测 Worker
```python
hooks_worker-dispatch(
    trigger="audit",
    context="outputs/hotel_raw_data.json 价格波动超15%告警",
    background=True
)
```

---

## 三、Autopilot 无人值守

### 批量视频生产
> **检查点③：** 确认任务数 >3、异常重试策略已设置后再启用。

```python
autopilot_enable()
# 然后派发任务：
content-studio → "做10期大明王朝解说"
# → 自动拆解 → 并行执行 → 异常重试 → 完成汇总
# 可以关电脑离开
```

### 查看进度
```python
autopilot_progress()  # 当前任务进度
autopilot_status()    # autopilot 运行状态
autopilot_log(last=10)  # 最近10条事件
```

### 停止
```python
autopilot_disable()  # 关闭无人值守模式
```

---

## 四、蜂巢协同（Swarm / Hive-Mind）

### 初始化视频生产蜂巢
> **检查点④：** 确认 topology 拓扑结构、maxAgents 不超过可用配额。

```python
swarm_init(
    topology="hierarchical",  # 层级结构：一个Queen指挥多个Worker
    maxAgents=5
)
```

### 加入 Agent
```python
hive-mind_join(agentId="video-producer", role="worker")
hive-mind_join(agentId="image-generator-agent", role="specialist")
```

### 共享记忆
```python
hive-mind_memory(
    action="set",
    key="video_style_template",
    value='{"hook_style":"悬念悬念","music":"低沉","pace":"快速"}'
)
```

---

## 五、模型路由降本

### 自动路由
> **检查点⑤：** 确认任务复杂度与选定的模型强弱匹配后再路由。

```python
# 根据任务复杂度自动选模型
hooks_model-route(task="配音参数微调")    # → 弱模型（低价）
hooks_model-route(task="历史剧脚本创作")  # → 强模型（高质）
```

### 查看费用
```python
hooks_metrics(period="7d")  # 最近7天token消耗
```

---

## 六、浏览器自动化

### 录制 OTA 操作流程
```python
browser_session_record(
    url="https://hotel.ctrip.com/hotel/shanghai",
    task="搜索上海外滩五星酒店 → 提取前10家价格"
)
# 返回 session ID
```

### 每日重放
```python
browser_session_replay(
    session="<session_id>",
    derive=True  # 生成新会话，保留模板
)
```

---

## 七、完整自动化流水线示例

### 酒店周报全自动
```
周一 9:00 →
  hooks_worker-dispatch (monitor) → 爬取竞品价格
  → memory_store 存入本周数据
  → neural_predict 预测下周趋势
  → hotel-analyst 生成周报
  → aidefence_scan 隐私检查
  → memory_store 更新分析历史
```

### 视频批量无人生产
```
用户: "做10期大明王朝" →
  autopilot_enable
  → content-studio 拆解任务
  → 并行派发 general 子代理
  → progress_check 追踪进度
  → 全部完成后 memory_store 汇总
  → autopilot_disable
```

## 注意事项
1. Autopilot 适合 >3 个任务的批量场景，单任务不建议
2. memory_store 的 key 建议用 `{领域}:{主题}:{日期}` 格式
3. Worker 监控频率不要超过每小时一次，避免反爬
4. 蜂巢协同需要所有 Agent 使用相同的模型才能共享上下文
