@echo off
REM Cross-platform start script for Windows
REM Starts all compliance agent services

setlocal enabledelayedexpansion

echo ========================================
echo Starting Compliance Agent Services
echo ========================================
echo.

REM Detect Docker Compose command
docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    docker compose version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Docker Compose is not available
        exit /b 1
    ) else (
        set DOCKER_COMPOSE=docker compose
    )
) else (
    set DOCKER_COMPOSE=docker-compose
)

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found
    echo Please run setup script first: scripts\setup-windows.bat
    exit /b 1
)

echo Starting all services...
%DOCKER_COMPOSE% up -d

echo.
echo Services starting in the background...
echo Use 'scripts\check_health.bat' to verify all services are running
echo Use '%DOCKER_COMPOSE% logs [service-name]' to view logs
echo Use '%DOCKER_COMPOSE% down' to stop all services
echo.