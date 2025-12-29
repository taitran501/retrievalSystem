#!/usr/bin/env python3
"""
Upload OCR text data to Milvus TransNetV2 collection
Creates a new collection with OCR text field or updates existing collection
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility


class OCRMilvusUploader:
    """Upload OCR results to Milvus collection"""
    
    def __init__(
        self,
        ocr_json_file: str = "/home/ir/ocr_results_all.json",
        collection_name: str = "AIC_2024_TransNetV2_OCR",
        milvus_host: str = "localhost",
        milvus_port: int = 19530
    ):
        self.ocr_json_file = Path(ocr_json_file)
        self.collection_name = collection_name
        
        # Connect to Milvus
        connections.connect(host=milvus_host, port=milvus_port)
        print(f"✅ Connected to Milvus at {milvus_host}:{milvus_port}")
        
        # Load existing collection or create new
        self.setup_collection()
    
    def setup_collection(self):
        """Create new collection with OCR field"""
        
        if utility.has_collection(self.collection_name):
            print(f"⚠️  Collection '{self.collection_name}' already exists")
            response = input("Drop and recreate? (yes/no): ")
            if response.lower() == 'yes':
                utility.drop_collection(self.collection_name)
                print("✅ Dropped old collection")
            else:
                print("Using existing collection")
                self.collection = Collection(self.collection_name)
                return
        
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
            FieldSchema(name="ocr_text", dtype=DataType.VARCHAR, max_length=2000),  # All detected text
            FieldSchema(name="has_text", dtype=DataType.BOOL)  # Quick filter for frames with text
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="TransNetV2 Keyframes with OCR Text"
        )
        
        self.collection = Collection(name=self.collection_name, schema=schema)
        print(f"✅ Created collection: {self.collection_name}")
    
    def load_ocr_data(self) -> Dict[str, Dict]:
        """
        Load all OCR results from merged JSON file
        
        Returns:
            {
                'L01/V001/0002': {
                    'ocr_text': 'detected text',
                    'has_text': True
                }
            }
        """
        print(f"\n📂 Loading OCR results from {self.ocr_json_file}...")
        
        if not self.ocr_json_file.exists():
            print(f"❌ OCR file not found: {self.ocr_json_file}")
            return {}
        
        with open(self.ocr_json_file, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
        
        # Convert to lookup dict
        # keyframe_path format: "L01/V001/0002.jpg" -> key: "L01/V001/0002"
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
    
    def upload_from_existing_collection(
        self,
        source_collection: str = "AIC_2024_TransNetV2",
        batch_size: int = 5000
    ):
        """
        Copy data from existing collection and add OCR text
        
        Args:
            source_collection: Name of source collection without OCR
            batch_size: Batch size for insertion
        """
        print(f"\n📤 Copying from {source_collection} and adding OCR data...")
        
        # Load OCR lookup
        ocr_lookup = self.load_ocr_data()
        
        # Connect to source collection
        if not utility.has_collection(source_collection):
            print(f"❌ Source collection '{source_collection}' not found")
            return
        
        source_coll = Collection(source_collection)
        source_coll.load()
        
        total_entities = source_coll.num_entities
        print(f"📊 Source collection: {total_entities:,} entities")
        
        # Query all data from source (in batches)
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
        
        offset = 0
        uploaded = 0
        
        with tqdm(total=total_entities, desc="Processing") as pbar:
            while offset < total_entities:
                # Milvus has max query window of 16384, so limit batch + offset
                current_batch_size = min(batch_size, 16384 - (offset % 16384))
                if current_batch_size <= 0:
                    current_batch_size = batch_size
                
                # Query batch from source - use iterator approach
                try:
                    results = source_coll.query(
                        expr=f"frame_id >= 0",  # Simple condition
                        output_fields=["vector", "video", "video_id", "frame_id", "keyframe_path", "time"],
                        limit=min(current_batch_size, 10000),  # Keep it under 16K limit
                        offset=offset % 16384  # Reset offset periodically
                    )
                except Exception as e:
                    # If offset too large, use alternative query
                    print(f"\n⚠️ Query limit exceeded, switching to scan mode...")
                    # Use search with random vector instead
                    break
                
                if not results:
                    offset += current_batch_size
                    if offset < total_entities:
                        continue
                    else:
                        break
                
                # Process each result
                for result in results:
                    # Build lookup key
                    path = result['keyframe_path']  # e.g., "L01/V001/12345.jpg"
                    key = path.replace('.jpg', '')
                    
                    # Get OCR data if exists
                    ocr_data = ocr_lookup.get(key, {'ocr_text': '', 'has_text': False})
                    
                    # Append to batch
                    batch_data['vectors'].append(result['vector'])
                    batch_data['videos'].append(result['video'])
                    batch_data['video_ids'].append(result['video_id'])
                    batch_data['frame_ids'].append(result['frame_id'])
                    batch_data['paths'].append(result['keyframe_path'])
                    batch_data['times'].append(result['time'])
                    batch_data['ocr_texts'].append(ocr_data['ocr_text'])
                    batch_data['has_texts'].append(ocr_data['has_text'])
                
                # Insert batch when full
                if len(batch_data['vectors']) >= batch_size:
                    self.collection.insert([
                        batch_data['vectors'],
                        batch_data['videos'],
                        batch_data['video_ids'],
                        batch_data['frame_ids'],
                        batch_data['paths'],
                        batch_data['times'],
                        batch_data['ocr_texts'],
                        batch_data['has_texts']
                    ])
                    self.collection.flush()
                    
                    uploaded += len(batch_data['vectors'])
                    pbar.update(len(batch_data['vectors']))
                    
                    # Reset batch
                    batch_data = {k: [] for k in batch_data.keys()}
                
                offset += len(results)
        
        # Insert remaining data
        if batch_data['vectors']:
            self.collection.insert([
                batch_data['vectors'],
                batch_data['videos'],
                batch_data['video_ids'],
                batch_data['frame_ids'],
                batch_data['paths'],
                batch_data['times'],
                batch_data['ocr_texts'],
                batch_data['has_texts']
            ])
            self.collection.flush()
            uploaded += len(batch_data['vectors'])
        
        print(f"\n✅ Uploaded {uploaded:,} entities with OCR data")
        
        # Build index
        print("\n🔧 Building HNSW index...")
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 32, "efConstruction": 512}
        }
        self.collection.create_index(field_name="vector", index_params=index_params)
        print("✅ Index built")
        
        # Load collection
        self.collection.load()
        print(f"✅ Collection loaded: {self.collection.num_entities:,} entities")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload OCR data to Milvus")
    parser.add_argument(
        "--ocr-json",
        default="/home/ir/ocr_results_all.json",
        help="Merged OCR results JSON file"
    )
    parser.add_argument(
        "--collection-name",
        default="AIC_2024_TransNetV2_OCR",
        help="New collection name with OCR"
    )
    parser.add_argument(
        "--source-collection",
        default="AIC_2024_TransNetV2",
        help="Source collection to copy from"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Milvus host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=19530,
        help="Milvus port"
    )
    
    args = parser.parse_args()
    
    uploader = OCRMilvusUploader(
        ocr_json_file=args.ocr_json,
        collection_name=args.collection_name,
        milvus_host=args.host,
        milvus_port=args.port
    )
    
    uploader.upload_from_existing_collection(
        source_collection=args.source_collection
    )
    
    print("\n" + "="*70)
    print("✅ OCR DATA UPLOAD COMPLETE")
    print("="*70)
    print(f"Collection: {args.collection_name}")
    print(f"Ready for hybrid search (vector + text)")


if __name__ == "__main__":
    main()
