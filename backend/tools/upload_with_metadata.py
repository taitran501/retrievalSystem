#!/usr/bin/env python3
"""Generate metadata from keyframes and upload to Milvus"""

import numpy as np
import pandas as pd
from pymilvus import MilvusClient, DataType
from pathlib import Path
import time

KEYFRAMES_DIR = r"c:\Users\trant\Documents\retrieval_system\retrievalSystem\data\keyframes"
EMBEDDINGS_DIR = r"c:\Users\trant\Documents\retrieval_system\retrievalSystem\data\embeddings"
MILVUS_URI = "http://127.0.0.1:19530"
COLLECTION_NAME = "AIC_2024_TransNetV2_Full"

def generate_metadata_for_batch(batch_id):
    """Generate metadata by scanning keyframes directory"""
    print(f"Generating metadata for {batch_id}...")
    
    batch_dir = Path(KEYFRAMES_DIR) / batch_id
    if not batch_dir.exists():
        return None
    
    metadata = []
    frame_id_counter = 0
    
    # Scan all videos in batch
    for video_dir in sorted(batch_dir.glob("V*")):
        video_name = f"{batch_id}_{video_dir.name}"  # e.g., "L19_V004"
        
        # Scan all frames in video
        for frame_file in sorted(video_dir.glob("*.jpg")):
            frame_num = frame_file.stem
            keyframe_path = f"{batch_id}/{video_dir.name}/{frame_num}.jpg"
            
            metadata.append({
                'frame_id': frame_id_counter,
                'keyframe_path': keyframe_path,
                'video': video_name
            })
            frame_id_counter += 1
    
    return pd.DataFrame(metadata)

def create_collection(client):
    """Create collection"""
    print("Creating collection...")
    if client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)
    
    schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("frame_id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=768)
    schema.add_field("keyframe_path", DataType.VARCHAR, max_length=256)
    schema.add_field("video", DataType.VARCHAR, max_length=64)
    
    client.create_collection(collection_name=COLLECTION_NAME, schema=schema)
    
    # Add index
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 1024}
    )
    client.create_index(COLLECTION_NAME, index_params)
    print("✅ Collection created")

def upload_batch(client, batch_id, vectors_file):
    """Upload batch with generated metadata"""
    print(f"\n{'='*60}")
    print(f"Processing {batch_id}...")
    
    # Generate metadata
    meta_df = generate_metadata_for_batch(batch_id)
    if meta_df is None:
        print(f"⚠️  No keyframes found for {batch_id}")
        return 0
    
    # Load vectors
    vectors = np.load(vectors_file)
    
    # Match counts
    if len(vectors) != len(meta_df):
        print(f"⚠️  Vector count ({len(vectors)}) != metadata count ({len(meta_df)})")
        print(f"   Using minimum: {min(len(vectors), len(meta_df))}")
        min_len = min(len(vectors), len(meta_df))
        vectors = vectors[:min_len]
        meta_df = meta_df.iloc[:min_len]
    
    print(f"Uploading {len(vectors)} vectors...")
    
    # Prepare data
    data = []
    for idx in range(len(meta_df)):
        data.append({
            "frame_id": int(meta_df.iloc[idx]['frame_id']),
            "vector": vectors[idx].tolist(),
            "keyframe_path": str(meta_df.iloc[idx]['keyframe_path']),
            "video": str(meta_df.iloc[idx]['video'])
        })
    
    # Insert in batches
    batch_size = 1000
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        client.insert(COLLECTION_NAME, batch)
        if (i+batch_size) % 10000 == 0:
            print(f"  Inserted {i+batch_size}/{len(data)}...")
    
    print(f"✅ {batch_id}: {len(data)} vectors uploaded")
    return len(data)

def main():
    print("="*60)
    print("MILVUS UPLOAD - WITH AUTO METADATA GENERATION")
    print("="*60)
    
    client = MilvusClient(uri=MILVUS_URI)
    print("✅ Connected to Milvus")
    
    create_collection(client)
    
    # Find vector files
    vector_files = sorted(Path(EMBEDDINGS_DIR).glob("L*_vectors.npy"))
    print(f"\nFound {len(vector_files)} batches")
    
    total = 0
    start = time.time()
    
    for vf in vector_files:
        batch_id = vf.stem.replace("_vectors", "")
        count = upload_batch(client, batch_id, vf)
        total += count
    
    client.load_collection(COLLECTION_NAME)
    
    print(f"\n{'='*60}")
    print(f"✅ COMPLETE!")
    print(f"Total: {total:,} vectors")
    print(f"Time: {time.time()-start:.1f}s")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
