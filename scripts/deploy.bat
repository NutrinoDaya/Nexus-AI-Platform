@echo off
REM NexusAIPlatform - Deployment Script for Windows
REM This script handles the complete deployment of NexusAIPlatform

setlocal enabledelayedexpansion

echo =========================================
echo   NexusAIPlatform Deployment Script
echo =========================================
echo.

REM Check Docker
echo [INFO] Checking dependencies...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)
echo [SUCCESS] Docker found

REM Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose is not installed.
        pause
        exit /b 1
    )
)
echo [SUCCESS] Docker Compose found

REM Check NVIDIA GPU (optional)
nvidia-smi >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] NVIDIA GPU detected
) else (
    echo [WARNING] NVIDIA GPU not detected. Will use CPU for inference.
)

REM Setup environment
echo.
echo [INFO] Setting up environment...
if not exist "config\.env" (
    if exist "config\.env.example" (
        copy "config\.env.example" "config\.env"
        echo [SUCCESS] Created config\.env from example
        echo [WARNING] Please edit config\.env with your settings
        pause
    ) else (
        echo [ERROR] config\.env.example not found
        pause
        exit /b 1
    )
) else (
    echo [SUCCESS] Environment file already exists
)

REM Create directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "models\checkpoints" mkdir "models\checkpoints"
if not exist "models\onnx" mkdir "models\onnx"
if not exist "models\tensorrt" mkdir "models\tensorrt"
echo [SUCCESS] Created data directories

REM Pull images
echo.
echo [INFO] Pulling Docker images...
docker-compose pull
if errorlevel 1 (
    echo [ERROR] Failed to pull images
    pause
    exit /b 1
)
echo [SUCCESS] Docker images pulled

REM Build services
echo.
echo [INFO] Building services...
docker-compose build --parallel
if errorlevel 1 (
    echo [ERROR] Failed to build services
    pause
    exit /b 1
)
echo [SUCCESS] Services built

REM Start services
echo.
echo [INFO] Starting NexusAIPlatform services...

echo [INFO] Starting database and storage services...
docker-compose up -d postgres redis minio
timeout /t 10 /nobreak >nul

echo [INFO] Starting MLflow...
docker-compose up -d mlflow
timeout /t 5 /nobreak >nul

echo [INFO] Starting application services...
docker-compose up -d backend celery-worker frontend

echo [INFO] Starting monitoring services...
docker-compose up -d prometheus grafana

echo [SUCCESS] All services started

REM Run migrations
echo.
echo [INFO] Running database migrations...
docker-compose exec backend alembic upgrade head
if errorlevel 1 (
    echo [WARNING] Database migrations failed (may need manual intervention)
)

REM Initialize storage
echo.
echo [INFO] Initializing object storage...
docker-compose exec backend python -m scripts.init_storage

REM Show status
echo.
echo [INFO] Service status:
docker-compose ps

REM Show access URLs
echo.
echo [SUCCESS] === NexusAIPlatform is now running ===
echo.
echo Access the platform at:
echo   Frontend Dashboard:  http://localhost:3000
echo   Backend API:         http://localhost:8000
echo   API Documentation:   http://localhost:8000/docs
echo   MLflow UI:           http://localhost:5000
echo   MinIO Console:       http://localhost:9001
echo   Grafana Dashboard:   http://localhost:3001 (admin/admin)
echo   Prometheus:          http://localhost:9090
echo.
echo [INFO] Default credentials:
echo   Admin user: admin@NexusAIPlatform.io
echo   Password: changeme (please change on first login)
echo.
echo Press Ctrl+C to stop viewing logs
echo.

REM Show logs
docker-compose logs -f --tail=50

endlocal
