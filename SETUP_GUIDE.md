# Compliance Agent Setup & Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Service Startup Order](#service-startup-order)
4. [Verification Steps](#verification-steps)
5. [Common Issues & Solutions](#common-issues--solutions)
6. [Production Deployment](#production-deployment)

## Prerequisites

### System Requirements
- **OS**: Windows 10/11, Linux (Ubuntu 20.04+ recommended), or macOS
- **RAM**: 8GB minimum (16GB recommended for production)
- **Storage**: 20GB minimum free space
- **CPU**: 4 cores minimum

### Software Requirements

#### Windows
```batch
# Install Docker Desktop for Windows from:
# https://www.docker.com/products/docker-desktop

# Verify installation (run in Command Prompt or PowerShell)
docker --version
docker-compose --version

# Install Python 3.8+ from:
# https://www.python.org/downloads/

# Verify Python installation
python --version
```

#### Linux/macOS
```bash
# Check Docker version (20.10+ required)
docker --version

# Check Docker Compose version (2.0+ required)
docker-compose --version

# Check Python version (3.8+ required for scripts)
python3 --version

# Linux only: Increase VM memory for Elasticsearch
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

### Windows-Specific Requirements
- Enable WSL2 (Windows Subsystem for Linux) for Docker Desktop
- Ensure Hyper-V is enabled
- Docker Desktop must be running before executing commands

## Initial Setup

### 1. Clone Repository

#### Windows
```batch
git clone <repository-url>
cd compliance-agent
```

#### Linux/macOS
```bash
git clone <repository-url>
cd compliance-agent
```

### 2. Environment Configuration

#### Windows
```batch
# Copy example environment file
copy .env.example .env

# Edit .env file with your settings using notepad or any text editor
notepad .env
```

#### Linux/macOS
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
nano .env
```

**Critical .env settings to review:**
```bash
# API Configuration
API_HOST=0.0.0.0
INGRESS_PORT=8000
PARSER_PORT=8001
VALIDATOR_PORT=8002
HASHWRITER_PORT=8003
REPORTER_PORT=8004

# Elasticsearch
ES_HOST=elasticsearch
ES_PORT=9200
ES_USER=elastic
ES_PASSWORD=changeme  # CHANGE IN PRODUCTION!

# MinIO/S3
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin      # CHANGE IN PRODUCTION!
S3_SECRET_KEY=minioadmin      # CHANGE IN PRODUCTION!
S3_BUCKET=compliance-data

# Security
JWT_SECRET_KEY=your-secret-key-here  # CHANGE THIS!
```

### 3. Create Required Directories

#### Windows
```batch
# Create directories for volumes
mkdir data\elasticsearch
mkdir data\minio
mkdir data\certs
mkdir logs\ingress
mkdir logs\parser
mkdir logs\validator
mkdir logs\hashwriter
mkdir logs\reporter
```

#### Linux/macOS
```bash
# Create directories for volumes
mkdir -p data/{elasticsearch,minio,certs}
mkdir -p logs/{ingress,parser,validator,hashwriter,reporter}

# Set permissions
chmod -R 755 data/
chmod -R 755 logs/
```

### 4. Run Setup Script

#### Windows
```batch
# Run setup script (generates certs, creates buckets, etc.)
scripts\setup.bat
```

#### Linux/macOS
```bash
# Make setup script executable
chmod +x scripts/setup.sh

# Run setup (generates certs, creates buckets, etc.)
./scripts/setup.sh
```

## Service Startup Order

### Option 1: Full Stack Startup (Recommended)
```bash
# Start all services with dependency management
docker-compose up -d

# Monitor startup logs
docker-compose logs -f
```

### Option 2: Manual Service-by-Service Startup
```bash
# 1. Start infrastructure services first
docker-compose up -d elasticsearch minio

# Wait for Elasticsearch to be ready (30-60 seconds)
until curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green\|yellow"'; do
    echo "Waiting for Elasticsearch..."
    sleep 5
done

# 2. Start Logstash for index templates
docker-compose up -d logstash

# 3. Start Kibana for monitoring
docker-compose up -d kibana

# 4. Start application services
docker-compose up -d hashwriter parser validator ingress

# 5. Finally start reporter service
docker-compose up -d reporter
```

## Verification Steps

### 1. Check All Services Are Running
```bash
# Check Docker containers
docker-compose ps

# All services should show "Up" status
```

### 2. Health Check All Endpoints

#### Windows
```batch
# Run the health check script
scripts\check_health.bat
```

#### Linux/macOS
```bash
# Run the health check script
chmod +x scripts/check_health.sh
./scripts/check_health.sh
```

### 3. Test Basic Functionality

#### Windows
```batch
# Run the test ingestion script
python scripts\test_ingestion.py

# Expected output:
# ✓ HL7 message ingested successfully
# ✓ Validation rules retrieved
# ✓ Metrics endpoint accessible
```

#### Linux/macOS
```bash
# Run the test ingestion script
python3 scripts/test_ingestion.py

# Expected output:
# ✓ HL7 message ingested successfully
# ✓ Validation rules retrieved
# ✓ Metrics endpoint accessible
```

### 4. Verify Elasticsearch Indices
```bash
# List Elasticsearch indices
curl -X GET "localhost:9200/_cat/indices?v"

# You should see:
# - compliance-messages-*
# - compliance-audit-*
```

### 5. Access Web Interfaces
- **Kibana**: http://localhost:5601 (elastic/changeme)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## Common Issues & Solutions

### Issue 1: Elasticsearch Won't Start

#### Linux
```bash
# Error: "max virtual memory areas vm.max_map_count [65530] is too low"
# Solution:
sudo sysctl -w vm.max_map_count=262144

# Error: "Elasticsearch exited with code 78"
# Solution: Check disk space and permissions
df -h
sudo chown -R 1000:1000 data/elasticsearch/
```

#### Windows
```batch
# Error: "Elasticsearch container keeps restarting"
# Solution: Increase Docker Desktop memory allocation
# 1. Open Docker Desktop
# 2. Go to Settings > Resources
# 3. Increase Memory to at least 4GB
# 4. Click "Apply & Restart"

# If using WSL2, increase memory in .wslconfig:
# Create/edit %USERPROFILE%\.wslconfig:
# [wsl2]
# memory=8GB
```

### Issue 2: Services Can't Connect
```bash
# Check if all services are on the same network
docker network ls
docker network inspect compliance-agent_compliance-net

# Restart services if needed
docker-compose restart
```

### Issue 3: MinIO Bucket Creation Failed
```bash
# Manually create bucket
docker-compose exec minio mc alias set myminio http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb myminio/compliance-data
docker-compose exec minio mc mb myminio/compliance-reports
```

### Issue 4: Parser Service Import Errors
```bash
# If parser fails with import errors, rebuild the image
docker-compose build parser
docker-compose up -d parser
```

### Issue 5: HashWriter Go Compilation Error
```bash
# The bytes import issue has been fixed, but if you see compilation errors:
docker-compose build hashwriter
docker-compose up -d hashwriter
```

## Production Deployment

### 1. Security Hardening
```bash
# Generate strong passwords
openssl rand -base64 32  # For JWT_SECRET_KEY
openssl rand -base64 32  # For ES_PASSWORD
openssl rand -base64 32  # For S3_SECRET_KEY

# Update .env with production values
```

### 2. TLS/SSL Configuration
```bash
# Replace self-signed certificates
cp /path/to/your/cert.pem data/certs/server.crt
cp /path/to/your/key.pem data/certs/server.key

# Update docker-compose.yml to use HTTPS
```

### 3. Resource Limits
Add to docker-compose.yml for each service:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

### 4. Monitoring Setup
```bash
# Deploy Prometheus
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Configure Grafana dashboards
docker run -d \
  -p 3000:3000 \
  grafana/grafana
```

### 5. Backup Configuration
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/compliance-agent/$DATE"

# Backup Elasticsearch
docker-compose exec elasticsearch \
  elasticsearch-dump \
  --input=http://localhost:9200/compliance-messages \
  --output=/backup/messages.json

# Backup MinIO data
docker-compose exec minio \
  mc mirror myminio/compliance-data /backup/minio/

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x backup.sh
```

## Verification Checklist

- [ ] All Docker containers are running
- [ ] All health endpoints return 200 OK
- [ ] Test HL7 message ingestion works
- [ ] Elasticsearch indices are created
- [ ] MinIO buckets are accessible
- [ ] Kibana dashboard loads
- [ ] Validation rules can be created/updated
- [ ] Hash-chain entries appear in S3
- [ ] Reporter service can generate PDFs

## Next Steps

1. **Configure Validation Rules**: Use the Validator API to add your specific compliance rules
2. **Set Up Dashboards**: Import Kibana dashboards from `dashboards/` directory
3. **Configure Alerts**: Set up Elasticsearch Watcher for compliance violations
4. **Test Load**: Run load tests with `locust -f tests/load_test.py`
5. **Schedule Reports**: Verify daily report generation at configured time

## Support

For issues:
1. Check container logs: `docker-compose logs [service-name]`
2. Review application logs in `logs/` directory
3. Check Elasticsearch logs: `docker-compose logs elasticsearch`
4. Verify network connectivity between services