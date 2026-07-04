#!/bin/bash
# 飞书 <-> Claude Code Bot
# lark-cli event consume --timeout (官方推荐子进程模式)
# 每 300 秒自动重启，无缝衔接

CLAUDE="E:/claude-code/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
SEEN_FILE="E:/工作AI/临时文件/bot_seen.txt"
LOG="E:/工作AI/临时文件/bot.log"
PIDFILE="E:/工作AI/临时文件/bot.pid"

echo $$ > "$PIDFILE"
touch "$SEEN_FILE"

cleanup() { rm -f "$PIDFILE"; exit 0; }
trap cleanup SIGINT SIGTERM

echo "[$(date +%H:%M:%S)] Bot启动 PID:$$" >> "$LOG"

while true; do
  echo "[$(date +%H:%M:%S)] 监听中..." >> "$LOG"

  lark-cli.cmd event consume im.message.receive_v1 \
    --timeout 300s --max-events 50 --as bot 2>/dev/null \
  | while IFS= read -r line; do
      MSG_ID=$(echo "$line" | grep -o '"message_id":"[^"]*"' | head -1 | cut -d'"' -f4)
      [ -z "$MSG_ID" ] && continue
      grep -q "$MSG_ID" "$SEEN_FILE" && continue
      echo "$MSG_ID" >> "$SEEN_FILE"
      # 只保留最近 500 条
      tail -500 "$SEEN_FILE" > "$SEEN_FILE.tmp" 2>/dev/null && mv "$SEEN_FILE.tmp" "$SEEN_FILE" 2>/dev/null

      CONTENT=$(echo "$line" | grep -o '"content":"[^"]*"' | head -1 | cut -d'"' -f4)
      echo "[$(date +%H:%M:%S)] 收到: $CONTENT" >> "$LOG"

      REPLY=$(cd "E:/工作AI" && "$CLAUDE" -p "[飞书私聊] $CONTENT" \
        --dangerously-skip-permissions --output-format text 2>/dev/null)

      if [ -n "$REPLY" ]; then
        echo "$REPLY" > /tmp/bot_reply.txt
        lark-cli.cmd im +messages-reply --message-id "$MSG_ID" \
          --text "$(cat /tmp/bot_reply.txt)" --as bot 2>/dev/null
        echo "[$(date +%H:%M:%S)] 已回复 (${#REPLY}字符)" >> "$LOG"
      fi
    done

  echo "[$(date +%H:%M:%S)] 轮次结束 3秒后重启" >> "$LOG"
  sleep 3
done
