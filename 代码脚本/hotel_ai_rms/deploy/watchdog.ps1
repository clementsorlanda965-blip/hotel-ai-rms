# =============================================================================
# watchdog.ps1 — Chrome CDP 心跳检测 + 自动重启
# =============================================================================
# 用途：确保 Chrome 远程调试端口始终可用
# 运行方式：作为 Windows 计划任务每 5 分钟执行一次
#          或在后台以循环模式运行: .\watchdog.ps1 -Loop
#
# 逻辑：
#   1. 检查 http://127.0.0.1:9222/json/version 是否响应
#   2. 响应正常 → 记录心跳、退出
#   3. 无响应 → 关闭孤立Chrome进程 → 拉起新Chrome CDP
#   4. 连续3次重启失败 → 飞书告警
# =============================================================================

param(
    [switch]$Loop,          # 循环模式（替代计划任务）
    [int]$IntervalSec = 300 # 循环模式下的检查间隔
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Resolve-Path "$scriptDir\.."

# ── 配置 ──
$CHROME_EXE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$CHROME_PORT = 9222
$HEALTH_URL = "http://127.0.0.1:${CHROME_PORT}/json/version"
$USER_DATA_DIR = "$rootDir\chrome_cdp_profile"
$STATE_FILE = "$rootDir\data\watchdog_state.json"
$LOG_FILE = "E:\工作AI\临时文件\watchdog.log"
$MAX_FAILURES = 3

# 确保目录存在
$dataDir = "$rootDir\data"
if (!(Test-Path $dataDir)) { New-Item -ItemType Directory -Force -Path $dataDir | Out-Null }

# ── 日志函数 ──
function Write-Log {
    param([string]$Level, [string]$Message)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] [$Level] $Message"
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
    Write-Host $line
}

# ── 读取/写入状态 ──
function Get-WatchdogState {
    if (Test-Path $STATE_FILE) {
        try { return Get-Content $STATE_FILE -Raw | ConvertFrom-Json }
        catch { }
    }
    return @{ consecutive_failures = 0; last_ok = $null; chrome_pid = $null; last_restart = $null }
}

function Set-WatchdogState($state) {
    $state | ConvertTo-Json -Depth 3 | Set-Content $STATE_FILE -Encoding UTF8
}

