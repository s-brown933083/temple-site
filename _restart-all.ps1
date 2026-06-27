# Temple Site 一键重启脚本
# 双击运行此脚本即可重启网站 + 隧道
# 无需管理员权限

$pfPy = "C:\Program Files\Python312\python.exe"
$cfPath = "C:\cloudflared\cloudflared-new.exe"
$logFile = "C:\cloudflared\tunnel.log"
$port = 5000

Write-Host "===== Temple Site 重启工具 =====" -ForegroundColor Cyan

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
$env:PORT = "$port"
Start-Process -NoNewWindow -FilePath $pfPy -ArgumentList "app.py" -WorkingDirectory "F:\temple-site"
Write-Host "  ✓ Flask 已启动 (http://localhost:$port)" -ForegroundColor Green

# 3. Start Tunnel
Write-Host "[3/3] 启动 Cloudflare 隧道..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath $cfPath -ArgumentList "tunnel --url http://localhost:$port --logfile `"$logFile`" --metrics localhost:53112"
Write-Host "  ✓ 隧道已启动" -ForegroundColor Green

Start-Sleep -Seconds 10

# 4. Show URL
if (Test-Path $logFile) {
    $log = Get-Content $logFile -Tail 30
    $urlLine = $log | Where-Object { $_ -match "trycloudflare" } | Select-Object -First 1
    if ($urlLine -match "https://([^\s]+)") {
        $url = $Matches[0].Trim()
        Write-Host "`n===== 网站已上线！ =====" -ForegroundColor Green
        Write-Host "全球访问地址: $url" -ForegroundColor Cyan
        Write-Host "(链接有效期至电脑关机，重启后需重新获取)" -ForegroundColor Gray
        # Open browser
        Start-Process "https://$url"
    }
}

Write-Host "`n管理后台: http://localhost:$port/admin" -ForegroundColor White
Write-Host "管理密码: temple2026" -ForegroundColor White
Write-Host "`n按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
