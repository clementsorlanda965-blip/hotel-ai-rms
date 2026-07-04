#!/bin/bash
# 一键清除所有飞书 Bot 僵尸进程
echo "清理僵尸进程..."
# 杀事件总线（先杀 Bus 会自动清理所有消费者）
wmic process where "name='lark-cli.exe'" get commandline,processid 2>/dev/null | grep -i "event._bus" | while read line; do
  PID=$(echo "$line" | grep -oE '[0-9]+$')
  [ -n "$PID" ] && wmic process where "processid=$PID" delete 2>/dev/null && echo "  Bus PID:$PID"
done
sleep 2
# 再杀残留的 event consume
wmic process where "name='lark-cli.exe'" get commandline,processid 2>/dev/null | grep -i "event.consume" | while read line; do
  PID=$(echo "$line" | grep -oE '[0-9]+$')
  [ -n "$PID" ] && taskkill /F /PID $PID 2>/dev/null && echo "  消费者 PID:$PID"
done
echo "完成"