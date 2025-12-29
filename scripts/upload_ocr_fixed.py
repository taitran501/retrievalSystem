#!/usr/bin/env python3
"""
Upload OCR text data to Milvus TransNetV2 collection - FIXED VERSION
Uses search-based iteration instead of query with offset
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm
import numpy as np

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility


def load_ocr_data(json_file: Path) -> Dict[str, Dict]:
    """Load OCR data from merged JSON file"""
    print(f"\n📂 Loading OCR results from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    # Convert to lookup dict: "L01/V001/0002" -> {"ocr_text": "...", "has_text": True}
    ocr_lookup = {}
    for entry in ocr_data:
        path = entry['keyframe_path']
        key = path.replace('.jpg', '').replace('.JPG', '')
        
        text = entry.get('ocr_text', '').strip()
        ocr_lookup[key] = {
            'ocr_text': text,
            'has_text': len(text) > 0
        }
    
    print(f"✅ Loaded OCR data for {len(ocr_lookup):,} frames")
    return ocr_lookup


def create_ocr_collection(collection_name: str):
    """Create new collection with OCR fields"""
    
    if utility.has_collection(collection_name):
        print(f"⚠️  Collection '{collection_name}' already exists")
        response = input("Drop and recreate? (yes/no): ")
        if response.lower() != 'yes':
            print("Exiting...")
            sys.exit(0)
        utility.drop_collection(collection_name)
        print("✅ Dropped old collection")
    
    # Define schema with OCR text field
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="video", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="frame_id", dtype=DataType.INT64),
        FieldSchema(name="keyframe_path", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="time", dtype=DataType.VARCHAR, max_length=20),
        # New OCR fields
        FieldSchema(name="ocr_text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="has_text", dtype=DataType.BOOL)
    ]
    
    schema = CollectionSchema(fields=fields, description="TransNetV2 Keyframes with OCR Text")
    collection = Collection(name=collection_name, schema=schema)
    print(f"✅ Created collection: {collection_name}")
    
    return collection


def upload_data(
    source_collection: str,
    target_collection: Collection,
    ocr_lookup: Dict,
    batch_size: int = 1000
):
    """Upload data from source to target with OCR"""
    
    print(f"\n📤 Copying from {source_collection} and adding OCR data...")
    
    # Load source collection
    source_coll = Collection(source_collection)
    source_coll.load()
    
    total_entities = source_coll.num_entities
    print(f"📊 Source collection: {total_entities:,} entities")
    
    # Use search-based iteration (no offset limit)
    # Get a random vector to start
    dummy_vector = np.random.rand(768).astype(np.float32).tolist()
    
    batch_data = {
        'vectors': [],
        'videos': [],
        'video_ids': [],
        'frame_ids': [],
        'paths': [],
        'times': [],
        'ocr_texts': [],
        'has_texts': []
    }
    
    uploaded = 0
    processed = 0
    
    with tqdm(total=total_entities, desc="Processing") as pbar:
        # Process in large batches
        search_limit = 16000  # Max Milvus allows
        
        while processed < total_entities:
            try:
                # Search to get next batch
                results = source_coll.search(
                    data=[dummy_vector],
                    anns_field="vector",
                    param={"metric_type": "COSINE", "params": {"nprobe": 1}},
                    limit=search_limit,
                    offset=processed,
                    output_fields=["vector", "video", "video_id", "frame_id", "keyframe_path", "time"]
                )
                
                if not results or not results[0]:
                    break
                
                # Process results
                for hit in results[0]:
                    entity = hit.entity
                    
                    # Build lookup key
                    path = entity.get('keyframe_path', '')
                    key = path.replace('.jpg', '')
                    
                    # Get OCR data
                    ocr_data = ocr_lookup.get(key, {'ocr_text': '', 'has_text': False})
                    
                    # Append to batch
                    batch_data['vectors'].append(entity.get('vector'))
                    batch_data['videos'].append(entity.get('video', ''))
                    batch_data['video_ids'].append(entity.get('video_id', ''))
                    batch_data['frame_ids'].append(entity.get('frame_id', 0))
                    batch_data['paths'].append(path)
                    batch_data['times'].append(entity.get('time', ''))
                    batch_data['ocr_texts'].append(ocr_data['ocr_text'])
                    batch_data['has_texts'].append(ocr_data['has_text'])
                    
                    # Insert batch when full
                    if len(batch_data['vectors']) >= batch_size:
                        target_collection.insert([
                            batch_data['vectors'],
                            batch_data['videos'],
                            batch_data['video_ids'],
                            batch_data['frame_ids'],
                            batch_data['paths'],
                            batch_data['times'],
                            batch_data['ocr_texts'],
                            batch_data['has_texts']
                        ])
                        target_collection.flush()
                        
                        uploaded += len(batch_data['vectors'])
                        pbar.update(len(batch_data['vectors']))
                        
                        # Reset batch
                        batch_data = {k: [] for k in batch_data.keys()}
                
                processed += len(results[0])
                
            except Exception as e:
                print(f"\n❌ Error at offset {processed}: {e}")
                break
    
    # Insert remaining data
    if batch_data['vectors']:
        target_collection.insert([
            batch_data['vectors'],
            batch_data['videos'],
            batch_data['video_ids'],
            batch_data['frame_ids'],
            batch_data['paths'],
            batch_data['times'],
            batch_data['ocr_texts'],
            batch_data['has_texts']
        ])
        target_collection.flush()
        uploaded += len(batch_data['vectors'])
    
    print(f"\n✅ Uploaded {uploaded:,} entities with OCR data")
    
    # Build index
    print("\n🔧 Building HNSW index...")
    index_params = {
        "metric_type": "COSINE",
        "index_type": "HNSW",
        "params": {"M": 32, "efConstruction": 512}
    }
    target_collection.create_index(field_name="vector", index_params=index_params)
    print("✅ Index built")
    
    # Load collection
    target_collection.load()
    print(f"✅ Collection loaded: {target_collection.num_entities:,} entities")


def main():
    print("="*70)
    print("OCR MILVUS UPLOADER - FIXED VERSION")
    print("="*70)
    
    # Configuration
    ocr_json_file = Path("/home/ir/ocr_results_all.json")
    source_collection = "AIC_2024_TransNetV2"
    target_collection_name = "AIC_2024_TransNetV2_OCR"
    milvus_host = "localhost"
    milvus_port = 19530
    
    # Connect to Milvus
    connections.connect(host=milvus_host, port=milvus_port)
    print(f"✅ Connected to Milvus at {milvus_host}:{milvus_port}")
    
    # Load OCR data
    ocr_lookup = load_ocr_data(ocr_json_file)
    
    # Create target collection
    target_coll = create_ocr_collection(target_collection_name)
    
    # Upload data
    upload_data(source_collection, target_coll, ocr_lookup, batch_size=1000)
    
    print("\n" + "="*70)
    print("✅ OCR DATA UPLOAD COMPLETE")
    print("="*70)
    print(f"Collection: {target_collection_name}")
    print(f"Ready for hybrid search (vector + text)")


if __name__ == "__main__":
    main()
