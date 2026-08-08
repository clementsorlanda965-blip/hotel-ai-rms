# =============================================================================
# install_tasks.ps1 — 一键安装 Windows 计划任务
# =============================================================================
# 用途：将 OTA 采集相关的所有定时任务注册到 Windows Task Scheduler
# 运行：以管理员身份运行 PowerShell，执行此脚本
#       .\install_tasks.ps1
#       .\install_tasks.ps1 -Uninstall  # 卸载所有任务
# =============================================================================

param(
    [switch]$Uninstall,
    [string]$TaskPrefix = "HotelRMS"
)

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Resolve-Path "$scriptDir\.."

# ── 任务定义 ──
$tasks = @(
    @{
        Name = "${TaskPrefix}_DailyScrape_09"
        Description = "酒店RMS - 每日09:00 OTA价格采集（含携程CDP+Google+Qunar）"
        ScriptPath = "$scriptDir\scheduled_scrape.ps1"
        Arguments = "-Mode auto"
        Triggers = @(
            @{ Type = "Daily"; At = "09:00" }
        )
        # 如果错过则1小时内重试
        MissedTask = @{ Enabled = $true; RestartOnMissed = $true; RestartInterval = 15 }
    },
    @{
        Name = "${TaskPrefix}_DailyScrape_15"
        Description = "酒店RMS - 每日15:00 OTA价格补采（Google Hotels）"
        ScriptPath = "$scriptDir\scheduled_scrape.ps1"
        Arguments = "-Mode google"
        Triggers = @(
            @{ Type = "Daily"; At = "15:00" }
        )
        MissedTask = @{ Enabled = $true; RestartOnMissed = $true; RestartInterval = 10 }
    },
    @{
        Name = "${TaskPrefix}_ChromeWatchdog"
        Description = "酒店RMS - Chrome CDP 看门狗（每5分钟心跳检测+自动重启）"
        ScriptPath = "$scriptDir\watchdog.ps1"
        Arguments = ""
        Triggers = @(
            @{ Type = "Daily"; At = "00:00" },
            @{ Type = "Repetition"; Interval = 5; Duration = "P1D" }
        )
        MissedTask = @{ Enabled = $false }
    },
    @{
        Name = "${TaskPrefix}_WeeklyReport"
        Description = "酒店RMS - 每周一08:00 生成OTA价格周报"
        ScriptPath = "$rootDir\bi_reports.py"
        Arguments = "--weekly"
        Triggers = @(
            @{ Type = "Weekly"; At = "08:00"; DaysOfWeek = "Monday" }
        )
        MissedTask = @{ Enabled = $true; RestartOnMissed = $true; RestartInterval = 30 }
    }
)

