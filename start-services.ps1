# PowerShell script to start BaseX and Redis services for dictionary application
# This script uses local BaseX installation and Docker for Redis

Write-Host "Starting dictionary services (BaseX and Redis)..." -ForegroundColor Green

# BaseX local installation path
$basexPath = "C:\Program Files (x86)\BaseX\bin\basexserver.bat"

# Check if BaseX is installed
if (!(Test-Path $basexPath)) {
    Write-Host "Error: BaseX not found at $basexPath" -ForegroundColor Red
    Write-Host "Please verify BaseX installation path." -ForegroundColor Yellow
    exit 1
}

# Check if Docker is running for Redis
try {
    docker version *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error: Docker is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Start BaseX Server
Write-Host "Starting BaseX Server (local installation)..." -ForegroundColor Cyan
$basexProcess = Start-Process -FilePath $basexPath -WindowStyle Minimized -PassThru
Start-Sleep 3

# Check if BaseX is running
try {
    $tcpTest = Test-NetConnection -ComputerName localhost -Port 1984 -WarningAction SilentlyContinue
    if ($tcpTest.TcpTestSucceeded) {
        Write-Host "✓ BaseX Server started successfully on port 1984" -ForegroundColor Green
    } else {
        Write-Host "Warning: BaseX may still be starting up..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Warning: Could not verify BaseX connection" -ForegroundColor Yellow
}

# Start Redis via Docker
Write-Host "Starting Redis (Docker)..." -ForegroundColor Cyan
docker run -d --name redis -p 6379:6379 redis:8

# Wait for Redis to be ready
Write-Host "Waiting for Redis to be ready..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0

while ($waited -lt $maxWait) {
    try {
        $redisTest = docker exec redis redis-cli ping 2>$null
        if ($redisTest -eq "PONG") {
            Write-Host "✓ Redis is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    Write-Host "Waiting for Redis... (${waited}s)" -ForegroundColor Yellow
    Start-Sleep 2
    $waited += 2
}

if ($waited -ge $maxWait) {
    Write-Host "Warning: Redis may not be fully ready yet." -ForegroundColor Yellow
}

Write-Host "`nService Status:" -ForegroundColor Cyan
Write-Host "- BaseX Server: Running (PID: $($basexProcess.Id))" -ForegroundColor White
docker ps --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`nService URLs:" -ForegroundColor Cyan
Write-Host "- BaseX Web Interface: http://localhost:8984/dba" -ForegroundColor White
Write-Host "- BaseX Client Port: 1984" -ForegroundColor White
Write-Host "- Redis Port: 6379" -ForegroundColor White

Write-Host "`nTo stop services:" -ForegroundColor Yellow
Write-Host "- BaseX: Close the BaseX server window or kill process $($basexProcess.Id)" -ForegroundColor White
Write-Host "- Redis: docker stop redis && docker rm redis" -ForegroundColor White
