# Mirth Connect Integration Guide

## Overview
This guide explains how to integrate the Compliance Agent with Mirth Connect for passive monitoring of HL7, DICOM, and FHIR messages.

## Integration Methods

### 1. HTTP Writer Destination (Recommended)

Add an HTTP Writer destination to your existing Mirth channels:

#### Step 1: Create HTTP Writer Destination
1. Open Mirth Connect Administrator
2. Edit your channel (e.g., ADT channel)
3. Go to **Destinations** tab
4. Click **Add Destination**
5. Select **HTTP Writer**

#### Step 2: Configure HTTP Writer
```javascript
// Destination Settings
URL: http://compliance-agent:8000/ingest/hl7
Method: POST
Content-Type: application/json
Headers:
  Authorization: Bearer your-token-here
  Content-Type: application/json

// Request Body (JavaScript)
var payload = {
    "channel_id": channelId,
    "payload": Base64.encode(connectorMessage.getEncodedData()),
    "message_id": connectorMessage.getMessageId(),
    "timestamp": new Date().toISOString()
};

return JSON.stringify(payload);
```

#### Step 3: Error Handling
```javascript
// In Response Transformer
if (responseStatus != "200") {
    logger.error("Compliance Agent failed: " + responseStatus);
    // Continue processing - don't block channel
}
```

### 2. Channel Cloning

Create a dedicated compliance channel that mirrors your main channel:

#### Step 1: Clone Existing Channel
1. Right-click your channel → **Clone Channel**
2. Rename to "Compliance - [Original Name]"
3. Change channel ID

#### Step 2: Modify Destination
- Remove original destination
- Add HTTP Writer pointing to Compliance Agent
- Set to **Asynchronous** mode

#### Step 3: Configure Source
```javascript
// Source Connector → Response
// Send to both original destination AND compliance channel
var complianceMsg = message;
router.routeMessage('compliance-channel-id', complianceMsg);
```

### 3. Database Polling (Alternative)

If direct HTTP isn't suitable, use database polling:

#### Step 1: Configure Database Writer
```sql
-- Add to your existing database destination
INSERT INTO compliance_queue (
    message_id, 
    channel_id, 
    message_type, 
    raw_message, 
    created_at
) VALUES (
    '${message.messageId}',
    '${channelId}',
    'HL7',
    '${Base64.encode(message.rawData)}',
    NOW()
);
```

#### Step 2: Create Polling Channel
```javascript
// Database Reader Source
SELECT * FROM compliance_queue WHERE processed = 0 LIMIT 100;

// Destination: HTTP Writer to Compliance Agent
var payload = {
    "channel_id": msg['channel_id'],
    "payload": msg['raw_message'],
    "message_id": msg['message_id']
};

// Mark as processed
UPDATE compliance_queue SET processed = 1 WHERE id = ${msg['id']};
```

## DICOM Integration

### DICOM C-STORE Listener
```javascript
// In your DICOM channel destination
var dicomMetadata = {
    "channel_id": channelId,
    "study_uid": msg['studyInstanceUID'],
    "series_uid": msg['seriesInstanceUID'], 
    "instance_uid": msg['sopInstanceUID'],
    "modality": msg['modality'],
    "metadata": {
        "patient_id": msg['patientID'],
        "patient_name": msg['patientName'],
        "study_date": msg['studyDate']
    }
};

// Send DICOM file + metadata
var httpConnector = new HTTPConnector();
httpConnector.setUrl("http://compliance-agent:8000/ingest/dicom");
httpConnector.setMethod("POST");
httpConnector.setHeaders({
    "Authorization": "Bearer your-token",
    "Content-Type": "application/dicom"
});
httpConnector.setParams(dicomMetadata);
httpConnector.setBinaryData(msg.getRawData());
httpConnector.send();
```

## FHIR Integration

### FHIR REST Listener
```javascript
// In FHIR channel destination
var fhirResource = JSON.parse(msg.getRawData());

var payload = {
    "channel_id": channelId,
    "resource_type": fhirResource.resourceType,
    "resource_id": fhirResource.id,
    "payload": fhirResource
};

// Send to Compliance Agent
var response = router.routeMessageByChannelId(
    'compliance-fhir-channel',
    JSON.stringify(payload)
);
```

## Configuration Templates

