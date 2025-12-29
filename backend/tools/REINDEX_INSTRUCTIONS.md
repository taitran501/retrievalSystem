# MILVUS RE-INDEXING - MANUAL STEPS

## Issue
Docker Desktop is not running, so Milvus cannot start.

## Steps to Re-index

### 1. Start Docker Desktop
```
- Open Docker Desktop application
- Wait for it to fully start (system tray icon should be green)
```

### 2. Start Milvus
```bash
cd c:/Users/trant/Documents/retrieval_system/retrievalSystem/database
docker-compose up -d

# Wait 10-15 seconds for Milvus to initialize
```

### 3. Run Re-indexing Script
```bash
cd c:/Users/trant/Documents/retrieval_system/retrievalSystem/backend
python reindex_milvus.py
```

This will:
- ✅ Drop old collection (if exists)  
- ✅ Create new collection with proper schema
- ✅ Index ALL L01-L24 embeddings (~700K+ vectors)
- ✅ Create HNSW index for fast search
- ✅ Load collection to memory

Expected time: **5-10 minutes** depending on system

### 4. Verify
```bash
# Check collection stats
python -c "from pymilvus import connections, Collection; connections.connect(); c = Collection('AIC_2024_TransNetV2_Full'); print(f'Total: {c.num_entities:,} vectors')"
```

---

## What's Been Prepared

✅ **Data verified**: 
  - L01-L24 embeddings (24 batches)
  - L01-L24 keyframes (24 directories)
  - Total: 48 .npy files + 48 .csv files

✅ **Script created**: `reindex_milvus.py`
  - Auto-detects all batches
  - Inserts in chunks (5000 vectors/batch)
  - Creates optimized HNSW index

---

## Once Complete

Your system will have:
- **Full dataset indexed** (not just L01-L12)
- **All missing keyframes** available for search
- **Better accuracy** on queries like "con lân", "rác", "đám cháy"
