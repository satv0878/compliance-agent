@echo off
REM Health check script for Windows
REM Checks if all compliance agent services are running correctly

echo ========================================
echo Compliance Agent Health Check
echo ========================================
echo.

REM Check if curl is available, if not use PowerShell
where curl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set CURL_CMD=curl -s -o nul -w "%%{http_code}"
) else (
    echo Using PowerShell for HTTP requests...
    set CURL_CMD=powershell -Command "(Invoke-WebRequest -Uri 
)

echo Checking service health...
echo.

REM Check each service
echo Checking Ingress Service (port 8000)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/health' -Method GET -UseBasicParsing; Write-Host '[OK] Ingress service is healthy' -ForegroundColor Green } catch { Write-Host '[FAIL] Ingress service is not responding' -ForegroundColor Red }"

echo Checking Parser Service (port 8001)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8001/health' -Method GET -UseBasicParsing; Write-Host '[OK] Parser service is healthy' -ForegroundColor Green } catch { Write-Host '[FAIL] Parser service is not responding' -ForegroundColor Red }"

echo Checking Validator Service (port 8002)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8002/health' -Method GET -UseBasicParsing; Write-Host '[OK] Validator service is healthy' -ForegroundColor Green } catch { Write-Host '[FAIL] Validator service is not responding' -ForegroundColor Red }"

echo Checking HashWriter Service (port 8003)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8003/health' -Method GET -UseBasicParsing; Write-Host '[OK] HashWriter service is healthy' -ForegroundColor Green } catch { Write-Host '[FAIL] HashWriter service is not responding' -ForegroundColor Red }"

echo Checking Reporter Service (port 8004)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8004/health' -Method GET -UseBasicParsing; Write-Host '[OK] Reporter service is healthy' -ForegroundColor Green } catch { Write-Host '[FAIL] Reporter service is not responding' -ForegroundColor Red }"

echo.
echo Checking infrastructure services...
echo.

echo Checking Elasticsearch (port 9200)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:9200/_cluster/health' -Method GET -UseBasicParsing -Credential (New-Object PSCredential('elastic', (ConvertTo-SecureString 'changeme' -AsPlainText -Force))); $health = ($response.Content | ConvertFrom-Json).status; Write-Host \"[OK] Elasticsearch is $health\" -ForegroundColor Green } catch { Write-Host '[FAIL] Elasticsearch is not responding' -ForegroundColor Red }"

echo Checking MinIO (port 9000)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:9000/minio/health/live' -Method GET -UseBasicParsing; Write-Host '[OK] MinIO is healthy' -ForegroundColor Green } catch { Write-Host '[FAIL] MinIO is not responding' -ForegroundColor Red }"

echo Checking Kibana (port 5601)...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5601/api/status' -Method GET -UseBasicParsing; Write-Host '[OK] Kibana is healthy' -ForegroundColor Green } catch { Write-Host '[FAIL] Kibana is not responding' -ForegroundColor Red }"

echo.
echo ========================================
echo Health check completed
echo ========================================
echo.
echo Web interfaces:
echo - Kibana: http://localhost:5601 (elastic/changeme)
echo - MinIO: http://localhost:9001 (minioadmin/minioadmin)
echo.