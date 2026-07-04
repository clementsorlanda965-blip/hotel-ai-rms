@echo off
:: ═══════════════════════════════════════════════════
:: LiteLLM 代理启动脚本
:: 作用：在本地 4000 端口启动 LiteLLM 代理，
::       将 DeepSeek API 封装成 OpenAI 兼容接口
:: ═══════════════════════════════════════════════════

:: 设置窗口标题
title LiteLLM Proxy - DeepSeek V4

:: 打印启动信息
echo Starting LiteLLM Proxy on http://127.0.0.1:4000 ...
echo Model: deepseek/deepseek-chat
echo.

:: 切换到脚本所在目录（确保能读取 litellm_config.yaml）
cd /d %~dp0

:: 启动 LiteLLM 代理，读取同目录下的 litellm_config.yaml 配置文件
python -m litellm --config litellm_config.yaml --port 4000

:: 代理退出后暂停，方便查看错误日志
pause
