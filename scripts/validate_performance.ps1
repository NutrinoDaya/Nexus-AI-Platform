# NexusAIPlatform Performance Validation Script
# Run this after deployment to verify optimal performance

param(
    [switch]$Verbose,
    [switch]$SkipLoadTest
)

Write-Host "`n=== NexusAIPlatform Performance Validation ===" -ForegroundColor Cyan
Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" -ForegroundColor Gray

$script:PassedTests = 0
$script:FailedTests = 0
$script:Warnings = 0

function Test-Section {
    param([string]$Name)
    Write-Host "`n[$Name]" -ForegroundColor Yellow
}

function Test-Pass {
    param([string]$Message)
    Write-Host "  [PASS] $Message" -ForegroundColor Green
    $script:PassedTests++
}

function Test-Fail {
    param([string]$Message)
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
    $script:FailedTests++
}

function Test-Warn {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
    $script:Warnings++
}

function Test-Info {
    param([string]$Message)
    Write-Host "  ℹ $Message" -ForegroundColor Cyan
}

# =============================================================================
# 1. Check Prerequisites
# =============================================================================
Test-Section "Prerequisites"

# Docker
try {
    $dockerVersion = docker --version
    Test-Pass "Docker installed: $dockerVersion"
} catch {
    Test-Fail "Docker not found. Install Docker Desktop."
    exit 1
}

# Docker Compose
try {
    $composeVersion = docker-compose --version
    Test-Pass "Docker Compose installed: $composeVersion"
} catch {
    Test-Fail "Docker Compose not found."
    exit 1
}

# GPU Check
try {
    $gpuInfo = nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
    if ($gpuInfo) {
        Test-Pass "GPU detected: $gpuInfo"
        $hasGPU = $true
    } else {
        Test-Warn "No GPU detected. CPU-only mode (slower performance)."
        $hasGPU = $false
    }
} catch {
    Test-Warn "nvidia-smi not found. Assuming CPU-only."
    $hasGPU = $false
}

# Disk Space
$drive = Get-PSDrive C
$freeGB = [math]::Round($drive.Free / 1GB, 2)
if ($freeGB -gt 50) {
    Test-Pass "Disk space: ${freeGB}GB free"
} elseif ($freeGB -gt 20) {
    Test-Warn "Disk space: ${freeGB}GB free (50GB+ recommended)"
} else {
    Test-Fail "Disk space: ${freeGB}GB free (insufficient - need 20GB+)"
}

# =============================================================================
# 2. Check Services Status
# =============================================================================
Test-Section "Service Status"

Push-Location d:\github\NexusAIPlatform

$services = @(
    "NexusAIPlatform-postgres",
    "NexusAIPlatform-redis",
    "NexusAIPlatform-minio",
    "NexusAIPlatform-mlflow",
    "NexusAIPlatform-backend",
    "NexusAIPlatform-celery-worker",
    "NexusAIPlatform-frontend",
    "NexusAIPlatform-prometheus",
    "NexusAIPlatform-grafana"
)

$runningServices = docker-compose ps --format json 2>$null | ConvertFrom-Json

foreach ($service in $services) {
    $status = $runningServices | Where-Object { $_.Name -eq $service }
    
    if ($status) {
        if ($status.State -eq "running") {
            if ($status.Health -eq "healthy" -or $status.Service -in @("mlflow", "frontend", "celery-worker")) {
                Test-Pass "$service is running"
            } elseif ($status.Health -eq "starting") {
                Test-Warn "$service is starting (wait 30s and rerun)"
            } else {
                Test-Fail "$service is unhealthy"
            }
        } else {
            Test-Fail "$service is not running ($($status.State))"
        }
    } else {
        Test-Fail "$service not found (run 'docker-compose up -d')"
    }
}

# =============================================================================
# 3. Check Network Connectivity
# =============================================================================
Test-Section "Network Connectivity"

$endpoints = @{
    "Backend API" = "http://localhost:8000/health"
    "Frontend" = "http://localhost:3000"
    "MLflow" = "http://localhost:5000"
    "MinIO" = "http://localhost:9000/minio/health/live"
    "Grafana" = "http://localhost:3001"
}

