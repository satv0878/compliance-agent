# Compliance Agent

A passive monitoring system for healthcare data integration that ensures regulatory compliance with DSGVO, KHZG, and EU-MDR requirements.

## Features

- **Multi-Protocol Support**: HL7 v2, DICOM, FHIR REST
- **Real-time Validation**: Configurable rules engine with < 50ms response time
- **Immutable Audit Trail**: Hash-chain with S3 object lock
- **Automated Reporting**: Daily PDF/JSON reports with digital signatures
- **High Performance**: 500+ messages/second throughput
- **No-Code Configuration**: REST API for rule management

## Quick Start

1. **Prerequisites**
   - Docker & Docker Compose
   - 8GB RAM minimum
   - 20GB disk space

2. **Setup**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd compliance-agent

   # Copy environment configuration
   cp .env.example .env

   # Start services
   docker-compose up -d

   # Run setup script
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

3. **Test Installation**
   ```bash
   # Check service health
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   curl http://localhost:8004/health

   # Run ingestion test
   python3 scripts/test_ingestion.py
   ```

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌───────────┐     ┌────────────┐
│   Ingress   │────▶│  Parser  │────▶│ Validator │────▶│ HashWriter │
│  (FastAPI)  │     │ (FastAPI)│     │ (FastAPI) │     │    (Go)    │
└─────────────┘     └──────────┘     └───────────┘     └────────────┘
                                                               │
                    ┌──────────┐     ┌───────────┐            ▼
                    │  Kibana  │◀────│  Elastic  │◀──────────────────
                    └──────────┘     └───────────┘
                                            │
                    ┌──────────┐            ▼
                    │ Reporter │     ┌───────────┐
                    │ (Python) │────▶│   MinIO   │
                    └──────────┘     └───────────┘
```

## API Endpoints

### Ingress Service (Port 8000)
- `POST /ingest/hl7` - Submit HL7 messages
- `POST /ingest/dicom` - Submit DICOM data
- `POST /ingest/fhir` - Submit FHIR resources
- `GET /metrics` - Prometheus metrics
- `GET /health` - Health check

### Validator Service (Port 8002)
- `GET /rules` - List validation rules
- `POST /rules` - Add new rule
- `PUT /rules/{id}` - Update rule
- `DELETE /rules/{id}` - Delete rule

### Reporter Service (Port 8004)
- `POST /generate/{date}` - Generate report for date
- `GET /report/{date}` - Download report (PDF/JSON)

## Configuration

### Environment Variables
Key configuration in `.env`:
```
ES_HOST=localhost
ES_PORT=9200
S3_ENDPOINT=http://localhost:9000
REPORT_GENERATION_TIME=23:55
REPORT_TIMEZONE=Europe/Berlin
```

### Validation Rules
Example rule configuration:
```json
{
  "id": "PID_NOT_EMPTY",
  "segment": "PID",
  "field": 3,
  "operator": "NOT_EMPTY",
  "severity": "ERROR",
  "message": "PID-3 must not be empty"
}
```

## Monitoring

- **Kibana Dashboard**: http://localhost:5601
- **MinIO Console**: http://localhost:9001
- **Elasticsearch**: http://localhost:9200

Default credentials:
- Elasticsearch: elastic/changeme
- MinIO: minioadmin/minioadmin

## Development

### Running Tests
```bash
# Unit tests
pytest tests/

# Integration tests
python scripts/test_ingestion.py

# Load testing
locust -f tests/load_test.py --host=http://localhost:8000
```

### Adding New Parsers
1. Implement parser in `services/parser/main.py`
2. Add validation rules in `services/validator/main.py`
3. Update ingress routes in `services/ingress/main.py`

## Production Deployment

### Kubernetes
```bash
# Apply Helm chart
helm install compliance-agent ./deployment/helm/

# Scale services
kubectl scale deployment parser-service --replicas=3
```

### Security Hardening
1. Replace self-signed certificates
2. Enable mutual TLS
3. Configure RBAC with Keycloak
4. Set up network policies
5. Enable audit logging

## Compliance

This system helps meet:
- **DSGVO Art. 30**: Processing registry generation
- **DSGVO Art. 32**: Data integrity via hash-chain
- **KHZG § 14**: Daily functionality proof
- **EU-MDR**: Change tracking and testing

## Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker logs
   ```bash
   docker-compose logs -f [service-name]
   ```

2. **Elasticsearch errors**: Increase VM memory
   ```bash
   sudo sysctl -w vm.max_map_count=262144
   ```

3. **MinIO bucket errors**: Re-run setup script

## License

Apache 2.0 - See LICENSE file

## Support

- Documentation: `/docs` directory
- Issues: GitHub Issues
- Contact: compliance-support@example.com