### Mirth Channel Template
```xml
<channel version="3.12.0">
    <id>compliance-hl7-monitor</id>
    <name>Compliance HL7 Monitor</name>
    <description>Passive monitoring for compliance</description>
    
    <sourceConnector version="3.12.0">
        <name>sourceConnector</name>
        <properties class="com.mirth.connect.connectors.tcp.TcpReceiverProperties">
            <pluginProperties/>
            <listenerConnectorProperties>
                <host>0.0.0.0</host>
                <port>6661</port>
            </listenerConnectorProperties>
            <serverMode>true</serverMode>
            <remoteAddress>0.0.0.0</remoteAddress>
            <remotePort>6661</remotePort>
        </properties>
    </sourceConnector>
    
    <destinationConnectors>
        <connector version="3.12.0">
            <name>Compliance Agent</name>
            <properties class="com.mirth.connect.connectors.http.HttpSenderProperties">
                <pluginProperties/>
                <destinationConnectorProperties>
                    <queueEnabled>false</queueEnabled>
                    <sendTimeout>30000</sendTimeout>
                    <template>${JSON.stringify({
                        "channel_id": channelId,
                        "payload": Base64.encode(connectorMessage.getEncodedData()),
                        "message_id": connectorMessage.getMessageId(),
                        "timestamp": new Date().toISOString()
                    })}</template>
                </destinationConnectorProperties>
                <url>http://compliance-agent:8000/ingest/hl7</url>
                <method>POST</method>
                <headers>
                    <entry>
                        <string>Authorization</string>
                        <string>Bearer your-token-here</string>
                    </entry>
                    <entry>
                        <string>Content-Type</string>
                        <string>application/json</string>
                    </entry>
                </headers>
            </properties>
        </connector>
    </destinationConnectors>
</channel>
```

## Best Practices

### 1. Non-Blocking Integration
```javascript
// Always use try-catch to prevent blocking main flow
try {
    var response = sendToComplianceAgent(message);
    if (response.status !== 200) {
        logger.warn("Compliance agent unavailable: " + response.status);
    }
} catch (e) {
    logger.error("Compliance agent error: " + e.message);
    // Continue normal processing
}
```

### 2. Async Processing
```javascript
// Use async destinations to avoid blocking
destinationConnector.setQueueEnabled(true);
destinationConnector.setThreadCount(2);
```

### 3. Message Filtering
```javascript
// Only send relevant messages to compliance agent
if (msg['MSH']['MSH.9']['MSH.9.1'] == 'ADT' || 
    msg['MSH']['MSH.9']['MSH.9.1'] == 'ORU') {
    // Send to compliance agent
    sendToComplianceAgent(message);
}
```

### 4. Rate Limiting
```javascript
// Implement basic rate limiting
var lastSent = globalMap.get('lastComplianceSent') || 0;
var now = Date.now();

if (now - lastSent > 100) { // Max 10 messages/second
    sendToComplianceAgent(message);
    globalMap.put('lastComplianceSent', now);
}
```

## Monitoring Integration

### Health Check Channel
```javascript
// Create a periodic health check
var healthCheck = {
    url: "http://compliance-agent:8000/health",
    method: "GET",
    timeout: 5000
};

var response = httpCall(healthCheck);
if (response.status !== 200) {
    alertManager.send("Compliance Agent is down!");
}
```

### Metrics Collection
```javascript
// Collect metrics from compliance agent
var metrics = httpCall({
    url: "http://compliance-agent:8000/metrics",
    method: "GET"
});

// Parse and store in Mirth statistics
channelUtil.setStatistic("compliance_messages_total", 
    parseMetric(metrics.body, "ingress_messages_total"));
```

## Deployment Configuration

### Docker Compose Update
```yaml
# Add to your existing docker-compose.yml
services:
  mirth:
    image: nextgenhealthcare/connect:latest
    ports:
      - "8080:8080"
      - "6661:6661"
    networks:
      - compliance-net
    depends_on:
      - compliance-agent
    environment:
      - COMPLIANCE_AGENT_URL=http://ingress-service:8000
```

### Network Configuration
```yaml
# Ensure services can communicate
networks:
  compliance-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Troubleshooting

### Common Issues
1. **Connection timeout**: Increase Mirth send timeout
2. **Memory issues**: Reduce message batch size
3. **SSL errors**: Configure proper certificates
4. **Rate limiting**: Implement exponential backoff

### Debug Channel
```javascript
// Create debug channel for testing
logger.info("Sending to compliance agent: " + JSON.stringify(payload));
var response = sendToComplianceAgent(payload);
logger.info("Response: " + response.status + " - " + response.body);
```

## Security Considerations

1. **Authentication**: Use proper bearer tokens
2. **Network**: Isolate compliance traffic
3. **Encryption**: Enable TLS for all communications
4. **Monitoring**: Log all compliance interactions
5. **Failover**: Implement circuit breaker pattern

This integration ensures your Mirth Connect channels passively forward messages to the Compliance Agent without disrupting normal operations.