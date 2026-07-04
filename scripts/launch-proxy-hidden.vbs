' ═══════════════════════════════════════════════
' 隐藏窗口启动 DeepSeek 代理
' 作用：调用 start-proxy.bat，但完全隐藏命令行窗口（后台运行）
' 参数：0 = 隐藏窗口, False = 不等待子进程
' ═══════════════════════════════════════════════
CreateObject("WScript.Shell").Run """E:\工作AI\scripts\start-proxy.bat""", 0, False
