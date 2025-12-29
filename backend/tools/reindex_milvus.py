"""
Milvus Re-indexing Script
Drops old collection and re-indexes with complete L01-L24 dataset
"""

import os
import glob
import numpy as np
import pandas as pd
from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType
from tqdm import tqdm
import time

# Configuration
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
COLLECTION_NAME = "AIC_2024_TransNetV2_Full"
EMBEDDINGS_DIR = "c:/Users/trant/Documents/retrieval_system/retrievalSystem/data/embeddings"
KEYFRAMES_BASE = "c:/Users/trant/Documents/retrieval_system/retrievalSystem/data/keyframes"

print("=" * 60)
print("MILVUS RE-INDEXING SCRIPT")
print("=" * 60)

# Step 1: Connect to Milvus
print("\n[1/4] Connecting to Milvus...")
connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
print(f"✅ Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")

# Step 2: Drop old collection if exists
print(f"\n[2/4] Checking for existing collection '{COLLECTION_NAME}'...")
if utility.has_collection(COLLECTION_NAME):
    print(f"⚠️  Found existing collection: {COLLECTION_NAME}")
    print(f"🗑️  Dropping collection...")
    utility.drop_collection(COLLECTION_NAME)
    print(f"✅ Old collection dropped successfully")
else:
    print(f"ℹ️  No existing collection found")

# Step 3: Create new collection
print(f"\n[3/4] Creating new collection '{COLLECTION_NAME}'...")

# Define schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="video", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="frame_id", dtype=DataType.INT64),
    FieldSchema(name="path", dtype=DataType.VARCHAR, max_length=200)
]

schema = CollectionSchema(fields=fields, description="AIC 2024 keyframes with TransNetV2")
collection = Collection(name=COLLECTION_NAME, schema=schema)

print("✅ Collection created with schema:")
print(f"   - Dimension: 768")
print(f"   - Fields: id, vector, video, frame_id, path")

# Step 4: Insert data from all batches (L01-L24)
print(f"\n[4/4] Indexing data from embeddings...")

# Find all embedding files
meta_files = sorted(glob.glob(f"{EMBEDDINGS_DIR}/L*_meta.csv"))
vector_files = sorted(glob.glob(f"{EMBEDDINGS_DIR}/L*_vectors.npy"))

print(f"📊 Found {len(meta_files)} batches to index")

total_inserted = 0
batch_size = 5000  # Insert in batches of 5000

for meta_file, vector_file in tqdm(zip(meta_files, vector_files), desc="Processing batches", total=len(meta_files)):
    batch_name = os.path.basename(meta_file).replace("_meta.csv", "")
    
    # Load metadata and vectors
    meta_df = pd.read_csv(meta_file)
    vectors = np.load(vector_file).astype(np.float32)
    
    if len(meta_df) != len(vectors):
        print(f"\n⚠️  WARNING: Mismatch in {batch_name}: {len(meta_df)} metadata vs {len(vectors)} vectors")
        continue
    
    # Prepare data for insertion
    num_records = len(meta_df)
    
    # Insert in smaller batches to avoid memory issues
    for i in range(0, num_records, batch_size):
        end = min(i + batch_size, num_records)
        
        # Convert numpy array to list properly (each vector as a list)
        batch_vectors = [vec.tolist() for vec in vectors[i:end]]
        
        batch_data = [
            batch_vectors,
            meta_df['video'].iloc[i:end].tolist(),
            meta_df['frame_id'].iloc[i:end].astype(int).tolist(),
            meta_df['path'].iloc[i:end].tolist()
        ]
        
        collection.insert(batch_data)
        total_inserted += (end - i)
    
    tqdm.write(f"  ✓ {batch_name}: {num_records:,} vectors indexed")

print(f"\n✅ Total vectors inserted: {total_inserted:,}")

# Step 5: Create index
print("\n[5/5] Creating HNSW index...")
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {
        "M": 16,        # Number of bi-directional links
        "efConstruction": 200  # Search depth during construction
    }
}

collection.create_index(field_name="vector", index_params=index_params)
print("✅ HNSW index created")

# Load collection to memory
print("\n[6/6] Loading collection to memory...")
collection.load()
print("✅ Collection loaded and ready for search")

# Final stats
print("\n" + "=" * 60)
print("RE-INDEXING COMPLETE!")
print("=" * 60)
print(f"Collection: {COLLECTION_NAME}")
print(f"Total vectors: {total_inserted:,}")
print(f"Index type: HNSW")
print(f"Metric: COSINE")
print(f"Status: Ready for queries")
print("=" * 60)

# Disconnect
connections.disconnect("default")
print("\n✅ Disconnected from Milvus")
