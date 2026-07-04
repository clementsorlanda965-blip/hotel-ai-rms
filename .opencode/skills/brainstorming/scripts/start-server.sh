#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# 启动头脑风暴服务器并输出连接信息
# Start the brainstorm server and output connection info
# ═══════════════════════════════════════════════════════════════
# Usage: start-server.sh [--project-dir <path>] [--host <bind-host>] [--url-host <display-host>] [--foreground] [--background]
#
# 在高位端口上启动服务器，以 JSON 格式输出连接 URL。
# 每个会话有独立目录，避免冲突。
# Starts server on a random high port, outputs JSON with URL.
# Each session gets its own directory to avoid conflicts.
#
# 参数说明 / Options:
#   --project-dir <path>  将会话文件存储到 <path>/.superpowers/brainstorm/ 下（而非 /tmp），
#                         服务器停止后文件仍然保留
#                         Store session files under <path>/.superpowers/brainstorm/
#                         instead of /tmp. Files persist after server stops.
#   --host <bind-host>    绑定的主机/接口（默认: 127.0.0.1）
#                         Host/interface to bind (default: 127.0.0.1).
#                         在远程/容器环境中使用 0.0.0.0
#                         Use 0.0.0.0 in remote/containerized environments.
#   --url-host <host>     返回的 URL JSON 中显示的主机名
#                         Hostname shown in returned URL JSON.
#   --foreground          在当前终端中运行服务器（不后台化）
#                         Run server in the current terminal (no backgrounding).
#   --background          强制后台模式（覆盖 Codex 自动前台检测）
#                         Force background mode (overrides Codex auto-foreground).

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ═══════════════════════════════════════════════════════════════
# 解析命令行参数
# ═══════════════════════════════════════════════════════════════
PROJECT_DIR=""
FOREGROUND="false"
FORCE_BACKGROUND="false"
BIND_HOST="127.0.0.1"
URL_HOST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    --host)
      BIND_HOST="$2"
      shift 2
      ;;
    --url-host)
      URL_HOST="$2"
      shift 2
      ;;
    --foreground|--no-daemon)
      FOREGROUND="true"
      shift
      ;;
    --background|--daemon)
      FORCE_BACKGROUND="true"
      shift
      ;;
    *)
      echo "{\"error\": \"Unknown argument: $1\"}"
      exit 1
      ;;
  esac
done

# 如果没有指定 URL 主机名，自动推导：
# 127.0.0.1/localhost → localhost，否则用绑定地址
if [[ -z "$URL_HOST" ]]; then
  if [[ "$BIND_HOST" == "127.0.0.1" || "$BIND_HOST" == "localhost" ]]; then
    URL_HOST="localhost"
  else
    URL_HOST="$BIND_HOST"
  fi
fi

# 某些环境会收割分离/后台进程，检测到后自动切换前台模式
# Some environments reap detached/background processes. Auto-foreground when detected.
if [[ -n "${CODEX_CI:-}" && "$FOREGROUND" != "true" && "$FORCE_BACKGROUND" != "true" ]]; then
  FOREGROUND="true"
fi

# Windows/Git Bash 会收割 nohup 后台进程，自动前台
# Windows/Git Bash reaps nohup background processes. Auto-foreground when detected.
if [[ "$FOREGROUND" != "true" && "$FORCE_BACKGROUND" != "true" ]]; then
  case "${OSTYPE:-}" in
    msys*|cygwin*|mingw*) FOREGROUND="true" ;;
  esac
  if [[ -n "${MSYSTEM:-}" ]]; then
    FOREGROUND="true"
  fi
fi

# ═══════════════════════════════════════════════════════════════
# 生成唯一会话 ID（进程ID + 时间戳）
# ═══════════════════════════════════════════════════════════════
SESSION_ID="$$-$(date +%s)"

if [[ -n "$PROJECT_DIR" ]]; then
  SESSION_DIR="${PROJECT_DIR}/.superpowers/brainstorm/${SESSION_ID}"
else
  SESSION_DIR="/tmp/brainstorm-${SESSION_ID}"
fi

