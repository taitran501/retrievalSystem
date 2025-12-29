#!/usr/bin/env python3
"""
Quick upload script for embeddings to Milvus
Uses existing embeddings in /home/ir/retrievalSystem/data/embeddings/
"""

import numpy as np
import pandas as pd
from pymilvus import MilvusClient, DataType
import os
from pathlib import Path
import time

# Paths
EMBEDDINGS_DIR = "/home/ir/retrievalSystem/data/embeddings"
MILVUS_URI = "http://127.0.0.1:19530"
COLLECTION_NAME = "AIC_2024_TransNetV2_Full"

def create_collection(client):
    """Create collection with schema"""
    print(f"Creating collection: {COLLECTION_NAME}")
    
    # Drop if exists
    if client.has_collection(COLLECTION_NAME):
        print(f"Collection {COLLECTION_NAME} exists, dropping...")
        client.drop_collection(COLLECTION_NAME)
    
    # Create collection with schema
    schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("frame_id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=768)
    schema.add_field("keyframe_path", DataType.VARCHAR, max_length=256)
    schema.add_field("video", DataType.VARCHAR, max_length=64)
    
    # Create collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=client.prepare_index_params()
    )
    
    # Add index
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 1024}
    )
    client.create_index(COLLECTION_NAME, index_params)
    print("Collection created successfully")

def upload_batch(client, batch_id, vectors_file, meta_file):
    """Upload one batch (L##) to Milvus"""
    print(f"\n{'='*60}")
    print(f"Uploading {batch_id}...")
    
    # Load data
    vectors = np.load(vectors_file)
    meta_df = pd.read_csv(meta_file)
    
    print(f"Loaded {len(vectors)} vectors, {len(meta_df)} metadata rows")
    
    # Prepare data
    data = []
    for idx, row in meta_df.iterrows():
        data.append({
            "frame_id": int(row['frame_id']),
            "vector": vectors[idx].tolist(),
            "keyframe_path": str(row['keyframe_path']),
            "video": str(row['video'])
        })
    
    # Insert in batches
    batch_size = 1000
    total_inserted = 0
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        client.insert(COLLECTION_NAME, batch)
        total_inserted += len(batch)
        if total_inserted % 10000 == 0:
            print(f"  Inserted {total_inserted}/{len(data)} rows...")
    
    print(f"✅ {batch_id}: Inserted {total_inserted} rows")
    return total_inserted

def main():
    print("="*60)
    print("MILVUS COLLECTION UPLOAD")
    print("="*60)
    
    # Connect to Milvus
    print(f"\nConnecting to Milvus at {MILVUS_URI}...")
    client = MilvusClient(uri=MILVUS_URI)
    print("✅ Connected!")
    
    # Create collection
    create_collection(client)
    
    # Find all embedding files
    embedding_files = sorted(Path(EMBEDDINGS_DIR).glob("L*_vectors.npy"))
    print(f"\nFound {len(embedding_files)} batches to upload")
    
    total_count = 0
    start_time = time.time()
    
    # Upload each batch
    for vectors_file in embedding_files:
        batch_id = vectors_file.stem.replace("_vectors", "")
        meta_file = vectors_file.parent / f"{batch_id}_meta.csv"
        
        if not meta_file.exists():
            print(f"⚠️  Skipping {batch_id}: metadata file not found")
            continue
        
        count = upload_batch(client, batch_id, vectors_file, meta_file)
        total_count += count
    
    # Load collection
    client.load_collection(COLLECTION_NAME)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ UPLOAD COMPLETE!")
    print(f"Total vectors uploaded: {total_count:,}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
