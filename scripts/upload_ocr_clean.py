#!/usr/bin/env python3
"""Simple OCR Upload - Clean version"""

import json
from pathlib import Path
from tqdm import tqdm
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# Config
OCR_JSON = Path("/home/ir/ocr_results_all.json")
SOURCE_COLL = "AIC_2024_TransNetV2"
TARGET_COLL = "AIC_2024_TransNetV2_OCR"
BATCH_SIZE = 1000

def main():
    print("="*70)
    print("OCR UPLOADER - Clean Version")
    print("="*70)
    
    # Connect
    connections.connect(host="localhost", port=19530)
    print("✅ Connected")
    
    # Load OCR
    print(f"\n📂 Loading {OCR_JSON}...")
    with open(OCR_JSON, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    ocr_lookup = {}
    for entry in ocr_data:
        path = entry['keyframe_path'].replace('.jpg', '').replace('.JPG', '')
        text = entry.get('ocr_text', '').strip()
        # Truncate to 1900 chars
        if len(text) > 1900:
            text = text[:1900]
        ocr_lookup[path] = text
    
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
    print(f"\n📊 Source: {total:,} entities")
    
    # Process
    uploaded = 0
    last_id = -1
    
    with tqdm(total=total, desc="Uploading") as pbar:
        while True:
            # Query by ID
            try:
                results = source.query(
                    expr=f"id > {last_id}",
                    output_fields=["id", "vector", "video", "video_id", "frame_id", "keyframe_path", "time"],
                    limit=BATCH_SIZE
                )
            except Exception as e:
                print(f"\n❌ Error: {e}")
                break
            
            if not results:
                break
            
            # Prepare batch
            vectors, videos, video_ids, frame_ids = [], [], [], []
            paths, times, ocr_texts, has_texts = [], [], [], []
            
            for r in results:
                path = r.get('keyframe_path', '')
                key = path.replace('.jpg', '').replace('.JPG', '')
                ocr_text = ocr_lookup.get(key, '')
                
                # Double-check truncation
                if len(ocr_text) > 1900:
                    ocr_text = ocr_text[:1900]
                
                vectors.append(r['vector'])
                videos.append(r.get('video', ''))
                video_ids.append(r.get('video_id', ''))
                frame_ids.append(r.get('frame_id', 0))
                paths.append(path)
                times.append(r.get('time', ''))
                ocr_texts.append(ocr_text)
                has_texts.append(len(ocr_text) > 0)
                
                last_id = r['id']
            
            # Insert batch
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
    print(f"✅ Loaded: {target.num_entities:,} entities")
    
    print("\n" + "="*70)
    print("✅ COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
