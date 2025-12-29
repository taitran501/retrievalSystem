#!/usr/bin/env python3
"""
Model Verification Script
Verify that Milvus collection dimension matches backend CLIP model
"""

import json
import sys
from pathlib import Path

def check_model_consistency():
    """Verify model and collection dimension consistency"""
    
    print("="*70)
    print("  MODEL CONSISTENCY VERIFICATION")
    print("="*70)
    
    # 1. Check backend config
    print("\n[Step 1] Checking backend configuration...")
    config_path = Path("/home/ir/retrievalBaseline/backend/config.json")
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    model_name = config.get('clip_model_name', 'Unknown')
    collection_name = config.get('collection_name', 'Unknown')
    
    print(f"   Model:      {model_name}")
    print(f"   Collection: {collection_name}")
    
    # 2. Determine expected dimension
    print("\n[Step 2] Determining expected embedding dimension...")
    
    model_dimensions = {
        'ViT-B-16': 512,
        'ViT-B-32': 512,
        'ViT-L-14': 768,
        'ViT-L-14-336': 768,
        'ViT-H-14': 1024,
        'ViT-H-14-378-quickgelu': 1024,
        'ViT-g-14': 1024,
    }
    
    expected_dim = model_dimensions.get(model_name, None)
    
    if expected_dim is None:
        print(f"⚠️  Unknown model: {model_name}")
        print("   Common dimensions:")
        for model, dim in model_dimensions.items():
            print(f"     - {model}: {dim}")
        expected_dim = 768  # Default guess
    else:
        print(f"   Expected dimension: {expected_dim}")
    
    # 3. Test CLIP encoding
    print("\n[Step 3] Testing CLIP encoding output...")
    try:
        import torch
        import open_clip
        
        print(f"   Loading model: {model_name}...")
        
        # Try to load the model
        try:
            model, _, preprocess = open_clip.create_model_and_transforms(
                model_name,
                pretrained=config.get('clip_pretrained', 'openai')
            )
        except Exception as e:
            print(f"   ⚠️  Cannot load model: {e}")
            print("   This may indicate model name mismatch")
            return False
        
        # Test encode
        text = open_clip.tokenize(["test query"])
        with torch.no_grad():
            text_features = model.encode_text(text)
        
        actual_dim = text_features.shape[1]
        print(f"   Actual output dimension: {actual_dim}")
        
        if actual_dim == expected_dim:
            print(f"   ✅ Dimension matches expected: {actual_dim}")
        else:
            print(f"   ❌ MISMATCH! Expected {expected_dim} but got {actual_dim}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing CLIP: {e}")
        return False
    
    # 4. Check Milvus collection schema
    print("\n[Step 4] Checking Milvus collection schema...")
    try:
        from pymilvus import MilvusClient, Collection, connections
        
        # Get Milvus host from config (default to localhost, but also try 192.168.20.156)
        milvus_host = config.get('milvus_host', '127.0.0.1')
        milvus_port = config.get('milvus_port', 19530)
        
        print(f"   Connecting to Milvus at {milvus_host}:{milvus_port}...")
        
        # Connect
        client = MilvusClient(
            uri=f"http://{milvus_host}:{milvus_port}",
            db=config.get('milvus_database', 'default')
        )
        
        # Check collection exists
        collections = client.list_collections()
        if collection_name not in collections:
            print(f"   ❌ Collection '{collection_name}' not found in Milvus")
            print(f"   Available collections: {collections}")
            return False
        
        print(f"   ✅ Collection '{collection_name}' exists")
        
        # Get schema using pymilvus directly
        connections.connect(
            host=config.get('milvus_host', '127.0.0.1'),
            port=config.get('milvus_port', 19530)
        )
        
        collection = Collection(collection_name)
        schema = collection.schema
        
        # Find vector field
        vector_field = None
        for field in schema.fields:
            if field.dtype in [101]:  # FLOAT_VECTOR
                vector_field = field
                break
        
        if vector_field is None:
            print("   ❌ No vector field found in collection schema")
            return False
        
        milvus_dim = vector_field.params.get('dim', 0)
        print(f"   Vector field: {vector_field.name}")
        print(f"   Milvus dimension: {milvus_dim}")
        
        # 5. Final comparison
        print("\n[Step 5] Final verification...")
        print(f"   Backend model output:  {actual_dim}")
        print(f"   Milvus collection dim: {milvus_dim}")
        
        if actual_dim == milvus_dim:
            print(f"\n   ✅ ✅ ✅ PERFECT MATCH! ({actual_dim} = {milvus_dim})")
            print("\n   Your system is correctly configured.")
            return True
        else:
            print(f"\n   ❌ ❌ ❌ CRITICAL MISMATCH!")
            print(f"\n   Backend outputs {actual_dim}-dimensional vectors")
            print(f"   But Milvus expects {milvus_dim}-dimensional vectors")
            print("\n   This means search results are RANDOM/MEANINGLESS!")
            print("\n   To fix:")
            print(f"   Option 1: Change backend model to output {milvus_dim} dimensions")
            print(f"   Option 2: Re-index Milvus collection with {actual_dim} dimensions")
            return False
        
    except Exception as e:
        print(f"   ❌ Error checking Milvus: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = check_model_consistency()
    
    print("\n" + "="*70)
    if success:
        print("✅ MODEL VERIFICATION PASSED")
        print("\nYour system is correctly configured.")
        print("You can proceed with building new features.")
        sys.exit(0)
    else:
        print("❌ MODEL VERIFICATION FAILED")
        print("\n⚠️  CRITICAL: Fix this before doing anything else!")
        print("Search results are likely incorrect due to dimension mismatch.")
        sys.exit(1)

if __name__ == "__main__":
    main()
