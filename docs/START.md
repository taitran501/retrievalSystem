# Quick Start

## Connect
```bash
ssh -L 8080:localhost:8080 -L 8000:localhost:8000 user@192.168.28.32
```

## Access
```
http://localhost:8080
```

## Services
- Frontend: Port 8080
- Backend: Port 8000
- Milvus: Port 19530

## Restart Services
```bash
# Frontend
cd /home/ir/retrievalBaseline/frontend
pkill -f "http.server.*8080"
nohup python3 -m http.server 8080 > frontend.log 2>&1 &

# Backend
cd /home/ir/retrievalBaseline/backend
pkill -f "python.*main.py"
nohup python3 main.py > backend.log 2>&1 &

# Database
cd /home/ir/retrievalBaseline/database
bash start_milvus.sh
```

## Check Status
```bash
# Verify all services
netstat -tlnp | grep -E "8080|8000|19530"

# Backend health
curl http://localhost:8000/health
```

## Visual Concept Search
- Click "Visual" tab (purple badge "NEW")
- Enter Vietnamese or English query
- Gets better results for non-English queries
