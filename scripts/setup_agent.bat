@echo off
:: ═══════════════════════════════════════════════════
:: 酒店管理系统 AI Agent — 三合一安装脚本
:: 作用：一键安装 Chrome DevTools MCP + TrendRadar + ruflo
:: ═══════════════════════════════════════════════════

:: 设置控制台代码页为 UTF-8，确保中文正常显示
chcp 65001 >nul

:: 设置窗口标题
title 酒店管理系统 AI Agent 一键安装

:: 打印欢迎标题
echo ============================================
echo   酒店管理系统 AI Agent — 三合一安装脚本
echo ============================================
echo.

:: ═══════════════════════════════════════════════
:: 步骤 1/3：Chrome DevTools MCP（浏览器自动化）
:: ═══════════════════════════════════════════════
echo [1/3] Chrome DevTools MCP — 已配置 (opencode.json)
echo   下次启动 OpenCode 时自动加载 42 个浏览器工具
echo.

:: ═══════════════════════════════════════════════
:: 步骤 2/3：TrendRadar（舆情监控 + AI 分析）
:: ═══════════════════════════════════════════════
echo [2/3] TrendRadar — 舆情监控 + AI 分析

:: 检查 tools\TrendRadar 目录是否存在
if not exist "tools\TrendRadar" (
    echo   正在克隆 TrendRadar...

    :: 从 GitHub 克隆 TrendRadar 仓库
    git clone https://github.com/sansan0/TrendRadar.git tools\TrendRadar

    :: 检查克隆是否成功，失败则跳过安装
    if %errorlevel% neq 0 (
        echo   ❌ 克隆失败，请手动执行: git clone https://github.com/sansan0/TrendRadar.git tools\TrendRadar
        goto next
    )
    echo   ✅ 克隆完成

    :: 安装 Python 依赖
    echo   正在安装 Python 依赖...
    cd tools\TrendRadar
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo   ❌ pip install 失败，请手动执行
        cd ..\..
        goto next
    )
    cd ..\..
    echo   ✅ pip install 完成
) else (
    echo   ⏩ TrendRadar 已存在，跳过克隆
)

:: 打印 MCP 服务启动方式
echo   启动 MCP 服务: python -m trendradar.mcp_server --port 3333
echo   详情: README-MCP-FAQ.md
echo.

:next
:: ═══════════════════════════════════════════════
:: 步骤 3/3：ruflo（多代理编排平台）
:: ═══════════════════════════════════════════════
echo [3/3] ruflo — 多代理编排平台
echo   正在安装 ruflo...

:: 用 npx 直接初始化 ruflo（--yes 跳过确认）
call npx ruflo@latest init --yes 2>nul

:: 检查安装结果
if %errorlevel% neq 0 (
    echo   ❌ npx 安装失败
    echo   请手动执行: npx ruflo@latest init
    goto end
)
echo   ✅ ruflo 安装完成

:: 打印 Claude Code 插件安装命令
echo   Claude Code 命令:
echo     /plugin install ruflo-core@ruflo
echo     /plugin install ruflo-swarm@ruflo
echo     /plugin install ruflo-autopilot@ruflo

:end
:: ═══════════════════════════════════════════════
:: 安装完成 — 打印总结
:: ═══════════════════════════════════════════════
echo.
echo ============================================
echo   安装完成!
echo   • Chrome DevTools MCP — opencode.json 已配置
echo   • TrendRadar — tools\TrendRadar (如成功)
echo   • ruflo — npx ruflo@latest (如成功)
echo ============================================
echo.
echo 使用方式:
echo   • 舆情监控: cd tools\TrendRadar ^&^& python -m trendradar start
echo   • 代理编排: npx ruflo@latest start
echo   • 浏览器测试: 下次 OpenCode 启动自动加载
echo ============================================

:: 暂停等待用户查看结果
pause
