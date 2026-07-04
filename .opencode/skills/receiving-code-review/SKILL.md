---
name: receiving-code-review
description: 接收代码审查反馈——收到代码审查反馈后、实施建议前使用，强调技术严谨性与独立验证，而非盲目接受。输入"审查反馈""代码评审意见"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Grep Glob Edit Write
metadata:
  language: zh-CN
---

# Code Review Reception

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## 工作流程

### Step 1: READ — 完整阅读反馈
完整阅读所有审查反馈，不做任何反应。不要边读边改。

### Step 2: UNDERSTAND — 用自己的话复述需求
对每条反馈，在自己脑中用技术语言重新表述一遍。不确定的标记为待澄清。

```
✅ 理解清晰 → 标记为"可直接实施"
❌ 理解模糊 → 标记为"需澄清"，暂不实施
```

### Step 3: VERIFY — 对照代码库验证
对每条建议进行技术验证，确认在当前代码库中是否合理：

```python
# 每条反馈的验证清单
for feedback in review_items:
    check = {
        "技术上是否正确": verify_technically(feedback),
        "是否破坏现有功能": check_backward_compat(feedback),
        "当前实现有合理原因": check_implementation_reason(feedback),
        "reviewer理解完整上下文": check_reviewer_context(feedback),
    }
    if all(check.values()):
        mark_as_accepted(feedback)
    else:
        mark_as_contested(feedback)
```

### Step 4: EVALUATE — 技术评估
对每条反馈的最终裁决：

| 评估结果 | 行动 |
|----------|------|
| 正确且适用 | 标记为接受，准备实施 |
| 正确但不适用当前场景 | 记录理由，暂不修改 |
| 技术上不正确 | 准备推回，附技术证据 |
| 无法判断 | 升级给决策者 |

### Step 5: RESPOND — 技术确认或推回
- **接受** → 简洁确认："已理解。[简要复述]，准备修改"
- **推回** → 用技术理由，不用防御性语言
- **需澄清** → 具体指出哪条不清楚

### Step 6: IMPLEMENT — 逐项实施
按照优先级逐项修改，每项改完单独测试：

```
项目顺序: 阻塞/安全问题 > 简单修复(拼写/导入) > 复杂重构 > 风格建议
```

## Forbidden Responses

**NEVER:**
- "You're absolutely right!" (explicit CLAUDE.md violation)
- "Great point!" / "Excellent feedback!" (performative)
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong
- Just start working (actions > words)

## Handling Unclear Feedback

```
IF any item is unclear:
  STOP - do not implement anything yet
  ASK for clarification on unclear items

WHY: Items may be related. Partial understanding = wrong implementation.
```

**Example:**
```
your human partner: "Fix 1-6"
You understand 1,2,3,6. Unclear on 4,5.

❌ WRONG: Implement 1,2,3,6 now, ask about 4,5 later
✅ RIGHT: "I understand items 1,2,3,6. Need clarification on 4 and 5 before proceeding."
```

## Source-Specific Handling

### From your human partner
- **Trusted** - implement after understanding
- **Still ask** if scope unclear
- **No performative agreement**
- **Skip to action** or technical acknowledgment

### From External Reviewers
```
BEFORE implementing:
  1. Check: Technically correct for THIS codebase?
  2. Check: Breaks existing functionality?
  3. Check: Reason for current implementation?
  4. Check: Works on all platforms/versions?
  5. Check: Does reviewer understand full context?

IF suggestion seems wrong:
  Push back with technical reasoning

IF can't easily verify:
  Say so: "I can't verify this without [X]. Should I [investigate/ask/proceed]?"

IF conflicts with your human partner's prior decisions:
  Stop and discuss with your human partner first
```

**your human partner's rule:** "External feedback - be skeptical, but check carefully"

## YAGNI Check for "Professional" Features

```
IF reviewer suggests "implementing properly":
  grep codebase for actual usage

  IF unused: "This endpoint isn't called. Remove it (YAGNI)?"
  IF used: Then implement properly
```

**your human partner's rule:** "You and reviewer both report to me. If we don't need this feature, don't add it."

