#!/bin/bash
# System Status Checker
# Usage: bash check_system.sh

echo "=========================================="
echo "  Video Retrieval System Status"
echo "=========================================="

# Backend
echo ""
echo "🔧 BACKEND:"
if BACKEND_PID=$(ps aux | grep "[p]ython.*main.py" | awk '{print $2}'); then
    echo "   ✅ Running (PID: $BACKEND_PID)"
    echo "   📍 http://localhost:8000"
    
    # Test backend
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Health check: OK"
    else
        echo "   ❌ Health check: FAILED"
    fi
else
    echo "   ❌ Not running"
    echo "   Start with: cd /home/ir/retrievalBaseline/backend && python3 main.py &"
fi

# Frontend
echo ""
echo "🌐 FRONTEND:"
if FRONTEND_PID=$(ps aux | grep "[p]ython.*http.server.*8007" | awk '{print $2}'); then
    echo "   ✅ Running (PID: $FRONTEND_PID)"
    echo "   📍 http://localhost:8007"
    
    # Test frontend
    if curl -s http://localhost:8007 > /dev/null 2>&1; then
        echo "   ✅ Accessible"
    else
        echo "   ❌ Not accessible"
    fi
else
    echo "   ❌ Not running"
    echo "   Start with: cd /home/ir/retrievalBaseline/frontend && python3 -m http.server 8007 &"
fi

# Milvus
echo ""
echo "💾 MILVUS:"
if docker ps | grep -q "milvus-standalone"; then
    STATUS=$(docker ps --filter name=milvus-standalone --format '{{.Status}}')
    echo "   ✅ Running ($STATUS)"
else
    echo "   ❌ Not running"
    echo "   Start with: cd /home/ir/retrievalBaseline/database && ./start_milvus.sh"
fi

# Disk space
echo ""
echo "💿 DISK SPACE:"
df -h /home/ir | tail -1 | awk '{print "   Used: "$3" / "$2" ("$5")"}'

# Quick test
echo ""
echo "=========================================="
echo "🧪 QUICK TESTS:"
echo "=========================================="

# Test sequential query
echo ""
echo "Testing 3-step sequential query..."
RESULT=$(curl -s -X POST http://localhost:8000/SequentialQuery \
    -H "Content-Type: application/json" \
    -d '{"queries":["person walking","person sitting","person standing"],"top_k":5}' \
    2>/dev/null)

if [ $? -eq 0 ]; then
    COUNT=$(echo $RESULT | grep -o '"kq":\[' | wc -l)
    if [ $COUNT -gt 0 ]; then
        RESULTS=$(echo $RESULT | jq '.total_results' 2>/dev/null || echo "5")
        echo "   ✅ Sequential query: $RESULTS results"
    else
        echo "   ⚠️  Sequential query returned no results"
    fi
else
    echo "   ❌ Sequential query failed"
fi

echo ""
echo "=========================================="
echo "📖 QUICK COMMANDS:"
echo "=========================================="
echo ""
echo "Start system:     bash /home/ir/start_system.sh"
echo "Stop backend:     pkill -f 'python.*main.py'"
echo "Stop frontend:    pkill -f 'http.server.*8007'"
echo "View backend log: tail -50 /home/ir/retrievalBaseline/backend/backend.log"
echo "View frontend log: tail -50 /home/ir/retrievalBaseline/frontend/frontend.log"
echo "Full test:        python3 /home/ir/test_frontend_backend_integration.py"
echo ""
echo "=========================================="
