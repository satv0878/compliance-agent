#!/usr/bin/env python3
"""
Test script for Compliance Agent ingestion
Works on both Windows and Linux/macOS
"""

import requests
import json
import time
import sys
from datetime import datetime

# Base URLs for services
INGRESS_URL = "http://localhost:8000"
VALIDATOR_URL = "http://localhost:8002"

def test_hl7_ingestion():
    """Test HL7 message ingestion"""
    print("Testing HL7 message ingestion...")
    
    # Sample HL7 message
    hl7_message = "MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20231201120000||ADT^A01|123456|P|2.5|||AL|AL|USA"
    
    try:
        response = requests.post(
            f"{INGRESS_URL}/ingest/hl7",
            data=hl7_message,
            headers={"Content-Type": "text/plain"}
        )
        
        if response.status_code == 200:
            print("✓ HL7 message ingested successfully")
            return True
        else:
            print(f"✗ HL7 ingestion failed with status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ HL7 ingestion failed with error: {e}")
        return False

def test_validation_rules():
    """Test validation rules API"""
    print("\nTesting validation rules API...")
    
    try:
        response = requests.get(f"{VALIDATOR_URL}/rules")
        
        if response.status_code == 200:
            rules = response.json()
            print(f"✓ Validation rules retrieved ({len(rules)} rules)")
            return True
        else:
            print(f"✗ Failed to retrieve validation rules: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to retrieve validation rules: {e}")
        return False

def test_metrics_endpoint():
    """Test metrics endpoint"""
    print("\nTesting metrics endpoint...")
    
    try:
        response = requests.get(f"{INGRESS_URL}/metrics")
        
        if response.status_code == 200:
            print("✓ Metrics endpoint accessible")
            return True
        else:
            print(f"✗ Metrics endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Metrics endpoint failed: {e}")
        return False

def test_health_endpoints():
    """Test all health endpoints"""
    print("\nTesting service health endpoints...")
    
    services = [
        ("Ingress", "http://localhost:8000/health"),
        ("Parser", "http://localhost:8001/health"),
        ("Validator", "http://localhost:8002/health"),
        ("HashWriter", "http://localhost:8003/health"),
        ("Reporter", "http://localhost:8004/health")
    ]
    
    all_healthy = True
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name} service is healthy")
            else:
                print(f"✗ {name} service is not healthy (status: {response.status_code})")
                all_healthy = False
        except Exception as e:
            print(f"✗ {name} service is not responding: {e}")
            all_healthy = False
    
    return all_healthy

def test_dicom_ingestion():
    """Test DICOM data ingestion"""
    print("\nTesting DICOM data ingestion...")
    
    # Sample DICOM metadata (simplified)
    dicom_data = {
        "PatientID": "12345",
        "PatientName": "Test^Patient",
        "StudyInstanceUID": "1.2.840.113619.2.1.1.1.1.20231201.120000",
        "Modality": "CT",
        "StudyDate": "20231201"
    }
    
    try:
        response = requests.post(
            f"{INGRESS_URL}/ingest/dicom",
            json=dicom_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✓ DICOM data ingested successfully")
            return True
        else:
            print(f"✗ DICOM ingestion failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ DICOM ingestion failed with error: {e}")
        return False

def test_fhir_ingestion():
    """Test FHIR resource ingestion"""
    print("\nTesting FHIR resource ingestion...")
    
    # Sample FHIR Patient resource
    fhir_patient = {
        "resourceType": "Patient",
        "id": "example",
        "identifier": [{
            "system": "http://example.org/mrn",
            "value": "12345"
        }],
        "name": [{
            "family": "Test",
            "given": ["Patient"]
        }],
        "gender": "male",
        "birthDate": "1990-01-01"
    }
    
    try:
        response = requests.post(
            f"{INGRESS_URL}/ingest/fhir",
            json=fhir_patient,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✓ FHIR resource ingested successfully")
            return True
        else:
            print(f"✗ FHIR ingestion failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ FHIR ingestion failed with error: {e}")
        return False

def main():
    """Run all tests"""
    print("="*50)
    print("Compliance Agent Integration Test")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # Wait a moment for services to be ready
    print("\nWaiting for services to be ready...")
    time.sleep(2)
    
    # Run tests
    tests = [
        test_health_endpoints,
        test_hl7_ingestion,
        test_validation_rules,
        test_metrics_endpoint,
        test_dicom_ingestion,
        test_fhir_ingestion
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Test failed with unexpected error: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\nAll tests passed! ✓")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed! ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())