## Implementation Order

```
FOR multi-item feedback:
  1. Clarify anything unclear FIRST
  2. Then implement in this order:
     - Blocking issues (breaks, security)
     - Simple fixes (typos, imports)
     - Complex fixes (refactoring, logic)
  3. Test each fix individually
  4. Verify no regressions
```

## When To Push Back

Push back when:
- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Legacy/compatibility reasons exist
- Conflicts with your human partner's architectural decisions

**How to push back:**
- Use technical reasoning, not defensiveness
- Ask specific questions
- Reference working tests/code
- Involve your human partner if architectural

**Signal if uncomfortable pushing back out loud:** "Strange things are afoot at the Circle K"

## Acknowledging Correct Feedback

When feedback IS correct:
```
✅ "Fixed. [Brief description of what changed]"
✅ "Good catch - [specific issue]. Fixed in [location]."
✅ [Just fix it and show in the code]

❌ "You're absolutely right!"
❌ "Great point!"
❌ "Thanks for catching that!"
❌ "Thanks for [anything]"
❌ ANY gratitude expression
```

**Why no thanks:** Actions speak. Just fix it. The code itself shows you heard the feedback.

**If you catch yourself about to write "Thanks":** DELETE IT. State the fix instead.

## Gracefully Correcting Your Pushback

If you pushed back and were wrong:
```
✅ "You were right - I checked [X] and it does [Y]. Implementing now."
✅ "Verified this and you're correct. My initial understanding was wrong because [reason]. Fixing."

❌ Long apology
❌ Defending why you pushed back
❌ Over-explaining
```

State the correction factually and move on.

## 边界条件处理

### 多条反馈相互矛盾
```
IF 两条反馈建议相互矛盾（如"加X"和"删X相关代码"）:
  1. 先别动手
  2. 向 reviewer 澄清矛盾点："这两条建议似乎指向不同方向：[引原文]。能否协调？"
  3. 如 reviewer 不及时回复，升级给你的 human partner 决策
```

### 反馈列表过长（10+项）
```
IF 反馈项 ≥ 10:
  1. 先按优先级分类：阻塞 > 简单修复 > 复杂重构 > 风格建议
  2. 向你的 human partner 摘要汇报："共[N]条，其中[M]条阻塞，[K]条简单。建议先修阻塞和简单的？"
  3. 获得确认后分批实施，每批不超过5项
```

### 多位 reviewer 意见冲突
```
IF 来自不同 reviewer 的意见冲突:
  1. 不自行裁决
  2. 向你的 human partner 汇报："Reviewer A 说[X]，Reviewer B 说[Y]。建议如何处理？"
  3. 按指示执行
```

### Reviewer 无法提供澄清
```
IF 发出澄清请求后 reviewer 超过24h未回复（或不可达）:
  1. 按你当前对需求的理解给出保守方案（最少改动）
  2. 标注为"待 reviewer 确认"
  3. 向你的 human partner 说明情况
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | State requirement or just act |
| Blind implementation | Verify against codebase first |
| Batch without testing | One at a time, test each |
| Assuming reviewer is right | Check if breaks things |
| Avoiding pushback | Technical correctness > comfort |
| Partial implementation | Clarify all items first |
| Can't verify, proceed anyway | State limitation, ask for direction |

## 边界条件速查表

| 场景 | 处理方式 |
|------|----------|
| **两条反馈相互矛盾** | 先不动手，向 reviewer 澄清矛盾点；如不及时回复，通知用户决策 |
| **反馈列表过长（≥10项）** | 按优先级分类（阻塞→简单→复杂→风格），向用户摘要汇报后分批实施（每批≤5项） |
| **多位 reviewer 意见冲突** | 不自行裁决，向用户汇报冲突点请用户决策 |
| **Reviewer 24h内未回复澄清** | 按最少改动方案实施，标注"待确认"，向用户说明情况 |
| **建议涉及修改架构决策** | 暂停实施，与用户讨论后再继续 |
| **建议不适用当前代码库** | 给出技术理由推回，引用现有代码/测试作证据 |
| **推回后发现错了** | 简洁更正："