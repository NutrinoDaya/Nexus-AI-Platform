@echo off
REM NexusAIPlatform Docker Image Packaging Script
REM Builds and packages Docker images for distribution

setlocal enabledelayedexpansion

cd /d "%~dp0\.."

set VERSION=%1
if "%VERSION%"=="" set VERSION=latest

set REGISTRY=%2

echo ======================================
echo NexusAIPlatform Docker Packaging
echo ======================================
echo Version: %VERSION%
if not "%REGISTRY%"=="" echo Registry: %REGISTRY%
echo.

REM Build images
echo [1/5] Building backend image...
docker build -f infra/docker/Dockerfile.backend -t NexusAIPlatform-backend:%VERSION% .
if errorlevel 1 (
    echo [ERROR] Failed to build backend image
    exit /b 1
)

echo.
echo [2/5] Building frontend image...
docker build -f infra/docker/Dockerfile.frontend -t NexusAIPlatform-frontend:%VERSION% ./frontend
if errorlevel 1 (
    echo [ERROR] Failed to build frontend image
    exit /b 1
)

echo.
echo [3/5] Creating image archives...
if not exist dist mkdir dist

docker save NexusAIPlatform-backend:%VERSION% | gzip > dist\NexusAIPlatform-backend-%VERSION%.tar.gz
docker save NexusAIPlatform-frontend:%VERSION% | gzip > dist\NexusAIPlatform-frontend-%VERSION%.tar.gz

echo.
echo [4/5] Generating deployment package...
if not exist dist\deploy-%VERSION% mkdir dist\deploy-%VERSION%
copy docker-compose.yml dist\deploy-%VERSION%\ >nul
xcopy config dist\deploy-%VERSION%\config\ /E /I /Y >nul
xcopy scripts dist\deploy-%VERSION%\scripts\ /E /I /Y >nul
copy README.md dist\deploy-%VERSION%\ >nul
copy QUICK_START.md dist\deploy-%VERSION%\ >nul

REM Create load scripts
echo @echo off > dist\deploy-%VERSION%\load-images.bat
echo echo Loading NexusAIPlatform Docker images... >> dist\deploy-%VERSION%\load-images.bat
echo docker load -i NexusAIPlatform-backend-%VERSION%.tar.gz >> dist\deploy-%VERSION%\load-images.bat
echo docker load -i NexusAIPlatform-frontend-%VERSION%.tar.gz >> dist\deploy-%VERSION%\load-images.bat
echo echo Images loaded successfully! >> dist\deploy-%VERSION%\load-images.bat

cd dist
tar -czf NexusAIPlatform-deploy-%VERSION%.tar.gz deploy-%VERSION%
cd ..

echo.
echo [5/5] Pushing to registry (if specified)...
if not "%REGISTRY%"=="" (
    docker tag NexusAIPlatform-backend:%VERSION% %REGISTRY%/NexusAIPlatform-backend:%VERSION%
    docker tag NexusAIPlatform-frontend:%VERSION% %REGISTRY%/NexusAIPlatform-frontend:%VERSION%
    
    echo Pushing backend...
    docker push %REGISTRY%/NexusAIPlatform-backend:%VERSION%
    
    echo Pushing frontend...
    docker push %REGISTRY%/NexusAIPlatform-frontend:%VERSION%
    
    echo Tagged and pushed to %REGISTRY%
) else (
    echo Skipping registry push (no registry specified)
)

echo.
echo ======================================
echo Packaging Complete!
echo ======================================
echo.
echo Generated files:
echo   - dist\NexusAIPlatform-backend-%VERSION%.tar.gz
echo   - dist\NexusAIPlatform-frontend-%VERSION%.tar.gz
echo   - dist\NexusAIPlatform-deploy-%VERSION%.tar.gz
echo.
echo To deploy on another machine:
echo   1. Copy NexusAIPlatform-deploy-%VERSION%.tar.gz to target machine
echo   2. Extract: tar -xzf NexusAIPlatform-deploy-%VERSION%.tar.gz
echo   3. Load images: cd deploy-%VERSION% ^&^& load-images.bat
echo   4. Deploy: scripts\deploy.bat
echo.

REM Show image sizes
echo Image sizes:
dir dist\*.tar.gz
echo.

endlocal