# ── 辅助函数 ──
function Register-ScheduledTaskItem {
    param($TaskDef)

    $taskName = $TaskDef.Name

    # 构建触发器XML
    $triggerXml = @()
    foreach ($trigger in $TaskDef.Triggers) {
        switch ($trigger.Type) {
            "Daily" {
                $triggerXml += @"
      <CalendarTrigger>
        <StartBoundary>$(Get-Date -Format 'yyyy-MM-dd')T$($trigger.At):00+08:00</StartBoundary>
        <Enabled>true</Enabled>
        <ScheduleByDay>
          <DaysInterval>1</DaysInterval>
        </ScheduleByDay>
      </CalendarTrigger>
"@
            }
            "Weekly" {
                $triggerXml += @"
      <CalendarTrigger>
        <StartBoundary>$(Get-Date -Format 'yyyy-MM-dd')T$($trigger.At):00+08:00</StartBoundary>
        <Enabled>true</Enabled>
        <ScheduleByWeek>
          <DaysOfWeek>
            <$($trigger.DaysOfWeek) />
          </DaysOfWeek>
          <WeeksInterval>1</WeeksInterval>
        </ScheduleByWeek>
      </CalendarTrigger>
"@
            }
            "Repetition" {
                $triggerXml += @"
      <CalendarTrigger>
        <StartBoundary>$(Get-Date -Format 'yyyy-MM-dd')T00:00:00+08:00</StartBoundary>
        <Enabled>true</Enabled>
        <Repetition>
          <Interval>PT$($trigger.Interval)M</Interval>
          <Duration>$($trigger.Duration)</Duration>
          <StopAtDurationEnd>false</StopAtDurationEnd>
        </Repetition>
        <ScheduleByDay>
          <DaysInterval>1</DaysInterval>
        </ScheduleByDay>
      </CalendarTrigger>
"@
            }
        }
    }

    $missedTaskXml = ""
    if ($TaskDef.MissedTask.Enabled) {
        $missedTaskXml = @"
    <Settings>
      <StartWhenAvailable>true</StartWhenAvailable>
      <RestartOnFailure>
        <Interval>PT$($TaskDef.MissedTask.RestartInterval)M</Interval>
        <Count>3</Count>
      </RestartOnFailure>
    </Settings>
"@
    } else {
        $missedTaskXml = @"
    <Settings>
      <StartWhenAvailable>false</StartWhenAvailable>
    </Settings>
"@
    }

    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>$($TaskDef.Description)</Description>
    <Author>Hotel AI-RMS</Author>
  </RegistrationInfo>
  <Triggers>
$($triggerXml -join "`n")
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -File "$($TaskDef.ScriptPath)" $($TaskDef.Arguments)</Arguments>
      <WorkingDirectory>$rootDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

    $tempFile = "$env:TEMP\${taskName}.xml"
    $xml | Out-File -FilePath $tempFile -Encoding Unicode -Force

    try {
        Register-ScheduledTask -TaskName $taskName -Xml (Get-Content $tempFile -Raw) -Force
        Write-Host "  ✅ $taskName"
        return $true
    } catch {
        Write-Host "  ❌ $taskName 失败: $_"
        return $false
    } finally {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}

function Unregister-ScheduledTaskItem {
    param([string]$TaskName)
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "  🗑️  $TaskName (已删除)"
    } catch {
        # 任务不存在是正常的
    }
}

# ── 主入口 ──
Write-Host ""
Write-Host "══════════════════════════════════════════"
Write-Host "  Hotel AI-RMS 计划任务安装/卸载工具"
Write-Host "══════════════════════════════════════════"
Write-Host ""

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!$isAdmin) {
    Write-Host "❌ 需要管理员权限！请右键 → 以管理员身份运行 PowerShell"
    Write-Host "   或者: Start-Process powershell -Verb RunAs -ArgumentList '-File $PSCommandPath'"
    exit 1
}

if ($Uninstall) {
    Write-Host "🗑️  卸载所有计划任务..."
    foreach ($task in $tasks) {
        Unregister-ScheduledTaskItem -TaskName $task.Name
    }
    Write-Host ""
    Write-Host "✅ 卸载完成"
    exit 0
}

Write-Host "📋 安装计划任务..."
Write-Host ""

$installFailed = $false
foreach ($task in $tasks) {
    Write-Host "  [$($task.Name)]"
    Write-Host "    $($task.Description)"
    if (!(Register-ScheduledTaskItem -TaskDef $task)) { $installFailed = $true }
}

if ($installFailed) {
    Write-Host "❌ 存在计划任务安装失败，请检查上方错误。"
    exit 1
}

Write-Host ""
Write-Host "══════════════════════════════════════════"
Write-Host "✅ 全部计划任务安装完成！"
Write-Host ""
Write-Host "📋 任务概览："
Write-Host "  • ${TaskPrefix}_DailyScrape_09  → 每日09:00 全量采集（携程CDP+Google+Qunar）"
Write-Host "  • ${TaskPrefix}_DailyScrape_15  → 每日15:00 快速补采（Google Hotels）"
Write-Host "  • ${TaskPrefix}_ChromeWatchdog  → 每5分钟 Chrome CDP 心跳检测"
Write-Host "  • ${TaskPrefix}_WeeklyReport    → 每周一早08:00 生成周报"
Write-Host ""
Write-Host "🔍 验证: taskschd.msc → 搜索 'HotelRMS'"
Write-Host "📊 日志: E:\工作AI\临时文件\watchdog.log"
Write-Host "📊 日志: E:\工作AI\临时文件\scheduled_scrape.log"
Write-Host ""
Write-Host "💡 手动测试单个采集:"
Write-Host "   powershell -File `"$scriptDir\scheduled_scrape.ps1`" -Mode auto"
Write-Host "══════════════════════════════════════════"
