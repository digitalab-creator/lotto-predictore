#!/bin/bash
# Test the email endpoint

echo "🏴‍☠️ Testing weekly combinations email endpoint..."
echo ""

# First check if backend is up
echo "1. Checking backend health..."
curl -s "http://localhost:8000/health" | head -3
echo ""
echo ""

# Check if email service is up  
echo "2. Checking email service health..."
curl -s "http://localhost:8001/health" | head -3
echo ""
echo ""

# Try the endpoint with timeout
echo "3. Calling send-weekly-combinations-email (10s timeout)..."
timeout 10 curl -X POST "http://localhost:8000/cron/send-weekly-combinations-email" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\nTotal time: %{time_total}s\n" \
  2>&1 || echo "❌ Request timed out or failed"
echo ""

echo "4. Checking recent logs..."
tail -20 backend/logs/dh_logger_fallback_backend_service/dh_logger_fallback_backend_service.log 2>/dev/null | grep -E "send-weekly|Querying|Found|Error|error" | tail -10 || echo "No relevant logs found"