foreach ($name in $endpoints.Keys) {
    try {
        $url = $endpoints[$name]
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Test-Pass "$name accessible at $url"
        } else {
            Test-Fail "$name returned status $($response.StatusCode)"
        }
    } catch {
        Test-Fail "$name not accessible at $url"
    }
}

# =============================================================================
# 4. Performance Tests
# =============================================================================
Test-Section "Performance Tests"

# API Latency
try {
    $times = @()
    for ($i = 0; $i -lt 10; $i++) {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing | Out-Null
        $sw.Stop()
        $times += $sw.ElapsedMilliseconds
    }
    
    $avgLatency = ($times | Measure-Object -Average).Average
    $maxLatency = ($times | Measure-Object -Maximum).Maximum
    
    if ($avgLatency -lt 50) {
        Test-Pass "API latency: ${avgLatency}ms avg, ${maxLatency}ms max (excellent)"
    } elseif ($avgLatency -lt 100) {
        Test-Pass "API latency: ${avgLatency}ms avg, ${maxLatency}ms max (good)"
    } elseif ($avgLatency -lt 200) {
        Test-Warn "API latency: ${avgLatency}ms avg, ${maxLatency}ms max (acceptable)"
    } else {
        Test-Fail "API latency: ${avgLatency}ms avg, ${maxLatency}ms max (slow)"
    }
} catch {
    Test-Fail "Failed to measure API latency"
}

# Database Connections
try {
    $dbConnections = docker exec NexusAIPlatform-postgres psql -U NexusAIPlatform -t -c "SELECT count(*) FROM pg_stat_activity;" 2>$null
    $dbConnections = [int]$dbConnections.Trim()
    
    if ($dbConnections -gt 0 -and $dbConnections -lt 100) {
        Test-Pass "Database connections: $dbConnections (healthy)"
    } elseif ($dbConnections -ge 100) {
        Test-Warn "Database connections: $dbConnections (high - check for leaks)"
    } else {
        Test-Fail "Database connections: $dbConnections (error)"
    }
} catch {
    Test-Warn "Failed to check database connections"
}

# Redis Latency
try {
    $redisLatency = docker exec NexusAIPlatform-redis redis-cli -a redis_secret --latency-history 1 2>$null | Select-String "min"
    if ($redisLatency -match "min: (\d+\.\d+)") {
        $minLatency = [double]$matches[1]
        if ($minLatency -lt 1) {
            Test-Pass "Redis latency: ${minLatency}ms (excellent)"
        } elseif ($minLatency -lt 5) {
            Test-Pass "Redis latency: ${minLatency}ms (good)"
        } else {
            Test-Warn "Redis latency: ${minLatency}ms (slow)"
        }
    }
} catch {
    Test-Warn "Failed to check Redis latency"
}

# GPU Utilization (if available)
if ($hasGPU) {
    try {
        $gpuUtil = nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits
        $gpuUtil = [int]$gpuUtil
        
        Test-Info "GPU utilization: ${gpuUtil}% (run inference to increase)"
        
        $gpuMemUsed = nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits
        $gpuMemTotal = nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits
        Test-Info "GPU memory: ${gpuMemUsed}MB / ${gpuMemTotal}MB"
    } catch {
        Test-Warn "Failed to check GPU utilization"
    }
}

# =============================================================================
# 5. Configuration Validation
# =============================================================================
Test-Section "Configuration Validation"

