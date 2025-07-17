# Deployment Instructions

## Git Repository Setup

The Compliance Agent has been committed to your local git repository. To push it to your remote repository:

### 1. Add your remote repository
```bash
# Replace with your actual repository URL
git remote add origin https://github.com/yourusername/compliance-agent.git
# OR for SSH:
# git remote add origin git@github.com:yourusername/compliance-agent.git
```

### 2. Push to remote
```bash
git push -u origin master
```

## Quick Start After Cloning

Once pushed, anyone can clone and run the system:

```bash
# Clone the repository
git clone https://github.com/yourusername/compliance-agent.git
cd compliance-agent

# Setup and start
make setup
make up

# Test the system
make test
```

## Production Deployment

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 100GB disk space for logs/reports

### Environment Configuration
1. Copy `.env.example` to `.env`
2. Update configurations:
   - Database passwords
   - S3 endpoints
   - TLS certificates
   - Authentication tokens

### Security Hardening
1. Replace self-signed certificates with proper CA certificates
2. Configure firewall rules
3. Set up log rotation
4. Enable audit logging
5. Configure backup procedures

### Monitoring
- Kibana Dashboard: http://localhost:5601
- Prometheus Metrics: http://localhost:8000/metrics
- Health Checks: Available on all service /health endpoints

## Mirth Connect Integration

See `docs/mirth-integration.md` for detailed integration instructions.

Quick setup:
```bash
./scripts/setup_mirth.sh
```

## Support

- Documentation: `/docs` directory
- Examples: `/examples` directory
- Tests: `/tests` directory
- Issues: GitHub Issues

## License

Apache 2.0 - See LICENSE file