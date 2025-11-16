@echo off
REM NexusAIPlatform Monitoring Script
REM Monitors system health, logs, and resource usage

setlocal enabledelayedexpansion

echo ======================================
echo NexusAIPlatform System Monitor
echo ======================================
echo.

cd /d "%~dp0\.."

REM Check if docker-compose is running
docker-compose ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Services are not running. Start with: docker-compose up -d
    exit /b 1
)

REM Check service health
echo Service Status:
echo ----------------------------------------
call :check_service postgres
call :check_service redis
call :check_service minio
call :check_service mlflow
call :check_service backend
call :check_service celery-worker
call :check_service frontend
call :check_service prometheus
call :check_service grafana
echo.

REM Resource usage
echo Resource Usage:
echo ----------------------------------------
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | findstr NexusAIPlatform
echo.

REM Recent errors
echo Recent Errors (last 10 minutes):
echo ----------------------------------------
for /f %%i in ('docker-compose logs --tail 1000 2^>^&1 ^| findstr /i "error" ^| find /c /v ""') do set ERROR_COUNT=%%i

if !ERROR_COUNT! gtr 0 (
    echo Found !ERROR_COUNT! errors
    docker-compose logs --tail 1000 2>&1 | findstr /i "error" | more +1
) else (
    echo [OK] No errors found
)
echo.

REM API Health Check
echo API Health Check:
echo ----------------------------------------
for /f %%i in ('curl -s -o nul -w "%%{http_code}" http://localhost:8000/health') do set HEALTH_CODE=%%i

if "!HEALTH_CODE!"=="200" (
    echo [OK] API is responding (HTTP !HEALTH_CODE!)
    echo.
    echo API Metrics:
    curl -s http://localhost:8000/metrics 2>nul | findstr /r "http_requests_total http_request_duration"
) else (
    echo [FAIL] API is not responding (HTTP !HEALTH_CODE!)
)
echo.

REM Database connections
echo Database Status:
echo ----------------------------------------
for /f "tokens=*" %%i in ('docker exec NexusAIPlatform-postgres psql -U NexusAIPlatform -t -c "SELECT count(*) FROM pg_stat_activity;" 2^>nul') do set DB_CONN=%%i
echo Active connections: !DB_CONN!
echo.

REM Redis status
echo Redis Status:
echo ----------------------------------------
docker exec NexusAIPlatform-redis redis-cli -a redis_secret INFO stats 2>nul | findstr /r "total_commands_processed keyspace"
echo.

REM Disk usage
echo Disk Usage:
echo ----------------------------------------
wmic logicaldisk get deviceid,freespace,size 2>nul | findstr "C:"
echo.

echo ======================================
echo Monitor Options:
echo ======================================
echo 1. Watch logs:       docker-compose logs -f
echo 2. Specific service: docker-compose logs -f ^<service^>
echo 3. Restart service:  docker-compose restart ^<service^>
echo 4. View Grafana:     http://localhost:3001
echo 5. View Prometheus:  http://localhost:9090
echo.

goto :eof

:check_service
set SERVICE=%1
for /f %%i in ('docker-compose ps -q %SERVICE% 2^>nul') do set CONTAINER_ID=%%i

if "!CONTAINER_ID!"=="" (
    echo [DOWN] %SERVICE%
    goto :eof
)

for /f %%i in ('docker inspect --format="{{.State.Status}}" !CONTAINER_ID! 2^>nul') do set STATUS=%%i

if "!STATUS!"=="running" (
    echo [HEALTHY] %SERVICE%
) else (
    echo [STOPPED] %SERVICE%
)
goto :eof