# 状态目录 + PID 文件 + 日志文件路径
STATE_DIR="${SESSION_DIR}/state"
PID_FILE="${STATE_DIR}/server.pid"
LOG_FILE="${STATE_DIR}/server.log"

# 创建会话目录（content 子目录 + state 子目录）
mkdir -p "${SESSION_DIR}/content" "$STATE_DIR"

# ═══════════════════════════════════════════════════════════════
# 清理旧实例：如果已有 PID 文件，杀掉旧服务器进程
# ═══════════════════════════════════════════════════════════════
if [[ -f "$PID_FILE" ]]; then
  old_pid=$(cat "$PID_FILE")
  kill "$old_pid" 2>/dev/null
  rm -f "$PID_FILE"
fi

cd "$SCRIPT_DIR"

# ═══════════════════════════════════════════════════════════════
# 解析 harness 进程 PID（本脚本的祖父进程）
# $PPID 是 harness 派生出来运行本脚本的临时 shell——脚本退出后它会消亡。
# harness 本身是 $PPID 的父进程。
# Resolve the harness PID (grandparent of this script).
# $PPID is the ephemeral shell the harness spawned to run us — it dies
# when this script exits. The harness itself is $PPID's parent.
# ═══════════════════════════════════════════════════════════════
OWNER_PID="$(ps -o ppid= -p "$PPID" 2>/dev/null | tr -d ' ')"
if [[ -z "$OWNER_PID" || "$OWNER_PID" == "1" ]]; then
  OWNER_PID="$PPID"
fi

# ═══════════════════════════════════════════════════════════════
# 前台模式：当环境会收割分离/后台进程时使用
# Foreground mode for environments that reap detached/background processes.
# ═══════════════════════════════════════════════════════════════
if [[ "$FOREGROUND" == "true" ]]; then
  echo "$$" > "$PID_FILE"
  env BRAINSTORM_DIR="$SESSION_DIR" BRAINSTORM_HOST="$BIND_HOST" BRAINSTORM_URL_HOST="$URL_HOST" BRAINSTORM_OWNER_PID="$OWNER_PID" node server.cjs
  exit $?
fi

# ═══════════════════════════════════════════════════════════════
# 后台模式：启动服务器并捕获输出到日志文件
# 使用 nohup 防止 shell 退出时杀掉进程，disown 从作业表中移除
# Start server, capturing output to log file
# Use nohup to survive shell exit; disown to remove from job table
# ═══════════════════════════════════════════════════════════════
nohup env BRAINSTORM_DIR="$SESSION_DIR" BRAINSTORM_HOST="$BIND_HOST" BRAINSTORM_URL_HOST="$URL_HOST" BRAINSTORM_OWNER_PID="$OWNER_PID" node server.cjs > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
disown "$SERVER_PID" 2>/dev/null
echo "$SERVER_PID" > "$PID_FILE"

# ═══════════════════════════════════════════════════════════════
# 等待服务器就绪消息（检查日志文件中的 "server-started"）
# 最多等待 5 秒（50 次 × 0.1 秒）
# Wait for server-started message (check log file)
# ═══════════════════════════════════════════════════════════════
for i in {1..50}; do
  if grep -q "server-started" "$LOG_FILE" 2>/dev/null; then
    # 验证服务器在短暂窗口后仍然存活（防止被进程收割器杀掉）
    # Verify server is still alive after a short window (catches process reapers)
    alive="true"
    for _ in {1..20}; do
      if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        alive="false"
        break
      fi
      sleep 0.1
    done
    if [[ "$alive" != "true" ]]; then
      echo "{\"error\": \"Server started but was killed. Retry in a persistent terminal with: $SCRIPT_DIR/start-server.sh${PROJECT_DIR:+ --project-dir $PROJECT_DIR} --host $BIND_HOST --url-host $URL_HOST --foreground\"}"
      exit 1
    fi
    grep "server-started" "$LOG_FILE" | head -1
    exit 0
  fi
  sleep 0.1
done

# 超时：服务器未能在 5 秒内启动
# Timeout - server didn't start
echo '{"error": "Server failed to start within 5 seconds"}'
exit 1
