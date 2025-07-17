#!/usr/bin/env python3

import requests
import base64
import json
import time
from datetime import datetime

# Base URL for the ingress service
BASE_URL = "http://localhost:8000"

# Test HL7 message
hl7_message = """MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20231015120000||ADT^A01|MSG00001|P|2.5
EVN|A01|20231015120000
PID|1||123456789^^^MRN^MR||DOE^JOHN^A||19800101|M|||123 MAIN ST^^ANYTOWN^ST^12345^USA||(555)123-4567|||M|NON|123456789
PV1|1|I|ICU^101^A||||ATTEND^DOCTOR^PRIMARY|||||||||||VISIT123|||||||||||||||||||||||||20231015120000"""

# Test bearer token
TOKEN = "test-token-123"

def test_hl7_ingestion():
    print("Testing HL7 ingestion...")
    
    # Encode message
    encoded_message = base64.b64encode(hl7_message.encode()).decode()
    
    payload = {
        "channel_id": "mirth-channel-01",
        "payload": encoded_message
    }
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/hl7",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            print("✓ HL7 message ingested successfully")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"✗ Failed to ingest HL7 message: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")

def test_validation_rules():
    print("\nTesting validation rules...")
    
    # Test message with empty PID-3 (should fail validation)
    invalid_hl7 = """MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20231015120000||ADT^A01|MSG00002|P|2.5
PID|1||||DOE^JANE^A||19900101|F"""
    
    encoded_message = base64.b64encode(invalid_hl7.encode()).decode()
    
    payload = {
        "channel_id": "mirth-channel-01",
        "payload": encoded_message
    }
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/hl7",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            validation = result.get("validation_result", {}).get("validation", {})
            if validation.get("overall_status") == "ERROR":
                print("✓ Validation correctly identified missing PID-3")
            else:
                print("✗ Validation should have failed for missing PID-3")
                
    except Exception as e:
        print(f"✗ Error: {str(e)}")

def test_metrics():
    print("\nChecking metrics endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/metrics")
        if response.status_code == 200:
            print("✓ Metrics endpoint accessible")
            # Show first few lines of metrics
            lines = response.text.split('\n')[:10]
            for line in lines:
                if line and not line.startswith('#'):
                    print(f"  {line}")
        else:
            print(f"✗ Failed to access metrics: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == "__main__":
    print("Compliance Agent Ingestion Test")
    print("=" * 40)
    
    # Wait for services to be ready
    print("Waiting for services to start...")
    time.sleep(5)
    
    test_hl7_ingestion()
    test_validation_rules()
    test_metrics()
    
    print("\nTest complete!")