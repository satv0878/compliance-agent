# Compliance / Insight Agent – Requirements & Design Specification (MVP v0.9)

> **Status:** Draft – September 2025\
> **Authors:** Product & Engineering Team\
> **Target Audiences:** Developers • DevOps • QA • Regulatory Affairs • Security Reviewers

---

## 1  Purpose

Hospitals and lab‑chains operating existing integration engines (Mirth, Rhapsody, InterSystems Ensemble, Orthanc …) must prove:

- **DSGVO Art. 30 & 32** – verarbeitungs­verzeichnis & Unveränder­barkeit personenbezogener Datenströme
- **KHZG § 14** – täglicher Funktions­nachweis der Interop‑Module, sonst 2 % Rechnungs­abschlag ab 01‑01‑2025
- **EU‑MDR Annex II/VII** – Design‑Change‑Record + Regression‑Test jeder Mapping‑Änderung (Klasse A‑SW)

The **Compliance / Insight Agent** delivers these proofs *passiv* und *No‑Code*, i.e. without modifying live channels.

---

## 2  Scope (MVP V0.9)

| In‑Scope                                                                      | Out‑of‑Scope                         |
| ----------------------------------------------------------------------------- | ------------------------------------ |
| Live‑mirroring of HL7 v2, DICOM C‑STORE, FHIR REST traffic                    | Message routing / transformation     |
| Validation Rules: PID‑3 ≠ empty, OBX‑3 LOINC match, DICOM Modality = Worklist | Clinical decision support, AI triage |
| Immutable Hash‑Chain Log (ES + S3 Object‑Lock)                                | Blockchain ledger, public consensus  |
| Daily PDF/A‑3 (+ JSON) Audit report, PKCS‑7 signed                            | Long‑term XDS registry integration   |
| Kibana dashboard + Watcher Alerts (Teams, ServiceNow)                         | SIEM correlation engines             |

---

## 3  Regulatory Constraints

| Regulation                  | MVP Compliance Strategy                                                     |
| --------------------------- | --------------------------------------------------------------------------- |
| DSGVO Art. 30               | Auto‑generated *Processing Registry* CSV (segment, tag, purpose, recipient) |
| DSGVO Art. 32               | Hash‑Chain + TSA root hash + WORM object lock; TLS 1.3 mutual auth          |
| KHZG § 14                   | Daily report shows: total messages, error rate, rule violations ≤ 1 %       |
| MDR (Accessory SW, Class A) | IEC 62304 doc set, auto‑regression test (50 HL7, 10 DICOM refs)             |

---

## 4  Functional Requirements

| ID    | Requirement                                                                        | Priority |
| ----- | ---------------------------------------------------------------------------------- | -------- |
| FR‑01 | System shall ingest ≥ 500 messages/s in burst                                      | MUST     |
| FR‑02 | Validate each message against active rule‑set and return result < 50 ms            | MUST     |
| FR‑03 | Persist audit‑entry with `timestamp, msgHash, prevHash, result`                    | MUST     |
| FR‑04 | Export signed PDF/A‑3 & JSON at 23:55 local daily                                  | MUST     |
| FR‑05 | Send alert if `severity=ERROR` count ≥ 3 per 5 min                                 | SHOULD   |
| FR‑06 | Provide REST endpoint `/rules` to add/activate validation rules (No‑Code UI later) | SHOULD   |

### Non‑Functional

- **Availability:** 99.5 % (single‑node); HA in v1.0
- **Security:** OWASP Top10, TLS 1.3, strict CSP on Kibana, RBAC via Keycloak
- **Data Retention:** 730 days hot+warm; cold ≥ 10 years in Glacier
- **DevOps:** GitHub Actions CI; docker‑compose (PoC); Helm (prod)

---

## 5  Architecture Overview

