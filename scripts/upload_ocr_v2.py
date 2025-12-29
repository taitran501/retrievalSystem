#!/usr/bin/env python3
"""OCR Upload V2 - With aggressive truncation and debugging"""

import json
from pathlib import Path
from tqdm import tqdm
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# Config
OCR_JSON = Path("/home/ir/ocr_results_all.json")
SOURCE_COLL = "AIC_2024_TransNetV2"
TARGET_COLL = "AIC_2024_TransNetV2_OCR"
BATCH_SIZE = 1000
MAX_OCR_LEN = 1900  # Safety margin below 2000

def main():
    print("="*70)
    print("OCR UPLOADER V2 - Aggressive Truncation")
    print("="*70)
    
    # Connect
    connections.connect(host="localhost", port=19530)
    print("✅ Connected")
    
    # Load OCR with strict truncation
    print(f"\n📂 Loading {OCR_JSON}...")
    with open(OCR_JSON, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    ocr_lookup = {}
    truncated_count = 0
    for entry in ocr_data:
        path = entry['keyframe_path'].replace('.jpg', '').replace('.JPG', '')
        text = entry.get('ocr_text', '').strip()
        
        # STRICT truncation
        if len(text) > MAX_OCR_LEN:
            truncated_count += 1
            text = text[:MAX_OCR_LEN]
        
        ocr_lookup[path] = text
    
    print(f"✅ Loaded {len(ocr_lookup):,} OCR entries ({truncated_count} truncated)")
    
    # Verify no long texts
    max_len = max(len(v) for v in ocr_lookup.values())
    print(f"📏 Max OCR text length: {max_len} chars (limit: {MAX_OCR_LEN})")
    
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
    
    # Process with safety checks
    uploaded = 0
    last_id = -1
    errors = []
    
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
                errors.append(f"Query error: {e}")
                break
            
            if not results:
                break
            
            # Prepare batch with triple-check truncation
            vectors, videos, video_ids, frame_ids = [], [], [], []
            paths, times, ocr_texts, has_texts = [], [], [], []
            
            for r in results:
                path = r.get('keyframe_path', '')
                key = path.replace('.jpg', '').replace('.JPG', '')
                ocr_text = ocr_lookup.get(key, '')
                
                # TRIPLE-CHECK: Force truncation even if lookup should have done it
                if len(ocr_text) > MAX_OCR_LEN:
                    errors.append(f"Unexpected long text at {path}: {len(ocr_text)} chars")
                    ocr_text = ocr_text[:MAX_OCR_LEN]
                
                vectors.append(r['vector'])
                videos.append(r.get('video', ''))
                video_ids.append(r.get('video_id', ''))
                frame_ids.append(r.get('frame_id', 0))
                paths.append(path)
                times.append(r.get('time', ''))
                ocr_texts.append(ocr_text)
                has_texts.append(len(ocr_text) > 0)
                
                last_id = r['id']
            
            # Final sanity check before insert
            bad_texts = [(i, len(t)) for i, t in enumerate(ocr_texts) if len(t) > 2000]
            if bad_texts:
                errors.append(f"Batch {uploaded//BATCH_SIZE} has {len(bad_texts)} texts > 2000 chars: {bad_texts[:3]}")
                print(f"⚠️ DEBUG: Found bad texts in batch {uploaded//BATCH_SIZE}: {bad_texts}")
                # Force truncate them
                ocr_texts = [t[:MAX_OCR_LEN] if len(t) > MAX_OCR_LEN else t for t in ocr_texts]
            
            # Debug: Log max length before insert
            max_ocr_len_in_batch = max(len(t) for t in ocr_texts) if ocr_texts else 0
            if uploaded // BATCH_SIZE == 27:  # Batch where it fails
                print(f"🔍 DEBUG Batch 27: max_ocr_len = {max_ocr_len_in_batch}, items = {len(ocr_texts)}")
                if max_ocr_len_in_batch > 1900:
                    print(f"   ⚠️ Found text > 1900! Lengths: {sorted([len(t) for t in ocr_texts if len(t) > 1900], reverse=True)[:5]}")
            
            # Insert batch
            try:
                target.insert([vectors, videos, video_ids, frame_ids, paths, times, ocr_texts, has_texts])
                target.flush()
            except Exception as e:
                errors.append(f"Insert error at batch {uploaded//BATCH_SIZE}: {e}")
                print(f"❌ INSERT ERROR at batch {uploaded//BATCH_SIZE}: {e}")
                print(f"   Max OCR length in failed batch: {max_ocr_len_in_batch}")
                print(f"   All OCR lengths > 1900: {[len(t) for t in ocr_texts if len(t) > 1900]}")
                break
            
            uploaded += len(vectors)
            pbar.update(len(vectors))
            
            if len(results) < BATCH_SIZE:
                break
    
    print(f"\n✅ Uploaded {uploaded:,} entities")
    
    if errors:
        print(f"\n⚠️ Encountered {len(errors)} warnings/errors:")
        for err in errors[:5]:
            print(f"  - {err}")
    
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
