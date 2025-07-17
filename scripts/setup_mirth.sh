#!/bin/bash

echo "Setting up Mirth Connect integration..."

# Check if Mirth is running
MIRTH_URL="http://localhost:8080/api"
MIRTH_USERNAME="admin"
MIRTH_PASSWORD="admin"

echo "Checking Mirth Connect status..."
curl -s -f "$MIRTH_URL/users/current" -u "$MIRTH_USERNAME:$MIRTH_PASSWORD" > /dev/null

if [ $? -eq 0 ]; then
    echo "✓ Mirth Connect is accessible"
else
    echo "✗ Cannot connect to Mirth Connect at $MIRTH_URL"
    echo "Please ensure Mirth Connect is running and accessible"
    exit 1
fi

# Create compliance monitoring channel
echo "Creating compliance monitoring channel..."

# Generate authentication token for compliance agent
COMPLIANCE_TOKEN=$(openssl rand -hex 32)
echo "Generated compliance token: $COMPLIANCE_TOKEN"

# Update docker-compose to include Mirth
cat << EOF >> docker-compose.yml

  # Mirth Connect
  mirth:
    image: nextgenhealthcare/connect:latest
    container_name: mirth-connect
    ports:
      - "8080:8080"
      - "6661:6661"
    networks:
      - compliance-net
    environment:
      - COMPLIANCE_AGENT_TOKEN=$COMPLIANCE_TOKEN
    volumes:
      - ./examples/mirth-channel-example.xml:/opt/connect/conf/channel-example.xml:ro
    depends_on:
      - ingress-service

EOF

# Update ingress service to accept the token
echo "Updating ingress service configuration..."
sed -i "s/your-token-here/$COMPLIANCE_TOKEN/g" examples/mirth-channel-example.xml

# Create Mirth configuration script
cat << 'EOF' > scripts/configure_mirth.js
// Mirth Connect configuration script
// Run this in Mirth Connect Administrator > Extensions > Script Console

// Function to send message to compliance agent
function sendToComplianceAgent(message, channelId) {
    try {
        var payload = {
            "channel_id": channelId,
            "payload": Base64.encode(message),
            "message_id": UUIDGenerator.getUUID(),
            "timestamp": new Date().toISOString()
        };
        
        var httpConnector = new HTTPConnector();
        httpConnector.setUrl("http://ingress-service:8000/ingest/hl7");
        httpConnector.setMethod("POST");
        httpConnector.setHeaders({
            "Authorization": "Bearer " + System.getProperty("COMPLIANCE_AGENT_TOKEN"),
            "Content-Type": "application/json"
        });
        httpConnector.setPayload(JSON.stringify(payload));
        
        var response = httpConnector.send();
        
        if (response.getStatus() == 200) {
            logger.info("Message sent to compliance agent successfully");
        } else {
            logger.warn("Compliance agent returned status: " + response.getStatus());
        }
        
        return response;
        
    } catch (e) {
        logger.error("Error sending to compliance agent: " + e.getMessage());
        // Don't throw - continue normal processing
        return null;
    }
}

// Global function to add compliance monitoring to existing channels
function addComplianceMonitoring(channelId) {
    var channel = Channels.getChannel(channelId);
    if (!channel) {
        logger.error("Channel not found: " + channelId);
        return false;
    }
    
    // Add compliance destination
    var complianceDestination = new Connector();
    complianceDestination.setName("Compliance Agent");
    complianceDestination.setTransportName("HTTP Writer");
    complianceDestination.setMode("DESTINATION");
    complianceDestination.setEnabled(true);
    complianceDestination.setWaitForPrevious(false);
    
    var httpProperties = new HTTPSenderProperties();
    httpProperties.setUrl("http://ingress-service:8000/ingest/hl7");
    httpProperties.setMethod("POST");
    httpProperties.setHeaders([
        new Property("Authorization", "Bearer " + System.getProperty("COMPLIANCE_AGENT_TOKEN")),
        new Property("Content-Type", "application/json")
    ]);
    httpProperties.setTemplate(
        '${JSON.stringify({' +
        '"channel_id": "' + channelId + '",' +
        '"payload": Base64.encode(connectorMessage.getEncodedData()),' +
        '"message_id": connectorMessage.getMessageId(),' +
        '"timestamp": new Date().toISOString()' +
        '})}'
    );
    
    complianceDestination.setProperties(httpProperties);
    
    // Add to channel
    channel.addDestination(complianceDestination);
    
    // Save channel
    Channels.updateChannel(channel, true);
    
    logger.info("Added compliance monitoring to channel: " + channelId);
    return true;
}

// Example usage:
// addComplianceMonitoring("your-channel-id");

logger.info("Compliance monitoring functions loaded");
EOF

echo "✓ Mirth integration setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the compliance agent: make up"
echo "2. Import the channel: examples/mirth-channel-example.xml"
echo "3. Run the configuration script in Mirth Administrator"
echo "4. Test with: curl -d 'MSH|^~\\&|TEST|TEST|TEST|TEST|...' localhost:6661"
echo ""
echo "Authentication token: $COMPLIANCE_TOKEN"
echo "Store this token securely - it's needed for authentication"