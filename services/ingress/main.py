from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from datetime import datetime
import base64
import uuid
import httpx
import logging
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Compliance Agent Ingress", version="0.9.0")
security = HTTPBearer()

message_counter = Counter('ingress_messages_total', 'Total messages received', ['type', 'channel'])
message_size_histogram = Histogram('ingress_message_size_bytes', 'Message size distribution')
processing_time_histogram = Histogram('ingress_processing_seconds', 'Processing time distribution')

class HL7Message(BaseModel):
    channel_id: str = Field(..., description="Source channel identifier")
    payload: str = Field(..., description="Base64 encoded HL7 message")
    message_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

class DICOMMessage(BaseModel):
    channel_id: str
    study_uid: str
    series_uid: str
    instance_uid: str
    modality: str
    metadata: dict = Field(default_factory=dict)

class FHIRMessage(BaseModel):
    channel_id: str
    resource_type: str
    resource_id: str
    payload: dict

class MessageResponse(BaseModel):
    message_id: str
    status: str
    timestamp: datetime
    validation_result: Optional[dict] = None

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # TODO: Implement proper JWT validation
    if not token:
        raise HTTPException(status_code=403, detail="Invalid authentication")
    return token

@app.post("/ingest/hl7", response_model=MessageResponse)
async def ingest_hl7(message: HL7Message, token: str = Depends(verify_token)):
    with processing_time_histogram.time():
        try:
            decoded_payload = base64.b64decode(message.payload).decode('utf-8')
            message_size_histogram.observe(len(decoded_payload))
            message_counter.labels(type='hl7', channel=message.channel_id).inc()
            
            # Forward to parser service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://parser-service:8001/parse/hl7",
                    json={
                        "message_id": message.message_id,
                        "channel_id": message.channel_id,
                        "payload": decoded_payload,
                        "timestamp": message.timestamp.isoformat()
                    }
                )
                response.raise_for_status()
                
            return MessageResponse(
                message_id=message.message_id,
                status="accepted",
                timestamp=datetime.utcnow(),
                validation_result=response.json()
            )
            
        except Exception as e:
            logger.error(f"Error processing HL7 message: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/dicom", response_model=MessageResponse)
async def ingest_dicom(request: Request, message: DICOMMessage, token: str = Depends(verify_token)):
    with processing_time_histogram.time():
        try:
            body = await request.body()
            message_size_histogram.observe(len(body))
            message_counter.labels(type='dicom', channel=message.channel_id).inc()
            
            # Forward to parser service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://parser-service:8001/parse/dicom",
                    content=body,
                    headers={"Content-Type": "application/dicom"},
                    params={
                        "channel_id": message.channel_id,
                        "study_uid": message.study_uid,
                        "series_uid": message.series_uid,
                        "instance_uid": message.instance_uid,
                        "modality": message.modality
                    }
                )
                response.raise_for_status()
                
            return MessageResponse(
                message_id=str(uuid.uuid4()),
                status="accepted",
                timestamp=datetime.utcnow(),
                validation_result=response.json()
            )
            
        except Exception as e:
            logger.error(f"Error processing DICOM message: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/fhir", response_model=MessageResponse)
async def ingest_fhir(message: FHIRMessage, token: str = Depends(verify_token)):
    with processing_time_histogram.time():
        try:
            message_counter.labels(type='fhir', channel=message.channel_id).inc()
            
            # Forward to parser service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://parser-service:8001/parse/fhir",
                    json={
                        "channel_id": message.channel_id,
                        "resource_type": message.resource_type,
                        "resource_id": message.resource_id,
                        "payload": message.payload
                    }
                )
                response.raise_for_status()
                
            return MessageResponse(
                message_id=str(uuid.uuid4()),
                status="accepted",
                timestamp=datetime.utcnow(),
                validation_result=response.json()
            )
            
        except Exception as e:
            logger.error(f"Error processing FHIR message: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return generate_latest()

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}