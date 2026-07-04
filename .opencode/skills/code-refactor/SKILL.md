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
精简冗余代码、提高可读性、降低复杂度，不改行为。适用于 Python/JavaScript/TypeScript/Go 等主流语言。

## 核心规则
- 不改功能逻辑
- 删无用变量和死代码
- 合并重复代码块
- 改善命名（变量/函数/类）
- 减少嵌套深度（提前 return / 卫语句）
- 拆分长函数（>30行）
- 提取魔法数字为常量
- 简化复杂条件表达式
- 不加注释（好代码自解释）

## 工作流程

### Step 1: 读取分析
使用 Read 读取目标文件，扫描以下问题并标记行号：

```python
issues = {
    "未用变量":     re.findall(r'(\w+)\s*=\s*.*(?:\n(?!\1))', text),
    "死代码":       ['#|//|/*'] + 函数定义后未调用的代码,
    "深嵌套":       [行 for 行 in text if 行.count('    ') > 3],
    "长函数":       [函数 for 函数 in functions if len(函数.lines) > 30],
    "魔法数字":     re.findall(r'(?<!=)\b\d{2,}\b(?!["\'])', text),
    "复杂条件":     [行 for 行 in text if 条件中 and/or/not 嵌套超过2层],
}
```

### Step 2: 制定重构策略

| 问题类型 | 重构手法 | 适用场景 |
|----------|----------|----------|
| 未用变量 | 删除 | 赋值后未引用的变量 |
| 死代码 | 删除 | 注释掉的代码、不可达分支 |
| 重复块 | 提取函数 | 3行以上相似度>80%的代码 |
| 深嵌套 | 卫语句 / 提前返回 | if 嵌套 > 3 层 |
| 长函数 | 拆分 | 单一函数 > 30 行 |
| 魔法数字 | 提取常量 | 散落在代码中的字面量 |
| 复杂条件 | 合并/拆分 | 含 3+ 个布尔运算符的条件 |

**示例：深嵌套重构**
```python
# 重构前
if user:
    if user.is_active:
        if user.has_permission('admin'):
            do_something()

# 重构后
if not user or not user.is_active:
    return
if not user.has_permission('admin'):
    return
do_something()
```

**示例：提取常量**
```python
# 重构前
if total > 3.14159 * radius ** 2:
    calculate(3600 * 24 * 7)

# 重构后
PI = 3.14159
SECONDS_IN_WEEK = 3600 * 24 * 7
if total > PI * radius ** 2:
    calculate(SECONDS_IN_WEEK)
```

### Step 3: 执行重构
用 Edit 逐项修改，每改一处立即验证语法：
```bash
python3 -c "import ast; ast.parse(open('file.py').read())"  # Python
node -e "require('fs').readFileSync('file.js','utf8')"      # JS
npx tsc --noEmit                                              # TS
```

### Step 4: 验证行为不变
```bash
pytest test_file.py -x -q   # 有测试
# 无测试：先写快照测试再重构
```

### Step 5: 交付总结
输出量化成果：删除无效代码行数、减少嵌套层数、提取函数/常量数量、测试通过率。

## 边界条件

| 场景 | 处理方式 |
|------|----------|
| 无测试覆盖 | Step4 前先写快照测试（pytest --snapshot-update）再重构 |
| 第三方库调用 | 不改外部API调用方式，只改调用处的变量命名 |
| 性能敏感路径 | 重构后用 timeit 基准对比，退化 > 5% 则回滚 |
| 多语言混排 | 逐语言扫描，只处理当前语言的代码块 |
| 全局搜索替换 | 用 Grep 确认所有引用，避免漏改 |

## 不做的场景（直接跳过）
- 改函数签名或返回值类型
- 引入新的第三方依赖
- 修改测试断言逻辑
- 重命名对外公开的 API

## 资源参考
- Martin Fowler 重构目录: https://refactoring.com/catalog/
- PEP 8: https://peps.python.org/pep-0008/
