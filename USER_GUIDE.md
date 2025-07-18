# Compliance Agent User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Basic Operations](#basic-operations)
4. [Working with Message Types](#working-with-message-types)
5. [Managing Validation Rules](#managing-validation-rules)
6. [Monitoring & Dashboards](#monitoring--dashboards)
7. [Generating Reports](#generating-reports)
8. [Common Tasks](#common-tasks)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Introduction

The Compliance Agent is a healthcare data monitoring system that ensures your medical data exchanges comply with regulations (DSGVO, KHZG, EU-MDR). It monitors messages in real-time, validates them against configurable rules, and maintains an immutable audit trail.

### Key Features
- **Real-time Monitoring**: Processes HL7, DICOM, and FHIR messages
- **Automatic Validation**: Checks messages against compliance rules
- **Audit Trail**: Creates tamper-proof records of all data exchanges
- **Daily Reports**: Generates compliance reports automatically

## Getting Started

### First-Time Setup Checklist

1. **Verify Installation**
   ```bash
   # Windows
   scripts\check_health.bat
   
   # Linux/macOS
   ./scripts/check_health.sh
   ```
   All services should show as "healthy".

2. **Access Web Interfaces**
   - **Kibana Dashboard**: http://localhost:5601
     - Username: `elastic`
     - Password: `changeme`
   - **MinIO Console**: http://localhost:9001
     - Username: `minioadmin`
     - Password: `minioadmin`

3. **Run Your First Test**
   ```bash
   # Windows
   python scripts\test_ingestion.py
   
   # Linux/macOS
   python3 scripts/test_ingestion.py
   ```

## Basic Operations

### 1. Sending Healthcare Messages

The system accepts three types of healthcare data formats:

#### HL7 v2 Messages
```bash
curl -X POST http://localhost:8000/ingest/hl7 \
  -H "Content-Type: text/plain" \
  -d 'MSH|^~\&|HIS|HOSPITAL|LAB|LAB|20240115120000||ORM^O01|MSG123|P|2.5|||AL|AL|'
```

#### DICOM Metadata
```bash
curl -X POST http://localhost:8000/ingest/dicom \
  -H "Content-Type: application/json" \
  -d '{
    "PatientID": "PAT001",
    "PatientName": "Doe^John",
    "StudyInstanceUID": "1.2.840.113619.2.1.1.1",
    "Modality": "CT",
    "StudyDate": "20240115"
  }'
```

#### FHIR Resources
```bash
curl -X POST http://localhost:8000/ingest/fhir \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Patient",
    "id": "pat001",
    "name": [{
      "family": "Doe",
      "given": ["John"]
    }],
    "gender": "male",
    "birthDate": "1980-01-01"
  }'
```

### 2. Checking Message Status

After sending a message, you can verify it was processed:

1. **Check Ingestion Metrics**
   ```bash
   curl http://localhost:8000/metrics | grep messages_ingested
   ```

2. **View in Kibana**
   - Open http://localhost:5601
   - Navigate to "Discover"
   - Select `compliance-messages-*` index
   - You'll see your processed messages

## Working with Message Types

### HL7 Messages

HL7 v2 messages are pipe-delimited healthcare messages. Common types:
- **ADT** (Admission, Discharge, Transfer)
- **ORM** (Order Messages)
- **ORU** (Observation Results)

Example ADT message for patient admission:
```
MSH|^~\&|HIS|HOSP|ADT|HOSP|20240115130000||ADT^A01|12345|P|2.5|||AL|AL|
EVN|A01|20240115130000||||
PID|1||PAT001||Doe^John^A||19800101|M|||123 Main St^^City^ST^12345||555-1234|||M||ACC001|123-45-6789|
PV1|1|I|ICU^101^A||||ATT001^Smith^Jane^Dr.|||SUR||||ADM|||ATT001|INP||||||||||||||||||||||||||20240115130000|
```

### DICOM Data

DICOM is used for medical imaging. When sending DICOM metadata:
```json
{
  "PatientID": "PAT001",
  "PatientName": "Doe^John",
  "StudyInstanceUID": "1.2.840.113619.2.1.1.1.1.20240115.130000",
  "SeriesInstanceUID": "1.2.840.113619.2.1.1.1.2.20240115.130000",
  "SOPInstanceUID": "1.2.840.113619.2.1.1.1.3.20240115.130000",
  "Modality": "MR",
  "StudyDate": "20240115",
  "StudyDescription": "Brain MRI",
  "InstitutionName": "General Hospital"
}
```

### FHIR Resources

FHIR uses JSON-based resources. Common resources:
- **Patient**: Demographic information
- **Observation**: Test results
- **Encounter**: Visit information

Example Observation:
```json
{
  "resourceType": "Observation",
  "id": "blood-pressure",
  "status": "final",
  "category": [{
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/observation-category",
      "code": "vital-signs"
    }]
  }],
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "85354-9",
      "display": "Blood pressure panel"
    }]
  },
  "subject": {
    "reference": "Patient/pat001"
  },
  "effectiveDateTime": "2024-01-15T13:00:00Z",
  "component": [
    {
      "code": {
        "coding": [{
          "system": "http://loinc.org",
          "code": "8480-6",
          "display": "Systolic blood pressure"
        }]
      },
      "valueQuantity": {
        "value": 120,
        "unit": "mmHg"
      }
    },
    {
      "code": {
        "coding": [{
          "system": "http://loinc.org",
          "code": "8462-4",
          "display": "Diastolic blood pressure"
        }]
      },
      "valueQuantity": {
        "value": 80,
        "unit": "mmHg"
      }
    }
  ]
}
```

## Managing Validation Rules

Validation rules ensure messages meet compliance requirements.

### 1. View Current Rules
```bash
curl http://localhost:8002/rules | json_pp
```

### 2. Add a New Rule

Example: Require patient ID in all HL7 messages:
```bash
curl -X POST http://localhost:8002/rules \
  -H "Content-Type: application/json" \
  -d '{
    "id": "REQUIRE_PATIENT_ID",
    "name": "Patient ID Required",
    "type": "HL7",
    "segment": "PID",
    "field": 3,
    "operator": "NOT_EMPTY",
    "severity": "ERROR",
    "message": "Patient ID (PID-3) is required for compliance",
    "active": true
  }'
```

### 3. Common Validation Rules

#### HL7 Rules
- **Patient Identification**: PID-3 must not be empty
- **Message Control ID**: MSH-10 must be unique
- **Sending Facility**: MSH-4 must be authorized

#### DICOM Rules
- **Patient ID Required**: PatientID must be present
- **Study UID Format**: Must follow DICOM UID format
- **Modality Whitelist**: Only approved modalities

#### FHIR Rules
- **Resource Validation**: Must conform to FHIR schema
- **Reference Integrity**: Referenced resources must exist
- **Required Fields**: Based on profile requirements

### 4. Update a Rule
```bash
curl -X PUT http://localhost:8002/rules/REQUIRE_PATIENT_ID \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "WARNING"
  }'
```

### 5. Disable a Rule
```bash
curl -X PUT http://localhost:8002/rules/REQUIRE_PATIENT_ID \
  -H "Content-Type: application/json" \
  -d '{
    "active": false
  }'
```

## Monitoring & Dashboards

### 1. Kibana Dashboards

Access Kibana at http://localhost:5601

#### Creating a Compliance Dashboard:
1. Go to **Dashboard** → **Create dashboard**
2. Add visualizations:
   - **Message Volume**: Line chart of messages over time
   - **Validation Status**: Pie chart of passed vs failed
   - **Message Types**: Bar chart by type (HL7, DICOM, FHIR)
   - **Top Validation Errors**: Data table of common issues

#### Useful Searches:
- Failed validations: `validation_status:"FAILED"`
- Specific message type: `message_type:"HL7"`
- Time range: `@timestamp:[now-1h TO now]`

### 2. Real-time Monitoring

Watch messages in real-time:
```bash
# Windows PowerShell
while ($true) {
    Clear-Host
    curl http://localhost:8000/metrics
    Start-Sleep -Seconds 5
}

# Linux/macOS
watch -n 5 'curl -s http://localhost:8000/metrics | grep -E "messages_ingested|validation_errors"'
```

### 3. Alert Configuration

Set up alerts in Kibana:
1. Go to **Stack Management** → **Watcher**
2. Create new alert for validation failures
3. Set threshold (e.g., > 10 failures in 5 minutes)
4. Configure email/webhook notification

## Generating Reports

### 1. Manual Report Generation

Generate a report for a specific date:
```bash
curl -X POST http://localhost:8004/generate/2024-01-15
```

### 2. Download Generated Report

```bash
# PDF format
curl -o compliance-report-2024-01-15.pdf \
  http://localhost:8004/report/2024-01-15?format=pdf

# JSON format
curl -o compliance-report-2024-01-15.json \
  http://localhost:8004/report/2024-01-15?format=json
```

### 3. Automatic Daily Reports

Reports are automatically generated daily at 23:55 (configurable in .env).

View in MinIO:
1. Open http://localhost:9001
2. Navigate to `compliance-reports` bucket
3. Reports are organized by year/month/day

### 4. Report Contents

Each report includes:
- **Summary Statistics**: Total messages, validation results
- **Compliance Metrics**: Pass/fail rates by regulation
- **Detailed Findings**: List of validation failures
- **Audit Trail**: Hash verification of data integrity
- **Recommendations**: Suggested improvements

## Common Tasks

### 1. Checking System Health

Quick health check of all components:
```bash
# Check if messages are being processed
curl http://localhost:8000/health

# Check validation service
curl http://localhost:8002/health

# Check report generation
curl http://localhost:8004/health
```

### 2. Investigating Failed Messages

1. Find failed messages in Kibana:
   - Search: `validation_status:"FAILED"`
   - Check `validation_errors` field for details

2. Common failure reasons:
   - Missing required fields
   - Invalid field formats
   - Unauthorized sender
   - Schema validation errors

### 3. Bulk Message Import

For testing or migration:
```python
import requests
import time

# Read messages from file
with open('messages.txt', 'r') as f:
    messages = f.readlines()

# Send each message
for msg in messages:
    response = requests.post(
        'http://localhost:8000/ingest/hl7',
        data=msg.strip(),
        headers={'Content-Type': 'text/plain'}
    )
    print(f"Sent message: {response.status_code}")
    time.sleep(0.1)  # Rate limiting
```

### 4. Exporting Audit Logs

Export audit logs for external analysis:
```bash
# Export from Elasticsearch
curl -X GET "localhost:9200/compliance-audit-*/_search?size=1000" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "range": {
        "@timestamp": {
          "gte": "2024-01-01",
          "lte": "2024-01-31"
        }
      }
    }
  }' > audit-logs-january.json
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Messages Not Being Processed
- **Check service health**: Run health check script
- **Verify network**: Ensure Docker network is up
- **Check logs**: `docker-compose logs ingress`

#### 2. Validation Always Fails
- **Review rules**: Some rules might be too strict
- **Check message format**: Ensure proper encoding
- **Verify field mappings**: HL7 field numbers start at 1

#### 3. Reports Not Generated
- **Check MinIO**: Ensure bucket exists and is writable
- **Verify time settings**: Check REPORT_GENERATION_TIME in .env
- **Review reporter logs**: `docker-compose logs reporter`

#### 4. High Memory Usage
- **Elasticsearch tuning**: Limit heap size in docker-compose.yml
- **Clear old data**: Implement data retention policy
- **Scale horizontally**: Add more service instances

### Getting Help

1. **Check Logs**
   ```bash
   # View all logs
   docker-compose logs
   
   # Specific service
   docker-compose logs validator -f
   ```

2. **Enable Debug Mode**
   Add to .env:
   ```
   LOG_LEVEL=DEBUG
   ```

3. **Common Log Locations**
   - Application logs: `./logs/[service-name]/`
   - Elasticsearch logs: `docker-compose logs elasticsearch`
   - System metrics: http://localhost:8000/metrics

## Best Practices

### 1. Security
- **Change default passwords** immediately
- **Use HTTPS** in production
- **Implement access controls** for sensitive data
- **Regular security audits** of validation rules

### 2. Performance
- **Batch messages** when possible
- **Monitor resource usage** regularly
- **Implement data retention** policies
- **Scale services** based on load

### 3. Compliance
- **Regular rule reviews** with compliance team
- **Document all customizations**
- **Maintain audit trail** integrity
- **Schedule compliance training**

### 4. Maintenance
- **Daily health checks**
- **Weekly report reviews**
- **Monthly rule audits**
- **Quarterly system updates**

## Quick Reference

### API Endpoints
| Service | Endpoint | Purpose |
|---------|----------|---------|
| Ingress | POST /ingest/hl7 | Submit HL7 messages |
| Ingress | POST /ingest/dicom | Submit DICOM data |
| Ingress | POST /ingest/fhir | Submit FHIR resources |
| Validator | GET /rules | List validation rules |
| Validator | POST /rules | Add validation rule |
| Reporter | POST /generate/{date} | Generate report |
| Reporter | GET /report/{date} | Download report |
| All | GET /health | Health check |
| All | GET /metrics | Prometheus metrics |

### Default Credentials
| Service | Username | Password | URL |
|---------|----------|----------|-----|
| Kibana | elastic | changeme | http://localhost:5601 |
| MinIO | minioadmin | minioadmin | http://localhost:9001 |

### Support Resources
- Configuration: `.env` file
- Logs: `./logs/` directory
- Documentation: This guide and README.md
- Health Check: `scripts/check_health.bat` (Windows) or `./scripts/check_health.sh` (Linux/macOS)