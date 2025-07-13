# PowerShell script to stop BaseX and Redis services for dictionary application

Write-Host "Stopping dictionary services (BaseX and Redis)..." -ForegroundColor Yellow

# Stop Redis Docker container
Write-Host "Stopping Redis container..." -ForegroundColor Cyan
try {
    $redisRunning = docker ps -q --filter "name=redis"
    if ($redisRunning) {
        docker stop redis
        docker rm redis
        Write-Host "✓ Redis container stopped and removed" -ForegroundColor Green
    } else {
        Write-Host "Redis container not running" -ForegroundColor Gray
    }
} catch {
    Write-Host "Error stopping Redis container: $($_.Exception.Message)" -ForegroundColor Red
}

###########################################################
# Stop Flask/Python processes (to prevent stale servers)   #
###########################################################
Write-Host "Stopping Flask/Python processes..." -ForegroundColor Cyan
try {
    # Kill all python.exe processes running Flask (Windows only)
    $flaskProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -match "flask" -or $_.CommandLine -match "run.py" -or $_.CommandLine -match "app.py"
    }
    if ($flaskProcesses) {
        foreach ($process in $flaskProcesses) {
            Write-Host "Stopping Flask/Python process (PID: $($process.Id))..." -ForegroundColor White
            Stop-Process -Id $process.Id -Force
        }
        Write-Host "✓ Flask/Python processes stopped" -ForegroundColor Green
    } else {
        Write-Host "No Flask/Python processes found" -ForegroundColor Gray
    }
} catch {
    Write-Host "Error stopping Flask/Python processes: $($_.Exception.Message)" -ForegroundColor Red
}

# Stop BaseX Server processes
Write-Host "Stopping BaseX Server..." -ForegroundColor Cyan
try {
    $basexProcesses = Get-Process -Name "java" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*basex*" -or 
        $_.MainWindowTitle -like "*BaseX*" -or
        $_.ProcessName -eq "basexserver"
    }
    
    if ($basexProcesses) {
        foreach ($process in $basexProcesses) {
            Write-Host "Stopping BaseX process (PID: $($process.Id))..." -ForegroundColor White
            Stop-Process -Id $process.Id -Force
        }
        Write-Host "✓ BaseX Server stopped" -ForegroundColor Green
    } else {
        # Alternative approach - kill any java process using port 1984
        $portProcess = Get-NetTCPConnection -LocalPort 1984 -ErrorAction SilentlyContinue
        if ($portProcess) {
            $processId = $portProcess.OwningProcess
            Write-Host "Stopping process using port 1984 (PID: $processId)..." -ForegroundColor White
            Stop-Process -Id $processId -Force
            Write-Host "✓ BaseX Server stopped" -ForegroundColor Green
        } else {
            Write-Host "BaseX Server not running" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "Error stopping BaseX: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "You may need to manually close the BaseX server window" -ForegroundColor Yellow
}

# Verify services are stopped
Write-Host "`nVerifying services are stopped..." -ForegroundColor Cyan

# Check Redis
$redisCheck = docker ps -q --filter "name=redis"
if ($redisCheck) {
    Write-Host "⚠ Redis container still running" -ForegroundColor Yellow
} else {
    Write-Host "✓ Redis stopped" -ForegroundColor Green
}

# Check BaseX port
try {
    $basexPort = Test-NetConnection -ComputerName localhost -Port 1984 -WarningAction SilentlyContinue
    if ($basexPort.TcpTestSucceeded) {
        Write-Host "⚠ BaseX port 1984 still in use" -ForegroundColor Yellow
    } else {
        Write-Host "✓ BaseX stopped" -ForegroundColor Green
    }
} catch {
    Write-Host "✓ BaseX stopped" -ForegroundColor Green
}

Write-Host "`nAll services stopped successfully!" -ForegroundColor Green
