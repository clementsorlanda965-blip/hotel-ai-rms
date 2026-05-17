---
name: requesting-code-review
description: 请求代码审查——完成任务或实现主要功能后、合并前，验证代码质量和需求满足度。输入"代码审查""审查代码""review"时触发。
---

# Requesting Code Review

Dispatch a code reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Checkpoint — confirm review scope:**
- Present: "即将审查 BASE..HEAD (共X个文件, Y行改动)。审查范围是否正确？"
- User can: confirm / narrow scope / change base
- Wait for user decision before dispatching

**3. Dispatch code reviewer subagent:**

Use Task tool with `general-purpose` type, fill template at `code-reviewer.md`

**Placeholders:**
- `{DESCRIPTION}` - Brief summary of what you built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit

**4. Receive results — checkpoint:**

Present reviewer output to user:
```
审查结果摘要：
  Critical: X
  Important: Y
  Minor: Z
  评估结论: [Ready to merge / With fixes / No]
```
Ask user: "是否按以下方案处理？修复Critical→修复Important→Minor暂缓"

**5. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

**6. After fixes — final checkpoint:**
- Present fix summary to user
- Ask: "修复完成。是否需再次审查或直接继续？"

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code reviewer subagent]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from docs/superpowers/plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each task or at natural checkpoints
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Error Recovery

**No git history (no base commit):**  "无可用base commit。是否以当前HEAD作为基准进行一次性审查？"
**No changes between SHAs (empty diff):**  "base和head之间无差异，无需审查。是否检查commit顺序？"
**Diff too large (>500 files):**  拆分审查：按模块分组，每组单独派发审查子代理，汇总结果。
**Reviewer subagent unavailable:**  Fallback到手动审查：列出diff关键文件，逐文件自我审查后向用户报告。
**Conflicting feedback across reviews:**  按Critical→Important→Minor优先级裁决，Critical歧义时请示用户。
**User disagrees with review:**  记录用户理由，标记为"用户裁决跳过"，不强制修改。

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: requesting-code-review/code-reviewer.md
