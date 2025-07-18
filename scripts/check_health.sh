#!/bin/bash
# Health check script for Linux/macOS
# Checks if all compliance agent services are running correctly

echo "========================================"
echo "Compliance Agent Health Check"
echo "========================================"
echo

# Function to check service health
check_service() {
    local name=$1
    local port=$2
    local endpoint=${3:-/health}
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port$endpoint" 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "✓ $name service (port $port) is healthy"
    else
        echo "✗ $name service (port $port) is not responding (HTTP $response)"
    fi
}

echo "Checking application services..."
echo
check_service "Ingress" 8000
check_service "Parser" 8001
check_service "Validator" 8002
check_service "HashWriter" 8003
check_service "Reporter" 8004

echo
echo "Checking infrastructure services..."
echo

# Check Elasticsearch
es_response=$(curl -s -u elastic:changeme "http://localhost:9200/_cluster/health" 2>/dev/null)
if [ $? -eq 0 ]; then
    es_status=$(echo "$es_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "✓ Elasticsearch is $es_status"
else
    echo "✗ Elasticsearch is not responding"
fi

# Check MinIO
minio_response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:9000/minio/health/live" 2>/dev/null)
if [ "$minio_response" = "200" ]; then
    echo "✓ MinIO is healthy"
else
    echo "✗ MinIO is not responding"
fi

# Check Kibana
kibana_response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5601/api/status" 2>/dev/null)
if [ "$kibana_response" = "200" ]; then
    echo "✓ Kibana is healthy"
else
    echo "✗ Kibana is not responding"
fi

echo
echo "========================================"
echo "Health check completed"
echo "========================================"
echo
echo "Web interfaces:"
echo "- Kibana: http://localhost:5601 (elastic/changeme)"
echo "- MinIO: http://localhost:9001 (minioadmin/minioadmin)"
echo