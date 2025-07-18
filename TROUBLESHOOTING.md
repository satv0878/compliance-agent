# Troubleshooting Guide

## Common Issues and Solutions

### Windows-Specific Issues

#### 1. Docker Compose Command Not Found
**Problem**: `docker-compose: command not found`
**Solution**: 
- Use `docker compose` instead of `docker-compose` (Docker Desktop includes Compose as a plugin)
- Or install standalone Docker Compose from https://docs.docker.com/compose/install/

#### 2. Volume Mount Issues on Windows
**Problem**: Volume mounts fail with permission errors
**Solution**:
- Ensure Docker Desktop has access to your drive (Settings > Resources > File Sharing)
- Use forward slashes in paths: `./data:/data` instead of `.\data:/data`
- Run PowerShell/Command Prompt as Administrator

#### 3. WSL2 Integration Issues
**Problem**: Docker commands fail in WSL2
**Solution**:
- Enable WSL2 integration in Docker Desktop (Settings > Resources > WSL Integration)
- Restart Docker Desktop after enabling WSL2 integration

#### 4. Port Conflicts
**Problem**: "Port already in use" errors
**Solution**:
```bash
# Check what's using the port
netstat -ano | findstr :9200
# Kill the process using the port
taskkill /PID <process_id> /F
```

### Linux-Specific Issues

#### 1. Permission Denied Errors
**Problem**: Permission errors when starting containers
**Solution**:
```bash
# Fix file permissions
sudo chown -R $USER:$USER ./data
sudo chown -R $USER:$USER ./logs
sudo chown -R $USER:$USER ./certs
```

#### 2. Docker Socket Permission
**Problem**: Cannot connect to Docker daemon
**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Restart shell or run
newgrp docker
```

### Cross-Platform Issues

#### 1. Services Not Starting
**Problem**: Services fail to start or become unhealthy
**Solution**:
1. Check Docker Desktop is running
2. Verify system resources (RAM, disk space)
3. Check container logs:
```bash
# Windows
docker compose logs elasticsearch
# Linux
docker-compose logs elasticsearch
```

#### 2. Elasticsearch Won't Start
**Problem**: Elasticsearch container exits immediately
**Solution**:
- Increase Docker memory allocation to at least 4GB
- Check if vm.max_map_count is set (Linux):
```bash
sudo sysctl -w vm.max_map_count=262144
```

#### 3. MinIO Buckets Not Created
**Problem**: MinIO bucket creation fails
**Solution**:
- Wait for MinIO to fully start before creating buckets
- Manually create buckets via web interface: http://localhost:9001
- Use MinIO CLI inside container:
```bash
docker exec -it compliance-minio mc mb /data/compliance-audit
```

#### 4. SSL Certificate Issues
**Problem**: SSL certificate generation fails
**Solution**:
- Manually generate certificates:
```bash
# Create certificates directory
mkdir -p certs

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout certs/server.key \
    -out certs/server.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Health Check Commands

#### Windows
```batch
# Check all services
scripts\check_health.bat

# Check specific service
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing"
```

#### Linux
```bash
# Check all services
./scripts/check_health.sh

# Check specific service
curl -f http://localhost:8000/health
```

### Performance Issues

#### 1. Slow Startup
**Problem**: Services take too long to start
**Solution**:
- Increase Docker memory allocation
- Use SSD storage for Docker volumes
- Disable unnecessary services temporarily

#### 2. High Memory Usage
**Problem**: System running out of memory
**Solution**:
- Reduce Elasticsearch heap size in docker-compose.yml:
```yaml
environment:
  - ES_JAVA_OPTS=-Xms256m -Xmx512m
```

### Debugging Steps

1. **Check Docker Desktop Status**
   - Ensure Docker Desktop is running
   - Check for updates

2. **Verify System Requirements**
   - Minimum 8GB RAM
   - 10GB free disk space
   - Docker Desktop 4.0+

3. **Check Container Logs**
   ```bash
   # View all logs
   docker compose logs
   
   # View specific service logs
   docker compose logs elasticsearch
   ```

4. **Test Individual Components**
   ```bash
   # Test Elasticsearch
   curl -u elastic:changeme http://localhost:9200/_cluster/health
   
   # Test MinIO
   curl http://localhost:9000/minio/health/live
   ```

5. **Reset Everything**
   ```bash
   # Stop all services
   docker compose down
   
   # Remove volumes (WARNING: This deletes all data)
   docker compose down -v
   
   # Remove all containers and images
   docker system prune -a
   
   # Start fresh
   docker compose up -d
   ```

### Getting Help

If issues persist:
1. Check the GitHub Issues page
2. Review Docker Desktop logs
3. Verify system requirements
4. Try running with minimal services first
5. Check firewall/antivirus settings

### Environment Variables

Common environment variables to check in `.env`:
- `ES_JAVA_OPTS`: Elasticsearch memory settings
- `MINIO_ROOT_USER`: MinIO access credentials
- `MINIO_ROOT_PASSWORD`: MinIO secret credentials
- `ELASTIC_PASSWORD`: Elasticsearch password

### Quick Reset Commands

#### Windows
```batch
# Full reset
docker compose down -v
docker system prune -a
scripts\setup-windows.bat
```

#### Linux
```bash
# Full reset
docker-compose down -v
docker system prune -a
./scripts/setup.sh
```