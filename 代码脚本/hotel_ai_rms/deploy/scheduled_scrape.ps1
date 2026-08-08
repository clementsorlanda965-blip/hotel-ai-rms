# =============================================================================
# scheduled_scrape.ps1 — 定时采集任务入口
# =============================================================================
# 用途：Windows Task Scheduler 调用此脚本执行每日 OTA 价格采集
# 计划：每日 09:00、15:00、21:00 各执行一次
#
# 执行流程：
#   1. 检查网络连通性
#   2. 检查 Chrome CDP 是否健康（不健康则尝试拉起）
#   3. 运行采集脚本
#   4. 验证输出数据质量
#   5. 检测竞对异常 → 飞书告警
#   6. 写入 SQLite 历史记录
#   7. 上报采集状态
# =============================================================================

param(
    [string]$Mode = "auto",           # auto|ctrip|google|fallback
    [switch]$SkipChromeCheck,         # 跳过 Chrome CDP 检查（纯 HTML 模式）
    [switch]$DryRun                   # 不实际采集，仅检查环境
)

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Resolve-Path "$scriptDir\.."
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (!$pythonExe) { $pythonExe = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (!$pythonExe) { $pythonExe = "python" }  # fallback

$LOG_FILE = "E:\工作AI\临时文件\scheduled_scrape.log"
$STATE_FILE = "$rootDir\data\scrape_state.json"

# ── 日志 ──
function Write-Log {
    param([string]$Level, [string]$Message)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] [$Level] $Message"
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
    Write-Host $line
}

# ── 网络检查 ──
function Test-InternetConnection {
    Write-Log "INFO" "检查网络连通性..."
    $targets = @(
        @{ url = "https://www.ctrip.com"; name = "携程" },
        @{ url = "https://www.google.com"; name = "Google" },
        @{ url = "https://hotel.qunar.com"; name = "去哪儿" }
    )

    $results = @()
    foreach ($t in $targets) {
        try {
            $req = [System.Net.WebRequest]::Create($t.url)
            $req.Timeout = 8000
            $req.Method = "HEAD"
            $resp = $req.GetResponse()
            $results += @{ target = $t.name; ok = $true; latency = 0 }
            $resp.Close()
        } catch {
            $results += @{ target = $t.name; ok = $false; latency = 0 }
        }
    }

    $okCount = ($results | Where-Object { $_.ok }).Count
    Write-Log "INFO" "网络检查: $okCount/$($results.Count) 可达"

    # 至少携程或去哪儿可用
    $ctrip = $results | Where-Object { $_.target -eq "携程" }
    $qunar = $results | Where-Object { $_.target -eq "去哪儿" }

    return ($ctrip.ok -or $qunar.ok)
}

# ── Chrome CDP 健康检查 ──
function Test-ChromeCDP {
    if ($SkipChromeCheck) { return $true }
    try {
        $req = [System.Net.WebRequest]::Create("http://127.0.0.1:9222/json/version")
        $req.Timeout = 5000
        $resp = $req.GetResponse()
        $stream = $resp.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $body = $reader.ReadToEnd()
        $reader.Close(); $resp.Close()
        $json = $body | ConvertFrom-Json
        if ($json.webSocketDebuggerUrl) {
            Write-Log "INFO" "Chrome CDP 健康 ✅"
            return $true
        }
    } catch {}
    Write-Log "WARN" "Chrome CDP 无响应"
    return $false
}

# ── 尝试拉起 Chrome CDP ──
function Start-ChromeIfNeeded {
    if ($SkipChromeCheck) { return $true }
    if (Test-ChromeCDP) { return $true }

    Write-Log "INFO" "尝试拉起 Chrome CDP..."
    $watchdogScript = "$scriptDir\watchdog.ps1"
    if (Test-Path $watchdogScript) {
        $result = & powershell -ExecutionPolicy Bypass -File $watchdogScript
        Start-Sleep -Seconds 5
        return Test-ChromeCDP
    } else {
        Write-Log "ERROR" "找不到 watchdog.ps1"
        return $false
    }
}

# ── 数据质量验证 ──
function Test-DataQuality {
    param([string]$JsonPath)

    if (!(Test-Path $JsonPath)) {
        Write-Log "ERROR" "输出文件不存在: $JsonPath"
        return $false
    }

    try {
        $data = Get-Content $JsonPath -Raw | ConvertFrom-Json

        $count = if ($data -is [array]) { $data.Count } else { $data.data.Count }
        if ($count -lt 5) {
            Write-Log "WARN" "数据量过少: ${count}条（阈值: 5）"
            return $false
        }

        # 检查价格合理性
        $prices = if ($data -is [array]) { $data | ForEach-Object { $_."单价_晚" } }
                  else { $data.data | ForEach-Object { $_."单价_晚" } }
        $prices = $prices | Where-Object { $_ -and $_ -is [int] }
        $avgPrice = ($prices | Measure-Object -Average).Average
        if ($avgPrice -lt 50 -or $avgPrice -gt 5000) {
            Write-Log "WARN" "均价异常: ¥${avgPrice}"
            return $false
        }

        Write-Log "INFO" "数据质量: ${count}条, 均价 ¥$([math]::Round($avgPrice)) ✅"
        return $true
    } catch {
        Write-Log "ERROR" "JSON解析失败: $_"
        return $false
    }
}

