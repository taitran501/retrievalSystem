#!/bin/bash
# Complete System Startup Script
# Usage: bash start_system.sh

echo "=========================================="
echo "  Starting Video Retrieval System"
echo "=========================================="

# 1. Start Backend (if not running)
echo ""
echo "1. Checking Backend..."
if ps aux | grep -q "[p]ython.*main.py"; then
    echo "   ✅ Backend already running"
else
    echo "   Starting backend..."
    cd /home/ir/retrievalBaseline/backend
    nohup python3 main.py > backend.log 2>&1 &
    sleep 3
    echo "   ✅ Backend started"
fi

# 2. Start Frontend (if not running)
echo ""
echo "2. Checking Frontend..."
if ps aux | grep -q "[p]ython.*http.server.*8007"; then
    echo "   ✅ Frontend already running"
else
    echo "   Starting frontend..."
    cd /home/ir/retrievalBaseline/frontend
    nohup python3 -m http.server 8007 > frontend.log 2>&1 &
    sleep 2
    echo "   ✅ Frontend started"
fi

# 3. Check Milvus
echo ""
echo "3. Checking Milvus..."
if docker ps | grep -q "milvus-standalone"; then
    echo "   ✅ Milvus running"
else
    echo "   ⚠️  Milvus not running. Start with:"
    echo "      cd /home/ir/retrievalBaseline/database && ./start_milvus.sh"
fi

# 4. Show access info
echo ""
echo "=========================================="
echo "  System Ready!"
echo "=========================================="
echo ""
echo "🌐 LOCAL ACCESS (on server):"
echo "   Frontend: http://localhost:8007"
echo "   Backend:  http://localhost:8000"
echo ""
echo "🔒 REMOTE ACCESS (from Windows):"
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "   1. Open PowerShell/Terminal on Windows"
echo "   2. Run SSH tunnel:"
echo "      ssh -L 18007:localhost:8007 -L 18000:localhost:8000 ir@$SERVER_IP"
echo "   3. Keep that terminal open"
echo "   4. Open browser: http://localhost:18007"
echo ""
echo "📊 CHECK STATUS:"
echo "   bash /home/ir/check_system.sh"
echo ""
echo "🧪 TEST SYSTEM:"
echo "   python3 /home/ir/test_frontend_backend_integration.py"
echo ""
echo "=========================================="
