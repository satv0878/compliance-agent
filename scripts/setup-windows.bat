@echo off
REM Enhanced Windows Setup Script for Compliance Agent
REM This script ensures proper setup on Windows systems

setlocal enabledelayedexpansion

echo ========================================
echo Compliance Agent Setup for Windows
echo ========================================
echo.

REM Check if Docker Desktop is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker Desktop is not running
    echo Please start Docker Desktop and try again
    exit /b 1
)

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
        echo Using Docker Compose plugin
    )
) else (
    set DOCKER_COMPOSE=docker-compose
    echo Using standalone Docker Compose
)

echo [1/7] Creating directory structure...
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

echo [2/7] Checking environment configuration...
REM Check if .env exists, if not copy from .env.example
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env >nul
        echo.
        echo IMPORTANT: Please edit .env file to configure your environment
        echo Default credentials: elastic/changeme, minioadmin/minioadmin
        echo.
    ) else (
        echo ERROR: .env.example not found!
        exit /b 1
    )
) else (
    echo .env file already exists
)

echo [3/7] Generating self-signed certificates...
REM Generate self-signed certificates using Docker
if not exist "certs\server.crt" (
    docker run --rm -v "%cd%\certs:/certs" alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/server.key -out /certs/server.crt -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" >nul 2>&1
    
    if !ERRORLEVEL! EQU 0 (
        echo Certificates generated successfully
    ) else (
        echo Warning: Certificate generation failed, continuing anyway...
    )
) else (
    echo Certificates already exist
)

echo [4/7] Cleaning up any existing containers...
%DOCKER_COMPOSE% down >nul 2>&1

echo [5/7] Starting infrastructure services...
REM Start only infrastructure services first
%DOCKER_COMPOSE% up -d elasticsearch minio

echo [6/7] Waiting for services to initialize...
REM Wait for services to be ready
echo Waiting for Elasticsearch to start...
timeout /t 30 /nobreak >nul

REM Check if Elasticsearch is ready
for /L %%i in (1,1,12) do (
    powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:9200/_cluster/health' -UseBasicParsing -Credential (New-Object PSCredential('elastic', (ConvertTo-SecureString 'changeme' -AsPlainText -Force))) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo Elasticsearch is ready
        goto :elasticsearch_ready
    )
    echo Waiting for Elasticsearch... (attempt %%i/12)
    timeout /t 10 /nobreak >nul
)
echo Warning: Elasticsearch may not be ready, continuing anyway...

:elasticsearch_ready
echo [7/7] Creating MinIO buckets...
REM Create MinIO buckets
%DOCKER_COMPOSE% exec -T minio sh -c "mc alias set myminio http://localhost:9000 minioadmin minioadmin && mc mb -p myminio/compliance-audit && mc mb -p myminio/compliance-reports && echo 'MinIO buckets created successfully'" >nul 2>&1

if !ERRORLEVEL! EQU 0 (
    echo MinIO buckets created successfully
) else (
    echo Warning: MinIO bucket creation failed, they may already exist
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Start all services: %DOCKER_COMPOSE% up -d
echo 2. Check service health: scripts\check_health.bat
echo 3. Run tests: python scripts\test_ingestion.py
echo.
echo Web interfaces:
echo - Kibana: http://localhost:5601 (elastic/changeme)
echo - MinIO: http://localhost:9001 (minioadmin/minioadmin)
echo.
echo For detailed instructions, see SETUP_GUIDE.md
echo.