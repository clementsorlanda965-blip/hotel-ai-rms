#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# 二分排查脚本：找出哪个测试创建了不需要的文件/状态
# Bisection script to find which test creates unwanted files/state
# ═══════════════════════════════════════════════════════════════
# Usage: ./find-polluter.sh <file_or_dir_to_check> <test_pattern>
# Example: ./find-polluter.sh '.git' 'src/**/*.test.ts'
#
# 工作原理：逐个运行测试，检测目标文件/目录是否出现，
# 找到第一个触发污染产生的测试文件
# How it works: Run tests one by one, checking if the target
# file/directory appears, identifying the first test that pollutes.

# 开启严格模式：任何命令失败立即退出
set -e

# 检查参数数量
if [ $# -ne 2 ]; then
  echo "Usage: $0 <file_to_check> <test_pattern>"
  echo "Example: $0 '.git' 'src/**/*.test.ts'"
  exit 1
fi

# 要检测的污染目标（文件或目录名）
POLLUTION_CHECK="$1"

# 测试文件的 glob 匹配模式
TEST_PATTERN="$2"

echo "🔍 Searching for test that creates: $POLLUTION_CHECK"
echo "Test pattern: $TEST_PATTERN"
echo ""

# ═══════════════════════════════════════════════════════════════
# 获取匹配的测试文件列表
# ═══════════════════════════════════════════════════════════════
TEST_FILES=$(find . -path "$TEST_PATTERN" | sort)
TOTAL=$(echo "$TEST_FILES" | wc -l | tr -d ' ')

echo "Found $TOTAL test files"
echo ""

# ═══════════════════════════════════════════════════════════════
# 逐个运行测试，直到找到污染源
# ═══════════════════════════════════════════════════════════════
COUNT=0
for TEST_FILE in $TEST_FILES; do
  COUNT=$((COUNT + 1))

  # 如果污染目标在执行前就已存在，跳过（不是这个测试造成的）
  # Skip if pollution already exists before this test
  if [ -e "$POLLUTION_CHECK" ]; then
    echo "⚠️  Pollution already exists before test $COUNT/$TOTAL"
    echo "   Skipping: $TEST_FILE"
    continue
  fi

  echo "[$COUNT/$TOTAL] Testing: $TEST_FILE"

  # 运行测试（静默输出，失败也不中断）
  # Run the test (suppress output, don't exit on failure)
  npm test "$TEST_FILE" > /dev/null 2>&1 || true

  # 检查污染目标是否出现
  # Check if pollution appeared after running this test
  if [ -e "$POLLUTION_CHECK" ]; then
    echo ""
    echo "🎯 FOUND POLLUTER!"
    echo "   Test: $TEST_FILE"
    echo "   Created: $POLLUTION_CHECK"
    echo ""
    echo "Pollution details:"

    # 列出污染目标的详细信息
    ls -la "$POLLUTION_CHECK"

    echo ""
    echo "To investigate:"
    echo "  npm test $TEST_FILE    # 单独运行这个测试"
    echo "  cat $TEST_FILE         # 查看测试代码"
    exit 1
  fi
done

# 没有找到污染源
echo ""
echo "✅ No polluter found - all tests clean!"
exit 0
