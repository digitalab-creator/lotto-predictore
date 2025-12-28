#!/bin/bash
# Monitor logs for duplicate combinations and algorithm selection

LOG_FILE="backend/logs/dh_logger_fallback_backend_service/dh_logger_fallback_backend_service.log"

echo "🏴‍☠️  Monitoring combination generation logs..."
echo "Looking for:"
echo "  - Duplicate number warnings"
echo "  - Algorithm selection logs"
echo "  - Combination storage logs"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

tail -f "$LOG_FILE" 2>/dev/null | grep --line-buffered -E "duplicate|Skipping.*combo|algorithm.*selected|best_pair|unique_combinations|Arrr!.*combo|Arrr!.*algorithm|Created algorithm combinations" | while read line; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if echo "$line" | grep -qi "duplicate\|skipping.*combo"; then
        echo "⚠️  [DUPLICATE DETECTED] $timestamp"
        echo "   $line"
        echo ""
    elif echo "$line" | grep -qi "algorithm.*selected\|best_pair\|unique_combinations\|Created algorithm combinations"; then
        echo "🔍 [ALGORITHM SELECTION] $timestamp"
        echo "   $line"
        echo ""
    elif echo "$line" | grep -qi "Arrr!.*combo"; then
        echo "✅ [COMBINATION STORED] $timestamp"
        echo "   $line"
        echo ""
    fi
done
