# Compliance Agent - Quick Start Guide

## 5-Minute Setup

### Prerequisites Check
```bash
# Ensure Docker and Docker Compose are installed
docker --version && docker-compose --version
```

### Step 1: Clone and Configure
```bash
# Clone repository
git clone <repository-url>
cd compliance-agent

# Setup environment
cp .env.example .env
```

### Step 2: Run Automated Setup
```bash
# One-command setup
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

### Step 3: Start All Services
```bash
# Start everything
docker-compose up -d

# Wait for services to initialize (60-90 seconds)
sleep 90
```

### Step 4: Verify Installation
```bash
# Quick health check
curl http://localhost:8000/health && echo " ✓ Ingress OK" || echo " ✗ Ingress Failed"
curl http://localhost:8001/health && echo " ✓ Parser OK" || echo " ✗ Parser Failed"
curl http://localhost:8002/health && echo " ✓ Validator OK" || echo " ✗ Validator Failed"
curl http://localhost:8003/health && echo " ✓ HashWriter OK" || echo " ✗ HashWriter Failed"
curl http://localhost:8004/health && echo " ✓ Reporter OK" || echo " ✗ Reporter Failed"
```

### Step 5: Test the System
```bash
# Run test script
python3 scripts/test_ingestion.py
```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| API Gateway | http://localhost:8000 | Main entry point |
| Kibana | http://localhost:5601 | Log visualization |
| MinIO | http://localhost:9001 | Object storage UI |

## Quick Test

Send a test HL7 message:
```bash
curl -X POST http://localhost:8000/ingest/hl7 \
  -H "Content-Type: text/plain" \
  -d 'MSH|^~\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20231201120000||ADT^A01|123456|P|2.5|||AL|AL|USA'
```

## Stop Services
```bash
docker-compose down
```

## Troubleshooting

If services fail to start:
```bash
# Check logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Full restart
docker-compose down && docker-compose up -d
```

For detailed setup instructions, see [SETUP_GUIDE.md](./SETUP_GUIDE.md)