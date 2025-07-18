# Compliance Agent - Windows Setup Guide

## Prerequisites

1. **Docker Desktop for Windows** (version 4.0+)
   - Download from: https://www.docker.com/products/docker-desktop
   - Ensure WSL2 integration is enabled
   - Allocate at least 8GB RAM to Docker

2. **System Requirements**
   - Windows 10/11 (64-bit)
   - 8GB RAM minimum (16GB recommended)
   - 10GB free disk space
   - WSL2 enabled (for better performance)

## Quick Setup (5 minutes)

### Option 1: Using Enhanced Setup Script
```cmd
# Clone the repository
git clone <repository-url>
cd compliance-agent

# Run the enhanced Windows setup script
scripts\setup-windows.bat

# Start all services
scripts\start.bat
```

### Option 2: Manual Setup
```cmd
# Clone and navigate
git clone <repository-url>
cd compliance-agent

# Copy environment file
copy .env.example .env

# Create directories
mkdir data\elasticsearch data\minio certs logs

# Start services
docker compose up -d
```

## Verification

### Check Service Health
```cmd
# Run health check script
scripts\check_health.bat

# Or check manually
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing"
```

### Access Web Interfaces
- **Kibana**: http://localhost:5601 (elastic/changeme)
- **MinIO**: http://localhost:9001 (minioadmin/minioadmin)
- **API Gateway**: http://localhost:8000

## Common Commands

### Starting Services
```cmd
# Start all services
docker compose up -d

# Start specific service
docker compose up -d elasticsearch

# Start with logs
docker compose up
```

### Stopping Services
```cmd
# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v
```

### Viewing Logs
```cmd
# View all logs
docker compose logs

# View specific service logs
docker compose logs elasticsearch

# Follow logs in real-time
docker compose logs -f ingress-service
```

## Testing the System

### Send Test HL7 Message
```cmd
# Using PowerShell
$body = 'MSH|^~\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20231201120000||ADT^A01|123456|P|2.5|||AL|AL|USA'
Invoke-WebRequest -Uri 'http://localhost:8000/ingest/hl7' -Method POST -Body $body -ContentType 'text/plain'

# Using curl (if installed)
curl -X POST http://localhost:8000/ingest/hl7 -H "Content-Type: text/plain" -d "MSH|^~\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20231201120000||ADT^A01|123456|P|2.5|||AL|AL|USA"
```

## Troubleshooting

### Common Issues

1. **"docker-compose: command not found"**
   - Use `docker compose` instead of `docker-compose`
   - Docker Desktop includes Compose as a plugin

2. **Permission Errors**
   - Run Command Prompt as Administrator
   - Ensure Docker Desktop has drive access permissions

3. **Port Already in Use**
   - Check what's using the port: `netstat -ano | findstr :9200`
   - Kill the process: `taskkill /PID <process_id> /F`

4. **Services Not Starting**
   - Increase Docker memory allocation in Docker Desktop settings
   - Check Docker Desktop is running
   - Verify system resources

### Performance Tips

1. **Use SSD Storage**
   - Store Docker volumes on SSD for better performance

2. **Increase Memory**
   - Allocate at least 8GB RAM to Docker Desktop
   - Consider 16GB for better performance

3. **WSL2 Integration**
   - Enable WSL2 backend in Docker Desktop
   - Use WSL2 terminal for better performance

### Reset Everything
```cmd
# Stop all services
docker compose down -v

# Remove all containers and images
docker system prune -a

# Run setup again
scripts\setup-windows.bat
```

## Service Architecture

The compliance agent consists of:
- **Ingress Service** (Port 8000): API gateway and entry point
- **Parser Service** (Port 8001): Message parsing and transformation
- **Validator Service** (Port 8002): Message validation
- **HashWriter Service** (Port 8003): Data hashing and storage
- **Reporter Service** (Port 8004): Report generation
- **Elasticsearch** (Port 9200): Search and analytics
- **Kibana** (Port 5601): Visualization dashboard
- **MinIO** (Port 9000/9001): Object storage
- **Logstash** (Port 8080): Log processing

## Security Notes

- Default credentials are provided for development
- Change passwords in production
- Use TLS certificates for production deployment
- Secure network access appropriately

## Support

For issues specific to Windows:
1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Verify Docker Desktop settings
3. Check Windows firewall settings
4. Ensure WSL2 is properly configured

For general issues:
1. Check container logs: `docker compose logs`
2. Verify system resources
3. Review [SETUP_GUIDE.md](./SETUP_GUIDE.md)
4. Check GitHub Issues page