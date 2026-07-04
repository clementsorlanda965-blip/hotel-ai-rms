<#
.SYNOPSIS
  在 Windows 启动文件夹创建 VBS 快捷方式，
  让 DeepSeek 代理在用户登录时静默启动（无窗口）
#>

# ═══════════════════════════════════════════════
# 路径配置
# ═══════════════════════════════════════════════

# Windows 启动文件夹路径
$startupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

# 目标：隐藏窗口启动代理的 VBS 脚本
$targetPath = "E:\工作AI\scripts\launch-proxy-hidden.vbs"

# 快捷方式保存路径
$shortcutPath = "$startupFolder\DeepSeekProxy.lnk"

# ═══════════════════════════════════════════════
# 创建 COM 对象并构建快捷方式
# ═══════════════════════════════════════════════
$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut($shortcutPath)

# 设定快捷方式属性
$shortcut.TargetPath = "wscript.exe"             # 用 wscript.exe 执行 VBS（无控制台窗口）
$shortcut.Arguments = "`"$targetPath`""           # 传 VBS 脚本路径作为参数
$shortcut.WorkingDirectory = "E:\工作AI\scripts"  # 工作目录
$shortcut.WindowStyle = 7                         # 窗口样式=7（最小化，无闪烁）
$shortcut.Description = "DeepSeek API Proxy for Claude Desktop"

# 保存快捷方式到文件
$shortcut.Save()

Write-Output "Shortcut created at: $shortcutPath"