1. **Ingress** (FastAPI) – HTTPS/Protobuf
2. **Parsers** (hapi‑hl7, dcm4che, fhir‑validator) – convert to Canonical JSON
3. **Validation Service** (Quarkus/Java) – apply rule‑set, call Terminology cache
4. **Hash‑Writer** (Go) – build chainHash, store in ES & S3
5. **Logstash + Elasticsearch 7.x** – store/search
6. **Kibana 7.x** – dashboard & watcher
7. **Report Service** (Python/ReportLab) – daily PDF/A‑3 + PKCS‑7 sign

*Detailed sequence diagram in **``**.*

---

## 6  Deployment Topology

- **PoC / Pilot:** single VM (4 CPU / 8 GB) running docker‑compose
- **Prod:**
  - Kubernetes 1.29
  - StatefulSet 3‑node ES cluster (hot/warm)
  - Parsers & Validator as HorizontalPodAutoscaler (CPU 70 %)
  - S3‑compatible Object‑Lock (MinIO / NetApp StorageGRID)

---

## 7  Interfaces

| Name             | Type               | Spec                                |
| ---------------- | ------------------ | ----------------------------------- |
| `/ingest/hl7`    | HTTP POST protobuf | ER7 payload base64, channelId, uuid |
| `/ingest/dicom`  | HTTP POST binary   | Encapsulated DICOM *+ Meta‑JSON*    |
| `/rules`         | REST CRUD          | JSON rule schema v0.1               |
| `/report/{date}` | GET                | returns PDF or JSON audit file      |

Authentication: mutual‑TLS certificate or OAuth2 client‑credentials.

---

## 8  Validation Rule Schema (excerpt)

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

---

## 9  Data Model (ES index `audit-*`)

| Field            | Type      | Comment                    |
| ---------------- | --------- | -------------------------- |
| `ts`             | `date`    | ISO‑8601 UTC               |
| `msgType`        | `keyword` | HL7 msgcode or DICOM event |
| `sha256_payload` | `keyword` | 64 hex chars               |
| `prevHash`       | `keyword` | chain reference            |
| `chainHash`      | `keyword` | integrity check            |
| `ruleId`         | `keyword` | validation rule triggered  |
| `severity`       | `keyword` | OK / WARN / ERROR          |

---

## 10  Security Controls

- **TLS 1.3** – required on ingress, cipher‑suite TLS\_AES\_128\_GCM\_SHA256
- **IAM** – Keycloak; roles `admin`, `auditor`, `viewer`
- **Secrets** – K8s sealed‑secret (`kubeseal`)
- **CVE Scans** – Trivy in CI pipeline
- **Pen‑Test Window** – after v1.0, OWASP ZAP & internal Red‑Team

---

## 11  Testing

| Layer       | Tool                               | Coverage                      |
| ----------- | ---------------------------------- | ----------------------------- |
| Unit        | Go `testing`, JUnit                | ≥ 90 % validator, hash‑writer |
| Integration | Postman/newman replay 1 k messages | All API paths                 |
| Load        | Locust (HL7 feed 500 msg/s)        | latency < 50 ms avg           |
| Security    | Trivy, OWASP ZAP baseline          | 0 critical CVE                |

---

## 12  Limitations / Open Items

- Single‑tenant only (multitenancy v1.0)
- FHIR validation ≈ 15 msg/s – optimise after IG cache refactor
- No GUI Rule‑Builder (CLI/JSON only) – roadmap v1.0

---

## 13  Roadmap (excerpt)

| Version | ETA      | Features                                                  |
| ------- | -------- | --------------------------------------------------------- |
| **0.9** | Sep 2025 | PoC – HL7/DICOM, hash‑chain, daily PDF                    |
| 1.0     | Q2 2026  | GUI Rule‑Builder, FHIR full, HA‑cluster, Keycloak IAM     |
| 1.1     | Q4 2026  | IHE ATNA bridge, multi‑tenant SaaS, Kubernetes Helm chart |

---

## 14  Glossary

- **WORM** – Write‑Once‑Read‑Many, immutable storage mode.
- **Hash‑Chain** – Each record stores hash of itself + previous → integrity.
- **TSA** – Time‑Stamp Authority, RFC 3161.

---

© 2025 Your Start‑up GmbH – Apache 2.0 license

Can you 
