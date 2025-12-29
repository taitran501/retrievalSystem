#!/usr/bin/env python3
"""
Upload Combined Collection: OCR + RAM Tags
Creates AIC_2024_TransNetV2_Full with both text features
"""

import json
from pathlib import Path
from tqdm import tqdm
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# Configuration
OCR_JSON = "/home/ir/ocr_results_cleaned_bytes.json"
RAM_JSON = "/home/ir/ram_results_cleaned.json"
SOURCE_COLL = "AIC_2024_TransNetV2"
TARGET_COLL = "AIC_2024_TransNetV2_Full"
BATCH_SIZE = 1000

def main():
    print("="*70)
    print("COMBINED UPLOAD: OCR + RAM Tags")
    print("="*70)
    
    connections.connect(host="localhost", port=19530)
    print("✅ Connected to Milvus")
    
    # Load OCR data
    print(f"\n📂 Loading OCR data: {OCR_JSON}")
    with open(OCR_JSON, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    ocr_lookup = {
        e['keyframe_path'].replace('.jpg', '').replace('.JPG', ''): e['ocr_text']
        for e in ocr_data
    }
    print(f"✅ Loaded {len(ocr_lookup):,} OCR entries")
    
    # Load RAM tags
    print(f"\n📂 Loading RAM tags: {RAM_JSON}")
    with open(RAM_JSON, 'r', encoding='utf-8') as f:
        ram_data = json.load(f)
    
    ram_lookup = {
        e['keyframe_path']: e['ram_tags']
        for e in ram_data
    }
    print(f"✅ Loaded {len(ram_lookup):,} RAM tag entries")
    print(f"   Average tags per frame: {sum(e['cleaned_tag_count'] for e in ram_data)/len(ram_data):.1f}")
    
    # Create new collection
    if utility.has_collection(TARGET_COLL):
        print(f"\n⚠️  Collection {TARGET_COLL} already exists")
        response = input("Drop and recreate? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Aborted")
            return
        utility.drop_collection(TARGET_COLL)
        print(f"✅ Dropped old {TARGET_COLL}")
    
    # Define schema with OCR + RAM fields
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="video", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="frame_id", dtype=DataType.INT64),
        FieldSchema(name="keyframe_path", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="time", dtype=DataType.VARCHAR, max_length=20),
        # OCR fields
        FieldSchema(name="ocr_text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="has_text", dtype=DataType.BOOL),
        # RAM tag fields
        FieldSchema(name="ram_tags", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="has_ram_tags", dtype=DataType.BOOL)
    ]
    
    schema = CollectionSchema(fields=fields, description="Combined collection with OCR and RAM tags")
    target = Collection(name=TARGET_COLL, schema=schema)
    print(f"✅ Created collection: {TARGET_COLL}")
    print(f"   Schema: 11 fields (7 original + 2 OCR + 2 RAM)")
    
    # Load source collection
    source = Collection(SOURCE_COLL)
    source.load()
    total = source.num_entities
    print(f"\n📊 Source collection: {total:,} entities")
    print(f"   OCR coverage: {len(ocr_lookup):,} ({100*len(ocr_lookup)/total:.1f}%)")
    print(f"   RAM coverage: {len(ram_lookup):,} ({100*len(ram_lookup)/total:.1f}%)")
    
    # Upload in batches
    uploaded = 0
    last_id = -1
    ocr_matched = 0
    ram_matched = 0
    both_matched = 0
    
    print(f"\n🚀 Starting upload (batch size: {BATCH_SIZE})")
    print("="*70)
    
    with tqdm(total=total, desc="Uploading", unit="frame") as pbar:
        while True:
            # Query source collection
            results = source.query(
                expr=f"id > {last_id}",
                output_fields=["id", "vector", "video", "video_id", "frame_id", "keyframe_path", "time"],
                limit=BATCH_SIZE
            )
            
            if not results:
                break
            
            # Prepare batch data
            vectors, videos, video_ids, frame_ids = [], [], [], []
            paths, times = [], []
            ocr_texts, has_texts = [], []
            ram_tags_list, has_ram_tags_list = [], []
            
            for r in results:
                # Original fields
                vectors.append(r['vector'])
                videos.append(r['video'])
                video_ids.append(r['video_id'])
                frame_ids.append(r['frame_id'])
                paths.append(r['keyframe_path'])
                times.append(r['time'])
                
                # Normalize path for lookup
                path = r.get('keyframe_path', '')
                key = path.replace('.jpg', '').replace('.JPG', '')
                
                # Join OCR data
                ocr_text = ocr_lookup.get(key, '')
                ocr_texts.append(ocr_text)
                has_text = bool(ocr_text)
                has_texts.append(has_text)
                if has_text:
                    ocr_matched += 1
                
                # Join RAM tags
                ram_tags = ram_lookup.get(key, '')
                ram_tags_list.append(ram_tags)
                has_ram = bool(ram_tags)
                has_ram_tags_list.append(has_ram)
                if has_ram:
                    ram_matched += 1
                
                # Track frames with both
                if has_text and has_ram:
                    both_matched += 1
                
                last_id = r['id']
            
            # Insert batch
            data = [
                vectors, videos, video_ids, frame_ids, paths, times,
                ocr_texts, has_texts, ram_tags_list, has_ram_tags_list
            ]
            
            target.insert(data)
            uploaded += len(results)
            pbar.update(len(results))
    
    # Build index
    print("\n🔨 Building HNSW index on vector field...")
    index_params = {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 16, "efConstruction": 256}
    }
    target.create_index(field_name="vector", index_params=index_params)
    target.load()
    print("✅ Index built and collection loaded")
    
    # Summary
    print("\n" + "="*70)
    print("UPLOAD COMPLETE")
    print("="*70)
    print(f"Total entities uploaded: {uploaded:,}")
    print(f"OCR text matches: {ocr_matched:,} ({100*ocr_matched/uploaded:.1f}%)")
    print(f"RAM tags matches: {ram_matched:,} ({100*ram_matched/uploaded:.1f}%)")
    print(f"Both OCR + RAM: {both_matched:,} ({100*both_matched/uploaded:.1f}%)")
    print(f"Collection: {TARGET_COLL}")
    print("="*70)


if __name__ == '__main__':
    main()
