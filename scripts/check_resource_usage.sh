#!/bin/bash
# Check if resource usage is normal or concerning
# Praisin' the FSM! 🍝⚓

echo "=== Resource Usage Analysis ==="
echo ""

# Get CPU and memory stats
CPU_PERC=$(docker stats --no-stream lotto-predictore_backend_1 --format "{{.CPUPerc}}" 2>/dev/null | sed 's/%//')
MEM_USAGE=$(docker stats --no-stream lotto-predictore_backend_1 --format "{{.MemPerc}}" 2>/dev/null | sed 's/%//')

echo "Current Usage:"
echo "  CPU: ${CPU_PERC}%"
echo "  Memory: ${MEM_USAGE}%"
echo ""

# Check CPU allocation
echo "Resource Allocation (from docker-compose.yml):"
echo "  Backend Container: 2 CPUs allocated, 1.5GB memory limit"
echo "  Server Total: 4 CPU cores"
echo ""

# Interpretation
echo "=== Interpretation ==="
echo ""

# CPU Analysis
CPU_INT=$(echo "$CPU_PERC" | cut -d. -f1)
if [ "$CPU_INT" -gt 200 ] 2>/dev/null; then
    echo "⚠️  CPU Usage: ${CPU_PERC}%"
    echo "   → Using > 2 CPUs (more than allocated)"
    echo "   → Process is very CPU-intensive"
    echo "   → Consider: This is normal for LSTM evaluation, but might benefit from optimization"
elif [ "$CPU_INT" -gt 150 ] 2>/dev/null; then
    echo "✅ CPU Usage: ${CPU_PERC}%"
    echo "   → Using ~1.5-2 CPUs (within allocation)"
    echo "   → Process is working hard (normal for LSTM)"
elif [ "$CPU_INT" -gt 100 ] 2>/dev/null; then
    echo "✅ CPU Usage: ${CPU_PERC}%"
    echo "   → Using ~1 CPU (well within 2 CPU allocation)"
    echo "   → Process is actively working"
elif [ "$CPU_INT" -gt 0 ] 2>/dev/null; then
    echo "✅ CPU Usage: ${CPU_PERC}%"
    echo "   → Process is working (using < 1 CPU)"
else
    echo "❌ CPU Usage: ${CPU_PERC}%"
    echo "   → Process might be stuck (0% CPU)"
fi
echo ""

# Memory Analysis
MEM_INT=$(echo "$MEM_USAGE" | cut -d. -f1)
if [ "$MEM_INT" -gt 90 ] 2>/dev/null; then
    echo "⚠️  Memory Usage: ${MEM_USAGE}%"
    echo "   → High memory usage (> 90%)"
    echo "   → Consider monitoring for memory leaks"
elif [ "$MEM_INT" -gt 70 ] 2>/dev/null; then
    echo "✅ Memory Usage: ${MEM_USAGE}%"
    echo "   → Moderate memory usage (70-90%)"
    echo "   → Normal for ML workloads"
else
    echo "✅ Memory Usage: ${MEM_USAGE}%"
    echo "   → Good memory usage (< 70%)"
fi
echo ""

echo "=== Summary ==="
if [ "$CPU_INT" -gt 0 ] && [ "$CPU_INT" -lt 200 ] && [ "$MEM_INT" -lt 90 ]; then
    echo "✅ Resources are SUFFICIENT"
    echo "   → CPU: Using allocated resources efficiently"
    echo "   → Memory: Within safe limits"
    echo "   → Process is working normally"
elif [ "$CPU_INT" -gt 200 ]; then
    echo "⚠️  CPU usage exceeds allocation"
    echo "   → Process is very CPU-intensive"
    echo "   → Consider: Add more CPUs or optimize LSTM evaluation"
else
    echo "❌ Process might be stuck or idle"
fi
echo ""


