# First-Time User Quick Start Guide

Welcome to the Compliance Agent! This guide will help you get started in 15 minutes.

## What is the Compliance Agent?

A system that monitors your healthcare data exchanges (HL7, DICOM, FHIR) to ensure they comply with regulations. Think of it as a security camera for your medical data - it watches, validates, and reports on everything.

## Step 1: Verify Everything is Running (2 minutes)

### Windows
Open Command Prompt and run:
```batch
scripts\check_health.bat
```

### Linux/macOS
Open Terminal and run:
```bash
./scripts/check_health.sh
```

You should see all services marked as "healthy" ✓

## Step 2: Send Your First Message (3 minutes)

Let's send a test patient admission message:

### Windows (PowerShell)
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/ingest/hl7" `
  -Method POST `
  -Headers @{"Content-Type"="text/plain"} `
  -Body 'MSH|^~\&|TEST|HOSPITAL|SYSTEM|FACILITY|20240115120000||ADT^A01|MSG001|P|2.5'
```

### Linux/macOS (Terminal)
```bash
curl -X POST http://localhost:8000/ingest/hl7 \
  -H "Content-Type: text/plain" \
  -d 'MSH|^~\&|TEST|HOSPITAL|SYSTEM|FACILITY|20240115120000||ADT^A01|MSG001|P|2.5'
```

You should receive a response like: `{"status":"accepted","message_id":"..."}`

## Step 3: View Your Message (5 minutes)

1. Open your web browser
2. Go to http://localhost:5601 (Kibana)
3. Login with:
   - Username: `elastic`
   - Password: `changeme`
4. Click "Discover" in the left menu
5. You should see your message with validation results!

## Step 4: Check Validation Results (3 minutes)

Your message was automatically validated. To see the rules:

```bash
curl http://localhost:8002/rules
```

Common validation checks:
- ✓ Valid message format
- ✓ Required fields present
- ✓ Authorized sender
- ✓ Timestamp validity

## Step 5: Generate Your First Report (2 minutes)

Generate a compliance report for today:

### Windows (PowerShell)
```powershell
$date = Get-Date -Format "yyyy-MM-dd"
Invoke-WebRequest -Uri "http://localhost:8004/generate/$date" -Method POST
```

### Linux/macOS
```bash
date=$(date +%Y-%m-%d)
curl -X POST http://localhost:8004/generate/$date
```

Then download it:
```bash
curl -o my-first-report.pdf http://localhost:8004/report/$(date +%Y-%m-%d)?format=pdf
```

## What's Next?

### Try Different Message Types

**DICOM Image Metadata:**
```bash
curl -X POST http://localhost:8000/ingest/dicom \
  -H "Content-Type: application/json" \
  -d '{
    "PatientID": "12345",
    "PatientName": "Test^Patient",
    "Modality": "CT",
    "StudyDate": "20240115"
  }'
```

**FHIR Patient Resource:**
```bash
curl -X POST http://localhost:8000/ingest/fhir \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Patient",
    "id": "pat123",
    "name": [{"family": "Test", "given": ["Patient"]}]
  }'
```

### Explore the Dashboards

1. **MinIO Console** (http://localhost:9001)
   - Username: `minioadmin`
   - Password: `minioadmin`
   - See stored reports and audit trails

2. **Kibana Dashboards** (http://localhost:5601)
   - Create visualizations
   - Set up alerts
   - Analyze trends

### Add Custom Validation Rules

Create a rule that checks for patient consent:
```bash
curl -X POST http://localhost:8002/rules \
  -H "Content-Type: application/json" \
  -d '{
    "id": "CONSENT_CHECK",
    "name": "Patient Consent Required",
    "type": "HL7",
    "segment": "CON",
    "field": 1,
    "operator": "NOT_EMPTY",
    "severity": "WARNING",
    "message": "Patient consent segment recommended"
  }'
```

## Common Questions

**Q: What types of medical data can I monitor?**
A: HL7 v2 messages, DICOM metadata, and FHIR resources.

**Q: How do I know if my data is compliant?**
A: Check the validation_status field in Kibana or wait for the daily report.

**Q: Can I add my own validation rules?**
A: Yes! Use the /rules API endpoint to add custom rules.

**Q: Where are the reports stored?**
A: In MinIO under the compliance-reports bucket, organized by date.

**Q: Is my data secure?**
A: Yes, all data is hash-chained for integrity and stored securely.

## Need Help?

- **Full User Guide**: See USER_GUIDE.md
- **Technical Setup**: See SETUP_GUIDE.md
- **Check Logs**: `docker-compose logs [service-name]`
- **API Reference**: See README.md

## Quick Command Reference

| Task | Command |
|------|---------|
| Check health | `scripts\check_health.bat` (Win) / `./scripts/check_health.sh` (Linux) |
| Send HL7 | `curl -X POST http://localhost:8000/ingest/hl7 -d "..."` |
| View rules | `curl http://localhost:8002/rules` |
| Generate report | `curl -X POST http://localhost:8004/generate/YYYY-MM-DD` |
| View logs | `docker-compose logs -f` |

Congratulations! You're now monitoring healthcare compliance! 🎉