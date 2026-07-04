---
name: verification-before-completion
description: 完成前验证——宣称工作完成或问题修复前必须运行验证命令并确认输出，先验证再断言。输入"验证""检查""确认完成""自检"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write Grep Glob
metadata:
  language: zh-CN
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## 工作流程（Gate Function）

### Step 0: 预确认
向用户呈现计划执行的验证命令："我将运行 [命令] 验证 [断言]。确认执行？"
等待用户明确同意后再继续。

### Step 1: 识别验证命令
确定能证明该断言的完整命令：

```python
# 验证命令对照
verification_map = {
    "测试通过": "python -m pytest tests/ -x --tb=short -q",
    "代码风格": "flake8 src/ --max-line-length=100",
    "编译成功": "python -c \"import ast; ast.parse(open('main.py').read())\"",
    "功能正确": "python -c \"from module import func; assert func(1) == 2\"",
    "构建通过": "npm run build",
}
```

### Step 2: 执行验证
运行完整命令，查看全部输出和退出码：

```bash
# 示例：验证测试
python -m pytest tests/ -x --tb=short -q
# 必须读取完整输出（不仅看退出码），确认具体失败项
```

### Step 3: 核对结果
- 退出码 = 0 ✅ → 检查输出中是否有"FAILED"、"Error"、"failure"等关键词
- 退出码 ≠ 0 ❌ → 输出实际状态（含失败原因），不得声称通过

### Step 4: 作出断言
- 验证通过 → 附证据陈述："测试通过 (34/34 pass, exit 0)"
- 验证失败 → 陈述实际状态："2项测试失败：[描述]，需修复"

Skip any step (0-4) = lying, not verifying

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## 边界条件

| 场景 | 处理方式 |
|------|----------|
| **验证命令本身不存在（如未安装 pytest）** | 安装对应工具或寻找替代验证方式（如 python -m unittest） |
| **验证命令耗时过长（>30秒）** | 设置超时，如果超时先报告"验证超时"，询问用户是否继续等待 |
| **无可用测试/验证命令*