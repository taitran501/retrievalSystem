import os
import glob
import numpy as np
import pandas as pd
from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType
from tqdm import tqdm
import time

# Configuration
CONFIG = {
    "embeddings_dir": "c:/Users/trant/Documents/retrieval_system/retrievalSystem/data/embeddings_512",
    "collection_name": "AIC_2024_ViTB16",
    "dim": 512,
    "milvus_host": "localhost",
    "milvus_port": 19530,
    "batch_size": 5000  # Upload in chunks of 5000 records
}

def initialize_milvus():
    print(f"Connecting to Milvus at {CONFIG['milvus_host']}:{CONFIG['milvus_port']}...")
    connections.connect(host=CONFIG['milvus_host'], port=CONFIG['milvus_port'])
    
    if utility.has_collection(CONFIG['collection_name']):
        print(f"⚠️  Found existing collection '{CONFIG['collection_name']}'. Dropping it...")
        utility.drop_collection(CONFIG['collection_name'])
        
    print(f"Creating collection '{CONFIG['collection_name']}'...")
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=CONFIG['dim']),
        FieldSchema(name="video", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="frame_id", dtype=DataType.INT64),
        FieldSchema(name="keyframe_path", dtype=DataType.VARCHAR, max_length=200)
    ]
    schema = CollectionSchema(fields=fields, description="AIC 2024 ViT-B-16 (Pre-encoded)")
    collection = Collection(name=CONFIG['collection_name'], schema=schema)
    
    print(f"✅ Collection created.")
    return collection

def main():
    collection = initialize_milvus()
    
    # Find all pre-encoded files
    meta_files = sorted(glob.glob(os.path.join(CONFIG["embeddings_dir"], "*_meta.csv")))
    vector_files = sorted(glob.glob(os.path.join(CONFIG["embeddings_dir"], "*_vectors.npy")))
    
    if not meta_files:
        print(f"❌ ERROR: No .csv files found in {CONFIG['embeddings_dir']}")
        return

    print(f"📊 Found {len(meta_files)} batches to upload.")
    
    total_inserted = 0
    t_start = time.time()

    for meta_file, vector_file in zip(meta_files, vector_files):
        batch_id = os.path.basename(meta_file).split("_")[0]
        print(f"\n🚀 Uploading {batch_id}...")
        
        # Load data
        meta_df = pd.read_csv(meta_file)
        vectors = np.load(vector_file).astype(np.float32)
        
        if len(meta_df) != len(vectors):
            print(f"⚠️  WARNING: Mismatch in {batch_id}: {len(meta_df)} meta vs {len(vectors)} vectors. Skipping.")
            continue
            
        # Verify dimension
        if vectors.shape[1] != CONFIG["dim"]:
            print(f"❌ ERROR: Vector dimension mismatch! Found {vectors.shape[1]}, expected {CONFIG['dim']}")
            return

        # Insert in batches
        num_records = len(meta_df)
        for i in tqdm(range(0, num_records, CONFIG["batch_size"]), desc=f"Pushing {batch_id}"):
            end = min(i + CONFIG["batch_size"], num_records)
            
            # Prepare Milvus data format
            batch_vectors = [v.tolist() for v in vectors[i:end]]
            batch_videos = meta_df['video'].iloc[i:end].tolist()
            batch_frames = meta_df['frame_id'].iloc[i:end].astype(int).tolist()
            batch_keyframe_paths = meta_df['path'].iloc[i:end].tolist() # Map 'path' meta to 'keyframe_path' field
            
            data = [
                batch_vectors,
                batch_videos,
                batch_frames,
                batch_keyframe_paths
            ]
            
            collection.insert(data)
            total_inserted += (end - i)

    print(f"\n[Finishing] Creating HNSW Index (COSINE)...")
    index_params = {
        "metric_type": "COSINE",
        "index_type": "HNSW",
        "params": {"M": 16, "efConstruction": 200}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    
    print("Loading collection to memory...")
    collection.load()
    
    t_end = time.time()
    print("\n" + "=" * 60)
    print("✅ RE-INDEXING COMPLETE!")
    print("=" * 60)
    print(f"Total Vectors: {total_inserted:,}")
    print(f"Total Time: {t_end - t_start:.2f} seconds")
    print(f"Collection: {CONFIG['collection_name']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
