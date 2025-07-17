from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import hl7
import pydicom
from fhir.resources import construct_fhir_element
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Message Parser Service", version="0.9.0")

class ParsedMessage(BaseModel):
    message_id: str
    channel_id: str
    message_type: str
    parsed_data: Dict[str, Any]
    timestamp: datetime
    raw_size: int

class HL7ParseRequest(BaseModel):
    message_id: str
    channel_id: str
    payload: str
    timestamp: str

async def forward_to_validator(parsed_message: ParsedMessage):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://validator-service:8002/validate",
            json=parsed_message.dict()
        )
        return response.json()

@app.post("/parse/hl7")
async def parse_hl7(request: HL7ParseRequest):
    try:
        message = hl7.parse(request.payload)
        
        # Extract key fields
        parsed_data = {
            "message_type": str(message.segment('MSH')[9]) if message.segment('MSH') else None,
            "message_control_id": str(message.segment('MSH')[10]) if message.segment('MSH') else None,
            "sending_application": str(message.segment('MSH')[3]) if message.segment('MSH') else None,
            "receiving_application": str(message.segment('MSH')[5]) if message.segment('MSH') else None,
            "segments": {}
        }
        
        # Extract patient data if present
        if message.segment('PID'):
            pid = message.segment('PID')
            parsed_data["segments"]["PID"] = {
                "patient_id": str(pid[3]) if len(pid) > 3 else None,
                "patient_name": str(pid[5]) if len(pid) > 5 else None,
                "date_of_birth": str(pid[7]) if len(pid) > 7 else None,
                "gender": str(pid[8]) if len(pid) > 8 else None
            }
        
        # Extract observations if present
        obx_segments = []
        for segment in message:
            if str(segment[0]) == 'OBX':
                obx_segments.append({
                    "observation_id": str(segment[3]) if len(segment) > 3 else None,
                    "observation_value": str(segment[5]) if len(segment) > 5 else None,
                    "units": str(segment[6]) if len(segment) > 6 else None,
                    "reference_range": str(segment[7]) if len(segment) > 7 else None
                })
        
        if obx_segments:
            parsed_data["segments"]["OBX"] = obx_segments
        
        parsed_message = ParsedMessage(
            message_id=request.message_id,
            channel_id=request.channel_id,
            message_type="HL7",
            parsed_data=parsed_data,
            timestamp=datetime.fromisoformat(request.timestamp),
            raw_size=len(request.payload)
        )
        
        # Forward to validator
        validation_result = await forward_to_validator(parsed_message)
        
        return {
            "parsed": parsed_data,
            "validation": validation_result,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error parsing HL7 message: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid HL7 message: {str(e)}")

@app.post("/parse/dicom")
async def parse_dicom(request: Request, channel_id: str, study_uid: str, 
                     series_uid: str, instance_uid: str, modality: str):
    try:
        body = await request.body()
        
        # Parse DICOM
        dicom_file = BytesIO(body)
        ds = pydicom.dcmread(dicom_file)
        
        parsed_data = {
            "study_instance_uid": study_uid,
            "series_instance_uid": series_uid,
            "sop_instance_uid": instance_uid,
            "modality": modality,
            "patient_name": str(ds.PatientName) if hasattr(ds, 'PatientName') else None,
            "patient_id": str(ds.PatientID) if hasattr(ds, 'PatientID') else None,
            "study_date": str(ds.StudyDate) if hasattr(ds, 'StudyDate') else None,
            "study_time": str(ds.StudyTime) if hasattr(ds, 'StudyTime') else None,
            "accession_number": str(ds.AccessionNumber) if hasattr(ds, 'AccessionNumber') else None,
            "referring_physician": str(ds.ReferringPhysicianName) if hasattr(ds, 'ReferringPhysicianName') else None
        }
        
        parsed_message = ParsedMessage(
            message_id=instance_uid,
            channel_id=channel_id,
            message_type="DICOM",
            parsed_data=parsed_data,
            timestamp=datetime.utcnow(),
            raw_size=len(body)
        )
        
        # Forward to validator
        validation_result = await forward_to_validator(parsed_message)
        
        return {
            "parsed": parsed_data,
            "validation": validation_result,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error parsing DICOM: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid DICOM data: {str(e)}")

@app.post("/parse/fhir")
async def parse_fhir(channel_id: str, resource_type: str, resource_id: str, payload: dict):
    try:
        # Validate FHIR resource structure
        fhir_resource = construct_fhir_element(resource_type, payload)
        
        parsed_data = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "data": payload
        }
        
        # Extract common fields based on resource type
        if resource_type == "Patient":
            parsed_data["patient_id"] = payload.get("id")
            parsed_data["patient_name"] = payload.get("name", [{}])[0].get("text") if payload.get("name") else None
            
        elif resource_type == "Observation":
            parsed_data["observation_code"] = payload.get("code", {}).get("coding", [{}])[0].get("code")
            parsed_data["observation_value"] = payload.get("valueQuantity", {}).get("value")
            
        parsed_message = ParsedMessage(
            message_id=resource_id,
            channel_id=channel_id,
            message_type="FHIR",
            parsed_data=parsed_data,
            timestamp=datetime.utcnow(),
            raw_size=len(json.dumps(payload))
        )
        
        # Forward to validator
        validation_result = await forward_to_validator(parsed_message)
        
        return {
            "parsed": parsed_data,
            "validation": validation_result,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error parsing FHIR resource: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid FHIR resource: {str(e)}")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}