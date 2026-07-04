#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# 停止头脑风暴服务器并清理临时文件
# Stop the brainstorm server and clean up
# ═══════════════════════════════════════════════════════════════
# Usage: stop-server.sh <session_dir>
#
# 杀掉服务器进程。仅在 /tmp 下的会话目录会被删除（临时目录）。
# .superpowers/ 下的持久化目录保留，以便后续查看设计稿。
# Kills the server process. Only deletes session directory if it's
# under /tmp (ephemeral). Persistent directories (.superpowers/) are
# kept so mockups can be reviewed later.

# 会话目录路径（必须参数）
SESSION_DIR="$1"

if [[ -z "$SESSION_DIR" ]]; then
  echo '{"error": "Usage: stop-server.sh <session_dir>"}'
  exit 1
fi

# 状态目录 + PID 文件路径
STATE_DIR="${SESSION_DIR}/state"
PID_FILE="${STATE_DIR}/server.pid"

# ═══════════════════════════════════════════════════════════════
# 如果 PID 文件存在，读取 PID 并停止进程
# ═══════════════════════════════════════════════════════════════
if [[ -f "$PID_FILE" ]]; then
  pid=$(cat "$PID_FILE")

  # 先尝试优雅关闭（SIGTERM），失败后强制杀掉（SIGKILL）
  # Try to stop gracefully, fallback to force if still alive
  kill "$pid" 2>/dev/null || true

  # 等待最多约 2 秒（20 次 × 0.1 秒）让进程优雅退出
  # Wait for graceful shutdown (up to ~2s)
  for i in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      break
    fi
    sleep 0.1
  done

  # 如果进程仍在运行，升级到强制终止（kill -9）
  # If still running, escalate to SIGKILL
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true

    # 等待 SIGKILL 生效
    # Give SIGKILL a moment to take effect
    sleep 0.1
  fi

  # 最终确认：进程是否真的停了
  if kill -0 "$pid" 2>/dev/null; then
    echo '{"status": "failed", "error": "process still running"}'
    exit 1
  fi

  # 清理 PID 文件和日志文件
  rm -f "$PID_FILE" "${STATE_DIR}/server.log"

  # 仅删除 /tmp 下的临时目录（持久化目录保留）
  # Only delete ephemeral /tmp directories
  if [[ "$SESSION_DIR" == /tmp/* ]]; then
    rm -rf "$SESSION_DIR"
  fi

  echo '{"status": "stopped"}'
else
  echo '{"status": "not_running"}'
fi
