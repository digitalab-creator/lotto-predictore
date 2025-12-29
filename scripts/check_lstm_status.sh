#!/bin/bash
# Check if LSTM grid search is actually working or stuck
# Praisin' the FSM! 🍝⚓

echo "=== LSTM Grid Search Status Check ==="
echo "Time: $(date)"
echo ""

# 1. Check CPU usage (BEST INDICATOR - if > 0%, it's working!)
echo "--- CPU Usage (BEST INDICATOR) ---"
CPU_USAGE=$(docker stats --no-stream lotto-predictore_backend_1 --format "{{.CPUPerc}}" 2>/dev/null | sed 's/%//' | head -1)
if [ -n "$CPU_USAGE" ]; then
    # Simple numeric comparison (works without bc)
    CPU_INT=$(echo "$CPU_USAGE" | cut -d. -f1)
    if [ "$CPU_INT" -gt 0 ] 2>/dev/null; then
        echo "✅ CPU Usage: ${CPU_USAGE}% - PROCESS IS WORKING! (High CPU = actively processing)"
    else
        echo "⚠️  CPU Usage: ${CPU_USAGE}% - Process might be stuck (0% = not processing)"
    fi
else
    echo "⚠️  Cannot get CPU usage"
fi
echo ""

# 2. Check recent log activity (last 2 minutes)
echo "--- Recent Log Activity (last 2 minutes) ---"
docker logs --since 2m lotto-predictore_backend_1 2>&1 | grep -E "FSM GRID|LSTM|grid_search|evaluation|strong algo" | tail -5
if [ $? -ne 0 ]; then
    echo "⚠️  No recent LSTM-related logs found"
fi
echo ""

# 3. Check if model files are being accessed (recently modified)
echo "--- Model File Activity ---"
MODEL_DIR="/app/models/sequence_classifier"
docker exec lotto-predictore_backend_1 sh -c "find $MODEL_DIR -type f -mmin -5 2>/dev/null | head -5" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  No recent model file activity"
fi
echo ""

# 4. Check database activity (if there are recent queries)
echo "--- Database Activity Check ---"
docker exec lotto-predictore_backend_1 sh -c "psql \$DATABASE_URL -c 'SELECT COUNT(*) FROM predictions WHERE created_at > NOW() - INTERVAL '\''5 minutes'\'';' 2>/dev/null" 2>/dev/null || echo "Cannot check database"
echo ""

# 5. Check memory usage (if memory is increasing, it's working)
echo "--- Memory Usage ---"
docker stats --no-stream lotto-predictore_backend_1 --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# 8. Check for LSTM-specific activity
echo "--- LSTM Grid Search Specific Checks ---"
echo "Checking for 'Loaded existing model' or 'evaluation' in recent logs..."
docker logs --since 10m lotto-predictore_backend_1 2>&1 | grep -E "Loaded existing model|Starting evaluation|evaluation|strong algo" | tail -3
if [ $? -eq 0 ]; then
    echo "✅ Found LSTM activity in logs"
else
    echo "⚠️  No LSTM activity in last 10 minutes"
fi
echo ""

# 6. Check for any error messages
echo "--- Recent Errors (if any) ---"
docker logs --since 5m lotto-predictore_backend_1 2>&1 | grep -iE "error|exception|traceback|failed" | tail -3
if [ $? -ne 0 ]; then
    echo "✅ No recent errors"
fi
echo ""

# 7. Check if the last log entry is recent
echo "--- Last Log Entry ---"
LAST_LOG=$(docker logs --tail 1 lotto-predictore_backend_1 2>&1)
if [ -n "$LAST_LOG" ]; then
    echo "$LAST_LOG"
    # Extract timestamp if possible
    TIMESTAMP=$(echo "$LAST_LOG" | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}" | head -1)
    if [ -n "$TIMESTAMP" ]; then
        echo "Last log timestamp: $TIMESTAMP"
    fi
else
    echo "⚠️  Cannot get last log entry"
fi
echo ""

echo "=== Interpretation ==="
echo "✅ If you see:"
echo "   - Recent log entries (within last 2 minutes)"
echo "   - CPU usage > 0%"
echo "   - Model files being modified"
echo "   → Process is WORKING (just slow)"
echo ""
echo "❌ If you see:"
echo "   - No logs for > 5 minutes"
echo "   - CPU usage = 0%"
echo "   - No file activity"
echo "   → Process might be STUCK"
echo ""

