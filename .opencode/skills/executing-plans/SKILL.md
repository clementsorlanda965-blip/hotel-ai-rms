---
name: executing-plans
description: 执行实施计划——当有编写好的实施计划需要在独立会话中逐步执行，并进行阶段性检查点审查。输入"执行计划""实施方案"时触发。
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## Example Workflow

```
User: "执行 docs/deployment-plan.md 的实施计划"

You: [Read plan] "已读取部署计划，包含3个任务。"
     [Present review] "计划完整，是否开始按顺序执行？"
User: "开始"

You: [Task 1: Setup environment]
     "正在执行任务1..."
     [After task 1] "任务1完成，验证通过。是否继续下一个任务？"
User: "继续"
...
```

**Note:** Tell your human partner that Superpowers works much better with access to subagents. The quality of its work will be significantly higher if run on a platform with subagent support (such as Claude Code or Codex). If subagents are available, use superpowers:subagent-driven-development instead of this skill.

## The Process

### Step 1: Load and Review Plan
1. Read plan file — use `Read` tool on the plan path
2. Review critically — check:
   - Are all prerequisites installed/available?
   - Is each step concrete enough to execute?
   - Are verification steps specified?
   - Are file paths and commands correct?
3. **Checkpoint:** Present your review summary to the user and ask for confirmation before starting
   - "已审阅计划，发现X个问题/计划完整。是否开始执行？"
   - Wait for explicit user approval (Y/n) before proceeding
4. If concerns: Raise them with your human partner before starting, wait for resolution
5. If no concerns and user confirmed: Create TodoWrite (or markdown checklist) and proceed

### Step 2: Execute Tasks

For each task:
1. Mark as in_progress in your checklist
2. Follow each step exactly (plan has bite-sized steps) — use:
   - `Read` to read source files before modifying
   - `Edit` to make targeted changes (preferred over full rewrites)
   - `Write` only for new files
   - `Bash` for commands (npm install, pytest, git, etc.)
3. Run verifications as specified (tests, lint, manual checks)
4. **Checkpoint after each task:** Present task result summary, ask user to confirm before next task
   - "✅ 任务X完成，验证通过。是否继续下一个任务？"
   - "❌ 任务X验证失败：[原因]。如何继续？重试/跳过/修改计划？"
5. Mark as completed after user confirmation

### Step 3: Complete Development

After all tasks complete and verified:
1. **Checkpoint:** Present completion summary to user and ask for confirmation
   - "所有任务已完成。是否调用 finishing-a-development-branch 进行收尾？"
   - Wait for explicit user approval
2. Announce: "I'm using the finishing-a-development-branch skill to complete this work."
3. **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
4. Follow that skill to verify tests, present options, execute choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Checkpoint for blockers:**
1. Describe the blocker clearly (what happened, what you tried)
2. Present 1-2 proposed solutions to the user
3. Ask user for guidance before proceeding
4. Wait for explicit user decision

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **superpowers:using-git-worktrees** - Ensures isolated workspace (creates one or verifies existing)
- **superpowers:writing-plans** - Creates the plan this skill executes
- **superpowers:finishing-a-development-branch** - Complete development after all tasks
