---
name: writing-plans
description: 编写实施计划——当有需求规格需要执行多步骤任务时，在编写代码前先制定详细的实施计划与检查点。输入"制定计划""实施方案""规划步骤"时触发。
license: MIT
compatibility: opencode
allowed-tools: Read Write Edit Bash Glob Grep WebFetch
metadata:
  audience: developer
  language: zh-CN
---

# 实施计划编写

> **资源引用**：测试用例见 `test-prompts.json`（3个测试场景：用户注册/数据导出/API微服务拆分），编写计划后模拟执行验证覆盖度。

## 概述

编写完整的实施计划，假设执行工程师对代码库零上下文了解。文档需包含：每个任务要改的文件、代码、测试、依赖文档、验证方式。DRY。YAGNI。TDD。频繁提交。

**开始声明：** "正在使用 writing-plans 技能编写实施计划。"

**保存位置：** `docs/plans/YYYY-MM-DD-<feature-name>.md`
- (用户偏好位置覆盖此默认值)

**范围检查：** 如果需求覆盖多个独立子系统，在编写计划前先拆分为独立计划，每个计划产出可独立测试交付的软件。

## 文件结构规划

定义任务前先列出所有新建/修改的文件及其职责：

- 每个文件一个清晰职责，文件越小越可靠
- 一起变更的文件放一起，按职责拆分而非技术层
- 现有代码库遵循既有模式，若文件过于臃肿可合理拆分
- 同一调用链的接口定义、实现、测试保持文件名对应

文件结构决定任务分解方式，每个任务应产出独立可理解的变更。

## 任务粒度

**每步一个操作（2-5分钟）：**
- "编写失败测试" → "运行验证失败" → "实现最简代码" → "运行验证通过" → "提交"

## 计划文档头部

```markdown
# [功能名称] 实施计划

> **注意：** 推荐使用 executing-plans 技能逐步执行，状态用 `- [ ]` 复选框追踪。

**目标：** [一句话描述]

**架构：** [2-3句技术方案]

**技术栈：** [关键库/框架]

---
```

## 任务结构

````markdown
### 任务 N：[组件名称]

**文件：**
- 创建：`exact/path/to/file.py`
- 修改：`exact/path/to/existing.py:123-145`
- 测试：`tests/exact/path/to/test.py`

- [ ] **步骤 1：编写失败测试**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **步骤 2：运行验证失败**

运行：`pytest tests/path/test.py::test_name -v`
预期：FAIL - "function not defined"

- [ ] **步骤 3：编写最简实现**

```python
def function(input):
    return expected
```

- [ ] **步骤 4：运行验证通过**

运行：`pytest tests/path/test.py::test_name -v`
预期：PASS

- [ ] **步骤 5：提交**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## 禁止占位符

每步必须包含执行所需的完整内容。以下为**计划失败**——永远不要这样写：
- "TBD" / "TODO" / "稍后实现" / "补充细节"
- "添加适当的错误处理" / "添加验证" / "处理边界情况"（无具体代码）
- "为以上代码写测试"（无具体测试代码）
- "与任务N类似"（重复代码，因为工程师可能乱序阅读）
- 只描述做什么但不展示如何做的步骤（代码步骤必须有代码块）
- 引用未在任何任务中定义的类型、函数或方法

## 记住
- 始终使用完整文件路径
- 每步的完整代码——如果步骤修改代码，展示代码
- 精确命令和预期输出
- DRY、YAGNI、TDD、频繁提交

## 异常处理

编写和执行计划过程中可能遇到以下异常：

| 异常场景 | 处理方式 |
|---------|---------|
| 用户拒绝计划范围 | 回到 Scope Check 重新界定范围，或拆分为更小子系统 |
| 测试框架不存在 | 检测 `pytest`/`jest`/`vitest` 可用性，缺失则提示安装命令 |
| 目标文件路径不存在 | 自动创建目录（`os.makedirs` / `mkdir -p`），路径无效则报错并建议 |
| Git提交冲突 | 提示 `git stash` 暂存变更，或开新分支重试 |
| 用户中途要求变更范围 | 暂停当前任务，回到 File Structure 修订计划，标记已完成步骤 |
| 依赖安装失败 | 提示具体错误和备选安装方式（pip/npm/pnpm），建议虚拟环境 |
| 计划文件保存路径冲突 | 追加时间戳后缀（`<name>-v2.md`），保留两份版本 |

## 自我审查

编写完整计划后，以全新视角对照需求逐项检查：

**1. 需求覆盖：** 逐条阅读需求规格，每条需求都能指向一个实现任务吗？列出缺口。

**2. 占位符扫描：** 搜索计划中所有"禁止占位符"章节提到的模式并修复。

**3. 类型一致性：** 后任务中使用的类型/方法签名/属性名与前面定义的一致吗？Task 3用`clearLayers()`但Task 7用`clearFullLayers()`属于bug。

发现问题直接修复，无需重新审查。如有需求规格找不到对应任务，补充任务。

## 执行交接

保存计划后，提供执行选择：

**"计划已保存至 `docs/plans/<filename>.md`。提供两种执行方式：**

**1. 逐任务执行（推荐）** — 在当前会话中使用 executing-plans 逐步执行，每步验证

**2. 手动执行** — 开发者自行遵循计划逐步实现

**请选择？"**

## 集成指引

本技能与以下技能配合使用：
- **brainstorming** — 编写计划前的需求分析
- **executing-plans** — 计划的分步执行引擎
- **subagent-driven-development** — 子代理并行开发
