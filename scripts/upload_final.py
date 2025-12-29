#!/usr/bin/env python3
"""Final OCR Upload - Using pre-cleaned data"""

import json
from pathlib import Path
from tqdm import tqdm
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

OCR_JSON = "/home/ir/ocr_results_cleaned_bytes.json"
SOURCE_COLL = "AIC_2024_TransNetV2"
TARGET_COLL = "AIC_2024_TransNetV2_OCR"
BATCH_SIZE = 1000

def main():
    print("="*70)
    print("FINAL OCR UPLOAD - Pre-cleaned Data")
    print("="*70)
    
    connections.connect(host="localhost", port=19530)
    print("✅ Connected")
    
    # Load pre-cleaned OCR
    print(f"\n📂 Loading {OCR_JSON}...")
    with open(OCR_JSON, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    ocr_lookup = {
        e['keyframe_path'].replace('.jpg', '').replace('.JPG', ''): e['ocr_text']
        for e in ocr_data
    }
    print(f"✅ Loaded {len(ocr_lookup):,} OCR entries")
    
    # Drop and create
    if utility.has_collection(TARGET_COLL):
        utility.drop_collection(TARGET_COLL)
        print(f"✅ Dropped old {TARGET_COLL}")
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="video", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="frame_id", dtype=DataType.INT64),
        FieldSchema(name="keyframe_path", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="time", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="ocr_text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="has_text", dtype=DataType.BOOL)
    ]
    
    schema = CollectionSchema(fields=fields)
    target = Collection(name=TARGET_COLL, schema=schema)
    print(f"✅ Created {TARGET_COLL}")
    
    # Load source
    source = Collection(SOURCE_COLL)
    source.load()
    total = source.num_entities
    print(f"\n📊 Source: {total:,} entities\n")
    
    # Process
    uploaded = 0
    last_id = -1
    
    with tqdm(total=total, desc="Uploading", unit="frame") as pbar:
        while True:
            results = source.query(
                expr=f"id > {last_id}",
                output_fields=["id", "vector", "video", "video_id", "frame_id", "keyframe_path", "time"],
                limit=BATCH_SIZE
            )
            
            if not results:
                break
            
            # Prepare batch
            vectors, videos, video_ids, frame_ids = [], [], [], []
            paths, times, ocr_texts, has_texts = [], [], [], []
            
            for r in results:
                path = r.get('keyframe_path', '')
                key = path.replace('.jpg', '').replace('.JPG', '')
                ocr_text = ocr_lookup.get(key, '')
                
                vectors.append(r['vector'])
                videos.append(r.get('video', ''))
                video_ids.append(r.get('video_id', ''))
                frame_ids.append(r.get('frame_id', 0))
                paths.append(path)
                times.append(r.get('time', ''))
                ocr_texts.append(ocr_text)
                has_texts.append(len(ocr_text) > 0)
                
                last_id = r['id']
            
            # Insert
            target.insert([vectors, videos, video_ids, frame_ids, paths, times, ocr_texts, has_texts])
            target.flush()
            
            uploaded += len(vectors)
            pbar.update(len(vectors))
            
            if len(results) < BATCH_SIZE:
                break
    
    print(f"\n✅ Uploaded {uploaded:,} entities")
    
    # Build index
    print("\n🔧 Building index...")
    target.create_index(
        field_name="vector",
        index_params={
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 32, "efConstruction": 512}
        }
    )
    print("✅ Index built")
    
    target.load()
    print(f"✅ Collection loaded: {target.num_entities:,} entities\n")
    
    print("="*70)
    print("✅ UPLOAD COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    main()
