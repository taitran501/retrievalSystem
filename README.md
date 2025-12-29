# Retrieval System

A full-stack video retrieval system with vector search capabilities using CLIP embeddings and Milvus database.

## Overview

This system provides a comprehensive solution for video content retrieval using:
- **Backend**: FastAPI service with CLIP model for text/image encoding
- **Frontend**: Vue.js 3 application with modern UI
- **Database**: Milvus vector database for efficient similarity search
- **Features**: Temporal queries, OCR processing, sequential search, and more

## Project Structure

```
retrievalSystem/
├── backend/          # FastAPI backend service
├── frontend/         # Vue.js frontend application
├── database/         # Docker compose for Milvus
├── data/             # Data files (keyframes, embeddings)
└── config/           # Configuration files
```

## Features

- **Vector Search**: High-performance similarity search using CLIP embeddings
- **Temporal Queries**: Sequential queries with temporal relationship scoring
- **OCR Processing**: Text extraction from video frames
- **WebSocket Support**: Real-time communication for live queries
- **Multi-modal Search**: Support for both text and image queries
- **Production Ready**: Comprehensive logging, error handling, and health checks

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Node.js 16+
- CUDA-capable GPU (optional, for faster processing)

### Installation

1. **Start Milvus Database**:
   ```bash
   cd database
   docker-compose up -d
   ```

2. **Setup Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Setup Frontend**:
   ```bash
   cd frontend
   npm install
   ```

### Running the System

**Windows**:
```bash
start_all.bat
```

**Linux/Mac**:
```bash
./scripts/start_system.sh
```

This will start:
- Milvus on `localhost:19530`
- Backend API on `http://localhost:8000`
- Frontend on `http://localhost:5173`

## Configuration

### Backend Configuration

Edit `backend/config.json` or set environment variables:

```json
{
  "clip_model_name": "ViT-H-14-378-quickgelu",
  "device": "cuda",
  "milvus_host": "localhost",
  "milvus_port": 19530,
  "collection_name": "AIC_2024_1",
  "search_limit": 3000
}
```

### Frontend Configuration

Frontend configuration is in `frontend/src/` and uses environment variables if needed.

## API Endpoints

- `GET /health` - Health check
- `POST /TextQuery` - Text-based search query
- `GET /config` - Get current configuration
- `WS /ws` - WebSocket connection for real-time queries

## Documentation

See the `docs/` directory for detailed documentation:
- `START.md` - Getting started guide
- `WORKING_FEATURES.md` - List of implemented features
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `QUICK_REFERENCE.md` - Quick reference guide

## Development

### Backend Development

```bash
cd backend
python main.py
# or
uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm run dev
```

### Running Tests

```bash
cd backend
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
