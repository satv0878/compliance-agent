from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import httpx
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Validation Service", version="0.9.0")

class Severity(str, Enum):
    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"

class ValidationRule(BaseModel):
    id: str
    name: str
    description: str
    segment: Optional[str] = None
    field: Optional[int] = None
    operator: str
    value: Optional[Any] = None
    severity: Severity
    message: str
    active: bool = True

class ValidationResult(BaseModel):
    rule_id: str
    passed: bool
    severity: Severity
    message: str
    details: Optional[Dict[str, Any]] = None

class ValidatedMessage(BaseModel):
    message_id: str
    channel_id: str
    message_type: str
    timestamp: datetime
    validation_results: List[ValidationResult]
    overall_status: Severity
    hash_data: Optional[Dict[str, str]] = None

# In-memory rule storage (should be replaced with database)
validation_rules = [
    ValidationRule(
        id="PID_NOT_EMPTY",
        name="Patient ID Required",
        description="PID-3 must not be empty",
        segment="PID",
        field=3,
        operator="NOT_EMPTY",
        severity=Severity.ERROR,
        message="PID-3 (Patient ID) must not be empty"
    ),
    ValidationRule(
        id="OBX_LOINC_VALID",
        name="Valid LOINC Code",
        description="OBX-3 must contain valid LOINC code",
        segment="OBX",
        field=3,
        operator="REGEX",
        value=r"^\d{1,5}-\d$",
        severity=Severity.WARN,
        message="OBX-3 should contain valid LOINC code format"
    ),
    ValidationRule(
        id="DICOM_MODALITY_CHECK",
        name="DICOM Modality Match",
        description="DICOM modality must match worklist",
        segment="DICOM",
        field=None,
        operator="IN_LIST",
        value=["CT", "MR", "US", "XR", "CR", "DX"],
        severity=Severity.WARN,
        message="DICOM modality should be in approved list"
    )
]

def apply_rule(rule: ValidationRule, data: Dict[str, Any]) -> ValidationResult:
    try:
        # HL7 rules
        if rule.segment and rule.segment != "DICOM":
            segments = data.get("parsed_data", {}).get("segments", {})
            segment_data = segments.get(rule.segment, {})
            
            if rule.operator == "NOT_EMPTY":
                field_key = {3: "patient_id", 5: "patient_name"}.get(rule.field)
                value = segment_data.get(field_key) if field_key else None
                passed = bool(value and str(value).strip())
                
            elif rule.operator == "REGEX":
                import re
                field_data = segment_data
                if isinstance(segment_data, list) and segment_data:
                    field_data = segment_data[0]
                value = field_data.get("observation_id", "")
                passed = bool(re.match(rule.value, str(value))) if value else False
                
            else:
                passed = True
                
        # DICOM rules
        elif rule.segment == "DICOM" and data.get("message_type") == "DICOM":
            parsed_data = data.get("parsed_data", {})
            
            if rule.operator == "IN_LIST":
                modality = parsed_data.get("modality", "")
                passed = modality in rule.value
            else:
                passed = True
                
        # FHIR rules
        elif data.get("message_type") == "FHIR":
            # Placeholder for FHIR validation
            passed = True
            
        else:
            passed = True
            
        return ValidationResult(
            rule_id=rule.id,
            passed=passed,
            severity=Severity.OK if passed else rule.severity,
            message=rule.message if not passed else "Validation passed",
            details={"rule": rule.dict()} if not passed else None
        )
        
    except Exception as e:
        logger.error(f"Error applying rule {rule.id}: {str(e)}")
        return ValidationResult(
            rule_id=rule.id,
            passed=False,
            severity=Severity.ERROR,
            message=f"Rule evaluation error: {str(e)}",
            details={"error": str(e)}
        )

async def forward_to_hashwriter(validated_message: ValidatedMessage):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://hashwriter-service:8003/hash",
            json=validated_message.dict()
        )
        return response.json()

@app.post("/validate")
async def validate_message(data: dict):
    try:
        # Apply all active rules
        results = []
        for rule in validation_rules:
            if rule.active:
                result = apply_rule(rule, data)
                results.append(result)
        
        # Determine overall status
        error_count = sum(1 for r in results if r.severity == Severity.ERROR)
        warn_count = sum(1 for r in results if r.severity == Severity.WARN)
        
        if error_count > 0:
            overall_status = Severity.ERROR
        elif warn_count > 0:
            overall_status = Severity.WARN
        else:
            overall_status = Severity.OK
        
        validated_message = ValidatedMessage(
            message_id=data.get("message_id"),
            channel_id=data.get("channel_id"),
            message_type=data.get("message_type"),
            timestamp=datetime.fromisoformat(data.get("timestamp")) if isinstance(data.get("timestamp"), str) else data.get("timestamp"),
            validation_results=results,
            overall_status=overall_status
        )
        
        # Forward to hash writer
        hash_result = await forward_to_hashwriter(validated_message)
        validated_message.hash_data = hash_result
        
        return {
            "validation_results": [r.dict() for r in results],
            "overall_status": overall_status,
            "hash_data": hash_result
        }
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rules")
async def get_rules():
    return {"rules": [rule.dict() for rule in validation_rules]}

@app.post("/rules")
async def add_rule(rule: ValidationRule):
    validation_rules.append(rule)
    return {"message": "Rule added", "rule_id": rule.id}

@app.put("/rules/{rule_id}")
async def update_rule(rule_id: str, rule: ValidationRule):
    for i, r in enumerate(validation_rules):
        if r.id == rule_id:
            validation_rules[i] = rule
            return {"message": "Rule updated", "rule_id": rule_id}
    raise HTTPException(status_code=404, detail="Rule not found")

@app.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    for i, r in enumerate(validation_rules):
        if r.id == rule_id:
            validation_rules.pop(i)
            return {"message": "Rule deleted", "rule_id": rule_id}
    raise HTTPException(status_code=404, detail="Rule not found")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}