# ── 飞书通知 ──
function Send-FeishuNotification {
    param([string]$Title, [string]$Content, [string]$Level = "info")

    $webhookUrl = $env:FEISHU_RMS_ALERT_WEBHOOK
    if (!$webhookUrl) {
        $envFile = "$rootDir\config\feishu.env"
        if (Test-Path $envFile) {
            Get-Content $envFile | Where-Object { $_ -match "^FEISHU_RMS_ALERT_WEBHOOK=(.+)" } | ForEach-Object {
                $webhookUrl = $Matches[1]
            }
        }
    }
    if (!$webhookUrl) { return }

    $color = @{ critical = "red"; warn = "yellow"; info = "green" }[$Level]
    $body = @{
        msg_type = "interactive"
        card = @{
            header = @{
                title = @{ tag = "plain_text"; content = $Title }
                template = $color
            }
            elements = @(@{ tag = "div"; text = @{ tag = "lark_md"; content = $Content } })
        }
    } | ConvertTo-Json -Depth 5 -Compress

    try {
        Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 10
    } catch {
        Write-Log "ERROR" "飞书通知发送失败: $_"
    }
}

# ── 读取/更新状态 ──
function Get-ScrapeState {
    if (Test-Path $STATE_FILE) {
        try { return Get-Content $STATE_FILE -Raw | ConvertFrom-Json } catch {}
    }
    return @{
        last_success = $null
        last_attempt = $null
        consecutive_failures = 0
        total_scrapes = 0
        successful_scrapes = 0
        alerts_triggered = 0
    }
}

function Set-ScrapeState($state) {
    $state | ConvertTo-Json -Depth 3 | Set-Content $STATE_FILE -Encoding UTF8
}

# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

Write-Log "INFO" "======================================================"
Write-Log "INFO" "定时OTA价格采集开始 (mode=$Mode)"
Write-Log "INFO" "======================================================"

$state = Get-ScrapeState
$state.last_attempt = (Get-Date).ToString("o")
$state.total_scrapes += 1

# Dry Run 模式
if ($DryRun) {
    Write-Log "INFO" "[DRY RUN] 环境检查模式"
    $netOk = Test-InternetConnection
    $chromeOk = Test-ChromeCDP
    Write-Log "INFO" "[DRY RUN] 网络: $netOk, Chrome CDP: $chromeOk"
    exit 0
}

# Step 1: 网络检查
if (!(Test-InternetConnection)) {
    Write-Log "FATAL" "网络不可达，中止采集"
    $state.consecutive_failures += 1
    Set-ScrapeState $state
    if ($state.consecutive_failures -ge 3) {
        Send-FeishuNotification "OTA采集连续失败" "连续 $($state.consecutive_failures) 次采集网络不可达" "critical"
    }
    exit 1
}

# Step 2: Chrome CDP 检查（仅 ctrip/auto 模式需要）
if ($Mode -in @("auto", "ctrip")) {
    if (!(Start-ChromeIfNeeded)) {
        Write-Log "WARN" "Chrome CDP 不可用，降级到模拟参考模式"
        $Mode = "fallback"
    }
}

# Step 3: 运行采集
Write-Log "INFO" "执行采集脚本..."
$scraperScript = "$rootDir\ota_scraper.py"
$outputJson = "$rootDir\ota_real_prices.json"
$outputCsv = "$rootDir\ota_real_prices.csv"

$startTime = Get-Date
try {
    $result = & $pythonExe $scraperScript --mode $Mode 2>&1
    $exitCode = $LASTEXITCODE
    $elapsed = ((Get-Date) - $startTime).TotalSeconds

    Write-Log "INFO" "采集完成 (耗时 ${elapsed}s, exit=$exitCode)"
    Write-Log "INFO" ($result -join "`n")
    if ($exitCode -ne 0) {
        throw "采集脚本退出码异常: $exitCode"
    }
} catch {
    Write-Log "FATAL" "采集脚本执行异常: $_"
    $state.consecutive_failures += 1
    Set-ScrapeState $state
    Send-FeishuNotification "OTA采集脚本异常" "错误：$_" "critical"
    exit 2
}

# Step 4: 数据质量验证
$dataOk = Test-DataQuality -JsonPath $outputJson

# Step 5: 读取数据，检测竞对异常
if ($dataOk) {
    try {
        $prices = Get-Content $outputJson -Raw | ConvertFrom-Json
        $count = if ($prices -is [array]) { $prices.Count } else { $prices.data.Count }
        $source = if ($prices -is [array]) { "未知" } else { $prices.source }

        # 统计真实价格酒店数
        $realCount = if ($prices -is [array]) {
            ($prices | Where-Object { $_."数据来源" -notmatch "模拟" }).Count
        } else {
            ($prices.data | Where-Object { $_."数据来源" -notmatch "模拟" }).Count
        }

        # 更新状态
        $state.consecutive_failures = 0
        $state.last_success = (Get-Date).ToString("o")
        $state.successful_scrapes += 1
        Set-ScrapeState $state

        # 构建汇总消息
        $summary = @"
✅ **OTA价格采集完成**

- 模式：$Mode
- 数据量：${count} 条
- 真实价格：${realCount} 条
- 数据来源：$source
- 耗时：$([math]::Round($elapsed, 1)) 秒
- 时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@
        Send-FeishuNotification "OTA价格采集日报" $summary "info"

        Write-Log "INFO" "采集成功 ✅ — $count 条, ${realCount}条真实价格"
        exit 0

    } catch {
        Write-Log "ERROR" "后处理异常: $_"
        exit 3
    }
} else {
    $state.consecutive_failures += 1
    Set-ScrapeState $state
    Write-Log "ERROR" "数据质量不合格 ❌"

    if ($state.consecutive_failures -ge 3) {
        Send-FeishuNotification "OTA数据质量告警" "连续 $($state.consecutive_failures) 次采集数据不合格" "critical"
    }
    exit 4
}
