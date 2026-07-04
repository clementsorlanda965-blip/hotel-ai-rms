@echo off
REM =============================================
REM set-winhttp-proxy.bat - 设置 Windows 系统级 HTTP 代理
REM 将 WinHTTP 代理指向 Clash (127.0.0.1:7890)
REM 排除本地地址和 localhost
REM =============================================

echo === 设置 WinHTTP 代理 ===
netsh winhttp set proxy "127.0.0.1:7890" "<local>;localhost;127.0.0.1;::1"
if %ERRORLEVEL% EQU 0 (
    echo 成功! WinHTTP 代理已设置为 127.0.0.1:7890
) else (
    echo 失败! 请以管理员权限运行此脚本
)
echo.
echo 当前 WinHTTP 代理状态:
netsh winhttp show proxy
pause
