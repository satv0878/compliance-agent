import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'validator'))
from main import app, ValidationRule, Severity

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

def test_get_rules():
    response = client.get("/rules")
    assert response.status_code == 200
    assert "rules" in response.json()
    assert len(response.json()["rules"]) > 0

def test_add_rule():
    new_rule = {
        "id": "TEST_RULE_001",
        "name": "Test Rule",
        "description": "Test rule for unit testing",
        "segment": "MSH",
        "field": 9,
        "operator": "NOT_EMPTY",
        "severity": "WARN",
        "message": "MSH-9 should not be empty",
        "active": True
    }
    
    response = client.post("/rules", json=new_rule)
    assert response.status_code == 200
    assert response.json()["rule_id"] == "TEST_RULE_001"

def test_validate_hl7_message():
    test_data = {
        "message_id": "TEST_MSG_001",
        "channel_id": "test-channel",
        "message_type": "HL7",
        "timestamp": "2023-10-15T12:00:00",
        "parsed_data": {
            "segments": {
                "PID": {
                    "patient_id": "123456",
                    "patient_name": "Doe^John",
                    "date_of_birth": "19800101",
                    "gender": "M"
                }
            }
        }
    }
    
    response = client.post("/validate", json=test_data)
    assert response.status_code == 200
    assert "validation_results" in response.json()
    assert "overall_status" in response.json()

def test_validate_missing_pid():
    test_data = {
        "message_id": "TEST_MSG_002",
        "channel_id": "test-channel",
        "message_type": "HL7",
        "timestamp": "2023-10-15T12:00:00",
        "parsed_data": {
            "segments": {
                "PID": {
                    "patient_id": "",  # Empty PID-3
                    "patient_name": "Doe^Jane",
                    "date_of_birth": "19900101",
                    "gender": "F"
                }
            }
        }
    }
    
    response = client.post("/validate", json=test_data)
    assert response.status_code == 200
    
    # Check that validation failed
    results = response.json()["validation_results"]
    pid_rule_result = next((r for r in results if r["rule_id"] == "PID_NOT_EMPTY"), None)
    assert pid_rule_result is not None
    assert pid_rule_result["passed"] is False
    assert pid_rule_result["severity"] == "ERROR"

def test_validate_dicom_modality():
    test_data = {
        "message_id": "TEST_DICOM_001",
        "channel_id": "test-channel",
        "message_type": "DICOM",
        "timestamp": "2023-10-15T12:00:00",
        "parsed_data": {
            "modality": "CT",
            "patient_id": "123456",
            "study_instance_uid": "1.2.3.4.5"
        }
    }
    
    response = client.post("/validate", json=test_data)
    assert response.status_code == 200
    
    # Check that DICOM modality validation passed
    results = response.json()["validation_results"]
    modality_result = next((r for r in results if r["rule_id"] == "DICOM_MODALITY_CHECK"), None)
    assert modality_result is not None
    assert modality_result["passed"] is True

def test_delete_rule():
    # First add a rule
    rule_id = "TEST_DELETE_RULE"
    new_rule = {
        "id": rule_id,
        "name": "Test Delete Rule",
        "description": "Rule to test deletion",
        "operator": "NOT_EMPTY",
        "severity": "WARN",
        "message": "Test message",
        "active": True
    }
    
    client.post("/rules", json=new_rule)
    
    # Then delete it
    response = client.delete(f"/rules/{rule_id}")
    assert response.status_code == 200
    assert response.json()["rule_id"] == rule_id
    
    # Verify it's gone
    response = client.delete(f"/rules/{rule_id}")
    assert response.status_code == 404