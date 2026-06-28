# Temple Site 一键启动脚本（云端隧道版）
# 双击运行即可让网站 24 小时上线
Write-Host "===== Temple Site 云端启动 =====" -ForegroundColor Cyan

$projectDir = "F:\temple-site"
$cfExe = "$env:USERPROFILE\cloudflared\cloudflared.exe"
$cfLog = "$env:USERPROFILE\cloudflared\tunnel.log"
$port = 5000

# Find Python
$python = Get-Command "py" -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command "python3" -ErrorAction SilentlyContinue }
if (-not $python) { $python = Get-Command "python" -ErrorAction SilentlyContinue }

# 1. Kill old processes
Write-Host "[1/3] 关闭旧进程..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
        if ($cmd -match "app.py") {
            Write-Host "  - 停止 Flask (PID: $($_.Id))" -ForegroundColor Gray
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    } catch {}
}
Get-Process | Where-Object { $_.ProcessName -match "cloudflared" } | ForEach-Object {
    Write-Host "  - 停止隧道 (PID: $($_.Id))" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# 2. Start Flask
Write-Host "[2/3] 启动 Flask 网站..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $python.Source -ArgumentList "app.py" -WorkingDirectory $projectDir
Write-Host "  ✓ Flask 已启动 (http://localhost:$port)" -ForegroundColor Green
Start-Sleep -Seconds 3

# 3. Start Tunnel
Write-Host "[3/3] 启动 Cloudflare Tunnel..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $cfExe `
  -ArgumentList "tunnel --url http://localhost:$port --logfile `"$cfLog`" --metrics localhost:53112"
Write-Host "  ✓ 隧道已启动" -ForegroundColor Green
Start-Sleep -Seconds 10

# 4. Show public URL
if (Test-Path $cfLog) {
    $log = Get-Content $cfLog -Tail 30
    $urlLine = $log | Where-Object { $_ -match "trycloudflare" } | Select-Object -First 1
    if ($urlLine -match "https://([^\s]+)") {
        $publicUrl = $Matches[0].Trim()
        Write-Host "`n=======================================" -ForegroundColor Green
        Write-Host "  网站已上线！全球访问地址：" -ForegroundColor Cyan
        Write-Host "  $publicUrl" -ForegroundColor White
        Write-Host "=======================================" -ForegroundColor Green
        Write-Host "`n(只要电脑不关机，链接永久有效)" -ForegroundColor Gray
        Start-Process $publicUrl
    }
}

Write-Host "`n管理后台: http://localhost:$port/admin" -ForegroundColor White
Write-Host "管理密码: temple2026" -ForegroundColor White
Write-Host "`n按任意键关闭（会断开隧道）..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
