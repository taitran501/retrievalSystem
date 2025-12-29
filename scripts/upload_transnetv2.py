#!/usr/bin/env python3
import os, sys, numpy as np, pandas as pd
from tqdm import tqdm
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

EMBEDDINGS_DIR = "/home/ir/keyframes_new/embedding/embeddings"
COLLECTION_NAME = "AIC_2024_TransNetV2"
BATCH_SIZE = 5000

def calc_time(frame_id, fps=25.0):
    """Calculate HH:MM:SS.mmm from frame_id"""
    s = frame_id / fps
    h, m = int(s//3600), int((s%3600)//60)
    return f"{h:02d}:{m:02d}:{s%60:06.3f}"

print("Connecting to Milvus...")
connections.connect(host="localhost", port="19530")
print("✅ Connected\n")

# Check if collection exists
if utility.has_collection(COLLECTION_NAME):
    print(f"⚠️  Collection '{COLLECTION_NAME}' already exists!")
    print(f"Current entities: {Collection(COLLECTION_NAME).num_entities:,}")
    resp = input("Drop and recreate? (yes/no): ")
    if resp.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)
    utility.drop_collection(COLLECTION_NAME)
    print("✅ Dropped old collection\n")

# Create schema (matching existing collections)
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="video", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="frame_id", dtype=DataType.INT64),
    FieldSchema(name="keyframe_path", dtype=DataType.VARCHAR, max_length=512),
    FieldSchema(name="time", dtype=DataType.VARCHAR, max_length=20)
]
schema = CollectionSchema(fields=fields, description="TransNetV2 Scene-Based Keyframes")
collection = Collection(name=COLLECTION_NAME, schema=schema)
print(f"✅ Collection created: {COLLECTION_NAME}\n")

# Upload level by level
total_uploaded = 0
for level_num in range(1, 13):
    level_id = f"L{level_num:02d}"
    
    vec_file = f"{EMBEDDINGS_DIR}/{level_id}_vectors.npy"
    meta_file = f"{EMBEDDINGS_DIR}/{level_id}_meta.csv"
    
    if not os.path.exists(vec_file):
        print(f"⚠️  Skipping {level_id}: file not found")
        continue
    
    vectors = np.load(vec_file).astype(np.float32)
    meta = pd.read_csv(meta_file)
    
    print(f"📤 Uploading {level_id}: {len(vectors):,} vectors")
    
    # Upload in batches
    for start_idx in tqdm(range(0, len(vectors), BATCH_SIZE), desc=f"  {level_id}"):
        end_idx = min(start_idx + BATCH_SIZE, len(vectors))
        
        batch_vectors = vectors[start_idx:end_idx]
        batch_meta = meta.iloc[start_idx:end_idx]
        
        # Prepare data
        data = [
            batch_vectors.tolist(),
            batch_meta['video'].tolist(),
            batch_meta['video'].tolist(),  # video_id same as video
            batch_meta['frame_id'].astype(int).tolist(),
            batch_meta['path'].tolist(),
            [calc_time(f) for f in batch_meta['frame_id']]
        ]
        
        collection.insert(data)
    
    collection.flush()
    total_uploaded += len(vectors)
    print(f"  ✅ {level_id} complete: {len(vectors):,} vectors\n")

print(f"\n{'='*60}")
print(f"✅ Upload Complete!")
print(f"{'='*60}")
print(f"Total uploaded: {total_uploaded:,} vectors")

# Build index
print("\n🔧 Building HNSW index (this may take 5-10 minutes)...")
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 32, "efConstruction": 512}
}
collection.create_index(field_name="vector", index_params=index_params)
print("✅ Index built!\n")

# Load and verify
collection.load()
final_count = collection.num_entities
print(f"{'='*60}")
print(f"✅ Verification:")
print(f"{'='*60}")
print(f"Collection: {COLLECTION_NAME}")
print(f"Entities: {final_count:,}")
print(f"Status: {'✅ SUCCESS' if final_count == total_uploaded else '⚠️  COUNT MISMATCH'}")
print(f"\n🎯 Ready to use in backend!")

connections.disconnect("default")
