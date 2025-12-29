#!/bin/bash

# Backend Start Script
# This script starts the FastAPI backend server for the retrieval system

echo "Starting Retrieval Backend Server..."

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo "Error: config.json not found!"
    echo "Please create config.json in the backend directory."
    exit 1
fi

# Check if virtual environment exists (optional)
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Warning: Dependencies may not be installed."
    echo "Run: pip install -r requirements.txt"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set default port if not specified
export PORT=${PORT:-8000}
export HOST=${HOST:-0.0.0.0}

echo "Starting server on $HOST:$PORT..."
echo "Backend will be available at:"
echo "  - http://localhost:$PORT (local)"
echo "  - http://$(hostname -I | awk '{print $1}'):$PORT (network)"
echo "API docs will be available at http://localhost:$PORT/docs"
echo ""
echo "To access from your local machine:"
echo "  1. Create SSH tunnel: ssh -L $PORT:localhost:$PORT user@server-ip"
echo "  2. Or access directly if firewall allows: http://SERVER_IP:$PORT"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python3 main.py

