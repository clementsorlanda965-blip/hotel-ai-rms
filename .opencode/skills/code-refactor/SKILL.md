---
name: code-refactor
description: 代码精简重构——优化结构、提高可读性、降低复杂度不改行为。输入"精简代码""重构""优化代码"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Grep Glob Edit Write
metadata:
  language: zh-CN
---

## 做什么
精简冗余代码、提高可读性、降低复杂度，**不改行为**。适用于 Python / JavaScript / TypeScript / 等主流语言。

## 核心规则
- **不改功能** — 输入输出行为零变化
- **删无用** — 未用变量、死代码、空函数
- **合并重复** — DRY原则，提取公共逻辑
- **改善命名** — 模糊命名改为意图自描述
- **减少嵌套** — 提前返回、反转条件、拆分函数
- **不加注释** — 代码自解释，不额外加注释

## 工作流程

### Step 1: 读取分析
使用 `Read` 读取文件，逐行扫描以下问题模式：

```python
# 待检测的问题清单
issues = {
    "unused_vars": [],    # 定义了但未使用的变量
    "dead_code": [],      # return 后不可达的代码
    "deep_nesting": [],   # 缩进超