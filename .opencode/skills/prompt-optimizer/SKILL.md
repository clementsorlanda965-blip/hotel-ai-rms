---
name: prompt-optimizer
description: 提示词优化——输入任意语言任意格式prompt，自动清洗垃圾词、翻译为英文、补必要缺失。不画蛇添足。输入"优化提示词""改写prompt""提示工程"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write
metadata:
  upstream: bananahub-ai/bananahub-skill
  language: zh-CN
---
## 做什么
优化用户输入的提示词，让它更清晰、更能被AI理解。

## 原则
1. 删除冗余的"请""帮我""能不能"等垃圾词
2. 把模糊描述变成具体指令
3. 补上缺失的上下文（格式、长度、风格）
4. 不画蛇添足，不改原意

## 工作流程

### Step 1: 输入分析
读取用户prompt，识别以下3类问题：

```python
issues = {
    "garbage_words": ["请", "帮我", "能不能", "好不好", "谢谢", "please", "help me"],
    "vague_phrases": ["改改", "看看", "弄一下", "搞搞", "处理", "整一下"],
    "missing_context": {
        "format": not ("json" in p or "表格" in p or "md" in p),
        "length": not ("字" in p or "页" in p or "sentence" in p),
        "style": not ("正式" in p or "专业" in p or "casual" in p),
    }
}
```

分析结果示例：
```
输入: "帮我把那个excel改改，加点公式"
→ 垃圾词: [帮, 把] | 模糊: [改改, 加点] | 缺失格式✓ 长度✗ 风格✗
```

### Step 2: 清洗转化
删除冗余词，将模糊描述重写为具体指令：

```python
# 模糊词 → 具体指令 映射
replace_map = {
    "改改": "修改 / 重构 / 优化",
    "看看": "审查 / 分析 / 评估", 
    "弄一下": "执行 / 实现 / 配置",
    "搞搞": "实现 / 开发 / 构建",
    "处理": "具体操作（如清洗数据/格式化）",
    "点": "定量描述（如3个/5行/10%增量）",
}
```

### Step 3: 补全输出
补充缺失的上下文信息：

```python
# 缺失补全规则
if not format:
    append("用Markdown表格输出" / "输出为J