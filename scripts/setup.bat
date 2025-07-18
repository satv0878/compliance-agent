@echo off
REM Compliance Agent Setup Script for Windows
REM This script sets up the initial environment for the compliance agent

echo ========================================
echo Compliance Agent Setup for Windows
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop for Windows from https://www.docker.com/products/docker-desktop
    exit /b 1
)

REM Check if Docker Compose is installed (try both commands)
docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    docker compose version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Docker Compose is not installed
        echo Docker Compose should be included with Docker Desktop
        exit /b 1
    ) else (
        set DOCKER_COMPOSE=docker compose
    )
) else (
    set DOCKER_COMPOSE=docker-compose
)

echo [1/6] Creating directory structure...
REM Create required directories
if not exist "data" mkdir data
if not exist "data\elasticsearch" mkdir data\elasticsearch
if not exist "data\minio" mkdir data\minio
if not exist "certs" mkdir certs
if not exist "logs" mkdir logs
if not exist "logs\ingress" mkdir logs\ingress
if not exist "logs\parser" mkdir logs\parser
if not exist "logs\validator" mkdir logs\validator
if not exist "logs\hashwriter" mkdir logs\hashwriter
if not exist "logs\reporter" mkdir logs\reporter

echo [2/6] Checking environment configuration...
REM Check if .env exists, if not copy from .env.example
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env >nul
        echo.
        echo IMPORTANT: Please edit .env file to configure your environment
        echo Press any key to continue after editing .env...
        pause >nul
    ) else (
        echo ERROR: .env.example not found!
        exit /b 1
    )
)

echo [3/6] Generating self-signed certificates...
REM Generate self-signed certificates using Docker
docker run --rm -v "%cd%\certs:/certs" alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/server.key -out /certs/server.crt -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Certificates generated successfully
) else (
    echo Warning: Certificate generation failed, continuing anyway...
)

echo [4/6] Starting infrastructure services...
REM Start only infrastructure services first
%DOCKER_COMPOSE% up -d elasticsearch minio

echo [5/6] Waiting for services to initialize...
REM Wait for Elasticsearch (Windows doesn't have built-in curl, so we use a timeout)
echo Waiting 60 seconds for Elasticsearch to start...
timeout /t 60 /nobreak >nul

echo [6/6] Creating MinIO buckets...
REM Create MinIO buckets
%DOCKER_COMPOSE% exec -T minio sh -c "mc alias set myminio http://localhost:9000 minioadmin minioadmin && mc mb -p myminio/compliance-audit && mc mb -p myminio/compliance-reports && echo 'MinIO buckets created successfully' || echo 'Buckets may already exist'"

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Start all services: %DOCKER_COMPOSE% up -d
echo 2. Check service health: Run check_health.bat
echo 3. Run tests: python scripts\test_ingestion.py
echo.
echo For detailed instructions, see SETUP_GUIDE.md
echo.