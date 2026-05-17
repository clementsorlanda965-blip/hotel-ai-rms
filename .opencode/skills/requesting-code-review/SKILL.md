---
name: requesting-code-review
description: 请求代码审查——完成任务或实现主要功能后、合并前，验证代码质量和需求满足度。输入"代码审查""审查代码""review"时触发。
---

# Requesting Code Review

**Purpose:** 在合并前或任务切换前，派发独立审查子代理检查代码质量与需求满足度。
**核心原则:** 早审查、常审查。

这6步流程在 `requesting-code-review/code-reviewer.md` 中有完整审查模板可复用。

Dispatch a code reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

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

**流程概述:** 获取范围→确认→派发→接收→处理→确认

| 步骤 | 输入 | 工具/操作 | 输出 |
|------|------|----------|------|
| 1.获取SHAs | git log | `git rev-parse HEAD~1` | BASE_SHA, HEAD_SHA |
| 2.确认范围 | SHAs | `git diff --stat {BASE}..{HEAD}` | 文件数/行数, 用户确认 |
| 3.派发审查 | 范围+模板 | Task tool | 审查结果 |
| 4.接收汇报 | 结果 | 格式化摘要 | 用户裁决方案 |
| 5.处理反馈 | 裁决 | Edit/Bash | 修复commit |
| 6.最终确认 | 修复状态 | 摘要汇报 | 用户决定 |

---

**Step 1 — 获取git SHAs:**
```bash
# 获取base和head
BASE_SHA=$(git rev-parse HEAD~1)   # 上一commit，或 origin/main
HEAD_SHA=$(git rev-parse HEAD)      # 当前HEAD

# 查看diff统计（用于Step 2确认范围）
git diff --stat ${BASE_SHA}..${HEAD_SHA}
```

**Step 2 — 确认审查范围（检查点）：**
- 读取 `git diff --stat` 输出
- 向用户呈现: "即将审查 ${BASE_SHA:0:7}..${HEAD_SHA:0:7} (共X个文件, Y行改动)。审查范围是否正确？"
- 用户可: 确认 / 缩小范围 / 更换base
- 等待用户决策后再派发

**Step 3 — 派发审查子代理:**
1. 打开模板文件 (路径: `requesting-code-review/code-reviewer.md`, 同目录可用 `Read` 读取)
2. 填充4个占位符:
   - `{DESCRIPTION}` — 实现概要
   - `{PLAN_OR_REQUIREMENTS}` — 需求/计划路径或文本
   - `{BASE_SHA}` — 起始commit
   - `{HEAD_SHA}` — 结束commit
3. 使用 Task tool (`general-purpose`类型) 派发，prompt填入完整填充后的模板内容
4. 模板包含: 代码质量/架构/测试/生产就绪度全方位检查 + 三级严重度分类 + 明确合并结论

**Step 4 — 接收审查结果（检查点）:**
- 读取子代理返回的 Strengths / Issues / Assessment
- 格式化呈现给用户:
```
审查结果摘要：
  Critical: X
  Important: Y
  Minor: Z
  评估结论: [Ready to merge / With fixes / No]
```
- 询问用户: "是否按以下方案处理？修复Critical → 修复Important → Minor暂缓"

**Step 5 — 处理反馈:**
- Critical: 立即修复（使用Edit工具修改代码，Bash运行测试）
- Important: 在继续前修复
- Minor: 记录待后续处理
- 如有争议: 用技术理由反驳，展示代码或测试证明

**Step 6 — 修复后确认（最终检查点）:**
- 生成修复摘要（改了哪些文件、解决了哪些问题）
- 询问用户: "修复完成。是否需再次审查或直接继续？"

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

// Step 1: Get SHAs
BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)
// Step 2: Get diff stats
git diff --stat ${BASE_SHA}..${HEAD_SHA}

You: "即将审查 a7981ec..3df7661 (共4个文件, 86行改动)。审查范围是否正确？"
User: "确认"

// Step 3: Dispatch
[Task tool: general-purpose]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

// Step 4: Receive results
[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: "审查结果：Critical=0, Important=1, Minor=1。建议修复Important后继续。同意？"
User: "同意"

// Step 5: Fix Important issue
// Step 6: Confirm
You: "已修复进度提示。是否需再次审查或继续？"
User: "继续"

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