# Check environment file
if (Test-Path "config\.env") {
    Test-Pass "config\.env exists"
    
    $envContent = Get-Content "config\.env" -Raw
    
    # Check for default passwords (security risk)
    $defaultPasswords = @(
        "NexusAIPlatform_secret",
        "redis_secret",
        "minioadmin_secret",
        "dev_secret_key"
    )
    
    $foundDefaults = @()
    foreach ($pwd in $defaultPasswords) {
        if ($envContent -match [regex]::Escape($pwd)) {
            $foundDefaults += $pwd
        }
    }
    
    if ($foundDefaults.Count -eq 0) {
        Test-Pass "No default passwords found (secure)"
    } else {
        Test-Warn "Default passwords found: $($foundDefaults -join ', ') (change in production!)"
    }
    
    # Check optimized settings
    $optimizations = @{
        "WORKERS=8" = "Server workers optimized"
        "LOG_LEVEL=WARNING" = "Logging optimized"
        "DB_POOL_SIZE=50" = "Database pool optimized"
        "INFERENCE_BATCH_SIZE=16" = "Inference batch optimized"
    }
    
    foreach ($setting in $optimizations.Keys) {
        if ($envContent -match [regex]::Escape($setting)) {
            Test-Pass $optimizations[$setting]
        } else {
            Test-Warn "$setting not found (may not be optimized)"
        }
    }
    
} else {
    Test-Fail "config\.env not found (copy from config\.env.example)"
}

# =============================================================================
# 6. Resource Usage
# =============================================================================
Test-Section "Resource Usage"

$stats = docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" 2>$null

if ($stats) {
    Test-Info "Container Resource Usage:"
    $stats | ForEach-Object {
        $parts = $_ -split ','
        $name = $parts[0]
        $cpu = $parts[1]
        $mem = $parts[2]
        
        if ($name -like "NexusAIPlatform-*") {
            Write-Host "    $name - CPU: $cpu, Memory: $mem" -ForegroundColor Gray
        }
    }
    Test-Pass "Resource monitoring active"
} else {
    Test-Warn "Failed to get container stats"
}

# =============================================================================
# 7. Load Test (Optional)
# =============================================================================
if (-not $SkipLoadTest) {
    Test-Section "Load Test (50 concurrent requests)"
    
    try {
        $jobs = @()
        $successCount = 0
        $failCount = 0
        
        Write-Host "  Running..." -ForegroundColor Gray
        
        for ($i = 0; $i -lt 50; $i++) {
            $jobs += Start-Job -ScriptBlock {
                try {
                    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
                    return @{ Success = $true; StatusCode = $response.StatusCode }
                } catch {
                    return @{ Success = $false; Error = $_.Exception.Message }
                }
            }
        }
        
        $results = $jobs | Wait-Job | Receive-Job
        $jobs | Remove-Job
        
        $successCount = ($results | Where-Object { $_.Success }).Count
        $successRate = [math]::Round(($successCount / 50) * 100, 1)
        
        if ($successRate -ge 95) {
            Test-Pass "Load test: $successCount/50 requests succeeded (${successRate}%)"
        } elseif ($successRate -ge 80) {
            Test-Warn "Load test: $successCount/50 requests succeeded (${successRate}%)"
        } else {
            Test-Fail "Load test: $successCount/50 requests succeeded (${successRate}%)"
        }
        
    } catch {
        Test-Fail "Load test failed: $_"
    }
} else {
    Test-Info "Load test skipped (use -SkipLoadTest:$false to enable)"
}

# =============================================================================
# Summary
# =============================================================================
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "  [PASS] Passed: $PassedTests" -ForegroundColor Green
if ($FailedTests -gt 0) {
    Write-Host "  [FAIL] Failed: $FailedTests" -ForegroundColor Red
}
if ($Warnings -gt 0) {
    Write-Host "  [WARN] Warnings: $Warnings" -ForegroundColor Yellow
}

$totalTests = $PassedTests + $FailedTests
$successRate = [math]::Round(($PassedTests / $totalTests) * 100, 1)

Write-Host "`n  Overall: ${successRate}% passed" -ForegroundColor $(if ($successRate -ge 80) { "Green" } else { "Red" })

if ($FailedTests -eq 0 -and $Warnings -eq 0) {
    Write-Host "`n[SUCCESS] All checks passed! System is ready for testing." -ForegroundColor Green
} elseif ($FailedTests -eq 0) {
    Write-Host "`n[PASS] System is operational with minor warnings." -ForegroundColor Yellow
} else {
    Write-Host "`n[WARN] System has issues that need attention." -ForegroundColor Red
}

Write-Host "`n$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" -ForegroundColor Gray

Pop-Location

# Return exit code
if ($FailedTests -eq 0) {
    exit 0
} else {
    exit 1
}
