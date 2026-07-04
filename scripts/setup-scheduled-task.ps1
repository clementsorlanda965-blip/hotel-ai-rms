<#
.SYNOPSIS
  创建 Windows 计划任务，让 DeepSeek 代理在系统启动时自动运行
  并在崩溃后自动重启，确保代理始终在线
#>

# ═══════════════════════════════════════════════
# 任务名称 + 代理脚本路径
# ═══════════════════════════════════════════════
$taskName = "DeepSeekProxy"
$scriptPath = "E:\工作AI\scripts\deepseek-proxy.mjs"

# ═══════════════════════════════════════════════
# 获取 node.exe 路径（从 PATH 中查找）
# ═══════════════════════════════════════════════
$nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $nodeExe) { $nodeExe = "node" }

# ═══════════════════════════════════════════════
# 构建计划任务组件
# ═══════════════════════════════════════════════

# 动作：用 node.exe 执行代理脚本
$action = New-ScheduledTaskAction -Execute $nodeExe -Argument "`"$scriptPath`"" -WorkingDirectory "E:\工作AI\scripts"

# 触发器：用户登录时自动启动
$trigger = New-ScheduledTaskTrigger -AtLogon

# 主体：以当前用户身份、最高权限运行
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# 设置：允许电池运行、不因电池停止、崩溃后无限重启（间隔1分钟）
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew

# ═══════════════════════════════════════════════
# 先删除旧任务，再创建新任务
# ═══════════════════════════════════════════════
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

Write-Output "Task '$taskName' created successfully."

# ═══════════════════════════════════════════════
# 立即启动代理（不等下次登录）
# ═══════════════════════════════════════════════
Start-ScheduledTask -TaskName $taskName
Write-Output "Task '$taskName' started."