# ── 查找Chrome CDP进程 ──
function Find-ChromeCDPProcess {
    # 通过命令行参数找到带 --remote-debugging-port=9222 的 chrome.exe
    Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Where-Object {
        try {
            (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -match "remote-debugging-port=$CHROME_PORT"
        } catch { $false }
    }
}

# ── 清理僵尸Chrome进程 ──
function Clear-ZombieChrome {
    Write-Log "WARN" "清理所有监听端口 ${CHROME_PORT} 的僵尸Chrome进程..."
    $procs = Find-ChromeCDPProcess
    foreach ($p in $procs) {
        try {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            Write-Log "INFO" "  终止 Chrome PID=$($p.Id)"
        } catch {
            Write-Log "ERROR" "  无法终止 PID=$($p.Id): $_"
        }
    }
    Start-Sleep -Seconds 3
}

# ── 启动Chrome CDP ──
function Start-ChromeCDP {
    Write-Log "INFO" "启动 Chrome CDP (port=$CHROME_PORT)..."

    # 确保用户数据目录存在
    if (!(Test-Path $USER_DATA_DIR)) {
        New-Item -ItemType Directory -Force -Path $USER_DATA_DIR | Out-Null
    }

    # 检查Chrome是否已安装
    if (!(Test-Path $CHROME_EXE)) {
        # 尝试其他路径
        $alt_paths = @(
            "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
        )
        $found = $false
        foreach ($p in $alt_paths) {
            if (Test-Path $p) { $CHROME_EXE = $p; $found = $true; break }
        }
        if (!$found) {
            Write-Log "FATAL" "找不到 Chrome 浏览器！"
            return $false
        }
    }

    # Chrome CDP 启动参数
    $chromeArgs = @(
        "--remote-debugging-port=$CHROME_PORT",
        "--user-data-dir=`"$USER_DATA_DIR`"",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-features=TranslateUI",
        "--disable-component-update",
        "--disable-background-mode",
        "--disable-popup-blocking",
        "--disable-notifications",
        "--disable-extensions-file-access-check",
        "--no-service-autorun",
        "--hide-crash-restore-bubble"
    )

    try {
        # 使用 Start-Process 启动（脱离 job object，CLAUDE.md 的要求）
        $proc = Start-Process -FilePath $CHROME_EXE `
            -ArgumentList $chromeArgs `
            -WindowStyle Hidden `
            -PassThru

        Write-Log "INFO" "Chrome 已启动 PID=$($proc.Id)"

        # 等待就绪
        $ready = $false
        for ($i = 1; $i -le 15; $i++) {
            Start-Sleep -Seconds 1
            $result = Test-ChromeHealth
            if ($result) {
                Write-Log "INFO" "Chrome CDP 就绪 (耗时 ${i}s)"
                $ready = $true
                break
            }
            if ($proc.HasExited) {
                Write-Log "ERROR" "Chrome 进程异常退出 (exit code: $($proc.ExitCode))"
                return $false
            }
        }

        if ($ready) {
            $state = Get-WatchdogState
            $state.consecutive_failures = 0
            $state.chrome_pid = $proc.Id
            $state.last_restart = (Get-Date).ToString("o")
            Set-WatchdogState $state
            return $true
        } else {
            Write-Log "ERROR" "Chrome CDP 启动超时（${i}秒未就绪）"
            return $false
        }
    } catch {
        Write-Log "FATAL" "启动 Chrome 异常: $_"
        return $false
    }
}

# ── 健康检查 ──
function Test-ChromeHealth {
    try {
        $req = [System.Net.WebRequest]::Create($HEALTH_URL)
        $req.Timeout = 5000
        $resp = $req.GetResponse()
        $stream = $resp.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $body = $reader.ReadToEnd()
        $reader.Close()
        $resp.Close()

        $json = $body | ConvertFrom-Json
        if ($json.webSocketDebuggerUrl) {
            return $true
        }
        Write-Log "WARN" "健康检查响应缺少 webSocketDebuggerUrl"
        return $false
    } catch {
        return $false
    }
}

# ── 主检查逻辑 ──
function Invoke-WatchdogCheck {
    $state = Get-WatchdogState

    Write-Log "INFO" "======== 心跳检测开始 ========"
    Write-Log "INFO" "Chrome端口: $CHROME_PORT, 连续失败: $($state.consecutive_failures)"

    $healthy = Test-ChromeHealth

    if ($healthy) {
        Write-Log "INFO" "Chrome CDP 健康检查通过 ✅"
        $state.consecutive_failures = 0
        $state.last_ok = (Get-Date).ToString("o")
        Set-WatchdogState $state
        return $true
    }

    # 不健康 — 记录失败
    $state.consecutive_failures += 1
    Set-WatchdogState $state

    $failures = $state.consecutive_failures
    Write-Log "WARN" "Chrome CDP 无响应 (连续第 ${failures} 次)"

    if ($failures -ge $MAX_FAILURES) {
        Write-Log "ERROR" "连续 ${failures} 次失败，执行强制重启..."

        # 1. 清理僵尸
        Clear-ZombieChrome

        # 2. 重启
        $success = Start-ChromeCDP

        if (!$success) {
            Write-Log "FATAL" "Chrome CDP 重启失败！触发飞书告警..."
            Send-FeishuAlert "Chrome CDP 连续 ${failures} 次重启失败" "CRITICAL"
            return $false
        }

        # 3. 重启后再次验证
        Start-Sleep -Seconds 3
        if (Test-ChromeHealth) {
            Write-Log "INFO" "Chrome CDP 重启成功 ✅"
            return $true
        } else {
            Write-Log "FATAL" "Chrome CDP 重启后仍然无响应！"
            Send-FeishuAlert "Chrome CDP 重启后仍无法恢复" "CRITICAL"
            return $false
        }
    } else {
        Write-Log "INFO" "等待下次检查（还需 $($MAX_FAILURES - $failures) 次失败才触发重启）"
        return $false
    }
}

# ── 飞书告警 ──
function Send-FeishuAlert {
    param([string]$Message, [string]$Level = "WARN")

    $webhookUrl = $env:FEISHU_RMS_ALERT_WEBHOOK
    if (!$webhookUrl) {
        # 检查配置文件
        $envFile = "$rootDir\config\feishu.env"
        if (Test-Path $envFile) {
            Get-Content $envFile | Where-Object { $_ -match "^FEISHU_RMS_ALERT_WEBHOOK=(.+)" } | ForEach-Object {
                $webhookUrl = $Matches[1]
            }
        }
    }

    if (!$webhookUrl) {
        Write-Log "WARN" "飞书Webhook未配置，跳过告警推送"
        return
    }

    $color = if ($Level -eq "CRITICAL") { "red" } elseif ($Level -eq "WARN") { "yellow" } else { "green" }
    $body = @{
        msg_type = "interactive"
        card = @{
            header = @{
                title = @{ tag = "plain_text"; content = "🏨 OTA采集监控告警" }
                template = $color
            }
            elements = @(
                @{
                    tag = "div"
                    text = @{
                        tag = "lark_md"
                        content = "**$Message**`n`n时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n服务器：$env:COMPUTERNAME"
                    }
                }
            )
        }
    } | ConvertTo-Json -Depth 5 -Compress

    try {
        Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 10
        Write-Log "INFO" "飞书告警已发送"
    } catch {
        Write-Log "ERROR" "飞书告警发送失败: $_"
    }
}

# ── 主入口 ──
if ($Loop) {
    Write-Log "INFO" "Chrome CDP 看门狗启动（循环模式，间隔 $IntervalSec 秒）"
    while ($true) {
        try {
            Invoke-WatchdogCheck
        } catch {
            Write-Log "ERROR" "看门狗循环异常: $_"
        }
        Start-Sleep -Seconds $IntervalSec
    }
} else {
    # 单次检查模式（适用于计划任务）
    try {
        $result = Invoke-WatchdogCheck
        exit ($result ? 0 : 1)
    } catch {
        Write-Log "FATAL" "看门狗致命异常: $_"
        exit 2
    }
}
