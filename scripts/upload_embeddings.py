#!/usr/bin/env python3
import os, sys, numpy as np, pandas as pd
from tqdm import tqdm
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# Config
EMBEDDINGS_DIR = "/home/ir/keyframes_new/embedding/embeddings"
COLLECTION_NAME = "AIC_2024_TransNetV2"
BATCH_SIZE = 5000

def calc_time(frame_id, fps=25.0):
    s = frame_id / fps
    h, m = int(s//3600), int((s%3600)//60)
    return f"{h:02d}:{m:02d}:{s%60:06.3f}"

connections.connect(host="localhost", port="19530")
print("✅ Connected to Milvus")

# Create collection
if utility.has_collection(COLLECTION_NAME):
    print(f"⚠️  Collection exists. Drop? (Ctrl+C to cancel)")
    input("Press Enter to continue...")
    utility.drop_collection(COLLECTION_NAME)

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="video", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="frame_id", dtype=DataType.INT64),
    FieldSchema(name="keyframe_path", dtype=DataType.VARCHAR, max_length=512),
    FieldSchema(name="time", dtype=DataType.VARCHAR, max_length=20)
]
schema = CollectionSchema(fields=fields, description="TransNetV2 Keyframes")
collection = Collection(name=COLLECTION_NAME, schema=schema)
print(f"✅ Collection created: {COLLECTION_NAME}")

# Upload each level
total = 0
for i in range(1, 13):
    lvl = f"L{i:02d}"
    vecs = np.load(f"{EMBEDDINGS_DIR}/{lvl}_vectors.npy").astype(np.float32)
    meta = pd.read_csv(f"{EMBEDDINGS_DIR}/{lvl}_meta.csv")
    
    print(f"📤 Uploading {lvl}: {len(vecs):,} vectors")
    
    for start in tqdm(range(0, len(vecs), BATCH_SIZE), desc=lvl):
        end = min(start + BATCH_SIZE, len(vecs))
        batch_v = vecs[start:end]
        batch_m = meta.iloc[start:end]
        
        data = [
            batch_v.tolist(),
            batch_m['video'].tolist(),
            batch_m['video'].tolist(),
            batch_m['frame_id'].astype(int).tolist(),
            batch_m['path'].tolist(),
            [calc_time(f) for f in batch_m['frame_id']]
        ]
        collection.insert(data)
    
    collection.flush()
    total += len(vecs)

print(f"\n✅ Uploaded {total:,} vectors")

# Build index
print("🔧 Building HNSW index...")
collection.create_index(
    field_name="vector",
    index_params={"metric_type": "COSINE", "index_type": "HNSW", 
                  "params": {"M": 32, "efConstruction": 512}}
)
print("✅ Index built!")

# Verify
collection.load()
print(f"✅ Total entities: {collection.num_entities:,}")