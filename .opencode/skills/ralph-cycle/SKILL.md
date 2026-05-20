---
name: ralph-cycle
description: Ralph开发循环——AI代理自动化开发。从需求到代码到测试到部署的完整自动化循环。输入"ralph""自动开发""开发循环"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write Glob Edit
metadata:
  language: zh-CN
---

## 做什么
Ralph循环：AI代理自动化开发。需求拆解→编码→测试→提交，全程自动流转，无需人工介入。

## 适用场景
- 多页面网站开发（3页以上）
- 批量功能实现（5个以上独立功能）
- 自动化测试修复（无需人工分析场景）
- 大型重构任务（涉及10个以上文件）

## 工作流程

### Step 1: 需求拆解
将需求拆解为可执行的任务清单，每个任务格式如下：

```yaml
- id: TASK-001
  name: "用户登录接口实现"
  priority: high           # high / medium / low
  complexity: M            # S / M / L
  depends_on: []           # 依赖的任务ID列表
  files: ["src/auth.py"]   # 涉及的文件
  acceptance:              # 验收标准
    - "POST /api/login 返回 token"
    - "密码错误返回 401"
```

任务编排原则：
- 优先实现无依赖的任务（leaf nodes）
- 按依赖链顺序排列（拓扑排序）
- 标注复杂度用于预估时间

### Step 2: 环境准备
```bash
# 检查项目类型并安装依赖
ls package.json go.mod requirements.txt 2>/dev/null
npm install        # Node.js
pip install -r requirements.txt --break-system-packages  # Python
git init && git add -A && git commit -m "chore: init"
git checkout -b feat/ralph-auto
```

### Step 3: 循环实现（核心循环）
每个任务走完「实现→测试→提交」子循环：

```python
for task in sorted(tasks, key=lambda t: t.priority):
    for attempt in range(3):  # 最多重试3次
        implement(task)       # 实现功能代码
        run_tests(task)       # 运行关联测试
        if all_tests_pass():
            commit(task)      # git commit
            break
        elif attempt < 2:
            fix_and_retry(task)
        else:
            suspend(task)     # 暂停并标记
```

**子循环细则：**
- 实现：Write 创建/修改文件，每次修改后检查语法
- 测试：优先跑该任务单元测试（`pytest test_file.py -x -q`），而非全量
- 提交：Conventional Commits（`feat/fix/chore: description`）
- 修复：读取测试错误输出，定位到具体行号针对性修复

### Step 4: 集成验证
```bash
pytest -x --tb=short   # 全量测试
python3 -m build       # 构建检查
flake8 src/            # lint 检查
```

### Step 5: 交付总结
输出报告：任务总数/完成数/跳过数/测试通过率/变更文件数/提交次数/总耗时/失败记录。

## 边界条件

| 场景 | 处理方式 |
|------|----------|
| 需求模糊 | Step1 主动提问澄清，列出 2-3 个选项让用户选择 |
| 循环阻塞（同一任务重试 3 次） | 暂停该任务标记为 SKIPPED，继续下一个，最终报告列出 |
| 外部依赖不可用 | 使用 mock/stub 隔离，标注需要替换的真实服务 |
| 文件冲突（多任务改同一文件） | 按依赖顺序串行执行，不并行编辑 |
| 测试环境缺失 | 跳过测试步骤，标注"需人工运行测试" |
| 中间产物丢失 | 每完成一个任务 git commit |
| 大型项目（>100 文件） | 按模块分批执行，每批独立提交 |

## 资源参考
- 提交规范: Conventional Commits (https://www.conventionalcommits.org/)
- 测试框架: pytest / Jest / Mocha 按语言自动选择
