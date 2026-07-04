@echo off
chcp 65001 >nul
:: ═══════════════════════════════════════════════════
:: Claude Code + DeepSeek V4 启动脚本 (Proxy 模式)
:: 代理自动注入 thinking=disabled, 模型名翻译
:: ═══════════════════════════════════════════════════

echo [启动] Claude Code + DeepSeek V4

:: 检查 Node.js 代理是否已在运行（端口 3206，而非有问题的 3200）
curl -s http://127.0.0.1:3206/health >nul 2>&1
if errorlevel 1 (
    echo [代理] 启动 DeepSeek 代理...
    powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "E:\claude-code\start-proxy.ps1"
    timeout /t 2 /nobreak >nul
)

:: 指向本地代理（端口 3206）
set ANTHROPIC_BASE_URL=http://127.0.0.1:3206
set ANTHROPIC_AUTH_TOKEN=sk-2b1524f7492a4ccfab9ee924fc173397

:: 启动 Claude Code（使用 claude-cn 入口，自带代理环境变量）
powershell -NoLogo -ExecutionPolicy Bypass -File "E:\claude-code\claude-cn.ps1" %*
