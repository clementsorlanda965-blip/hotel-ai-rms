@echo off
:: ═══════════════════════════════════════════════════
:: DeepSeek API 代理 — 自动重启守护脚本
:: 作用：在本地 3200 端口启动 Node.js 代理服务，
::       崩溃后自动重启，确保 Claude Desktop 始终能连上
:: ═══════════════════════════════════════════════════

:: 设置窗口标题
title DeepSeek Proxy - Auto Restart

:: 切换到脚本所在目录
cd /d "E:\工作AI\scripts"

:: 打印启动时间戳
echo [%date% %time%] DeepSeek Proxy Monitor Started

:loop
:: 每次循环都打印启动日志
echo [%date% %time%] Starting DeepSeek Proxy on port 3200...

:: 启动 Node.js 代理服务器（deepseek-proxy.mjs 负责转发 API 请求到 DeepSeek）
node "E:\工作AI\scripts\deepseek-proxy.mjs"

:: 代理退出后等待 3 秒再重启（防止频繁崩溃循环）
echo [%date% %time%] Proxy exited with code %ERRORLEVEL%. Restarting in 3 seconds...
timeout /t 3 /nobreak >nul

:: 跳回循环头部，重新启动代理
goto loop
