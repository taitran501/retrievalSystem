"""
Direct test to understand exactly what query_milvus returns
Bypass the backend and call the method directly
"""
import sys
import asyncio
import torch
import torch.nn.functional as F
import open_clip

# Add backend to path
sys.path.insert(0, 'c:/Users/trant/Documents/retrieval_system/retrievalSystem/backend')

from main import VectorSearchService, Config

async def test_direct():
    print("=" * 60)
    print("DIRECT TEST OF VectorSearchService.query_milvus()")
    print("=" * 60)
    
    # Initialize service (same as backend)
    config = Config('config.json')
    service = VectorSearchService(config)
    
    # Encode a simple query
    query = "person"
    print(f"\n1. Encoding query: '{query}'")
    query_vector = service.encode_clip_text(query)
    print(f"   Vector shape: {query_vector.shape}")
    
    # Call query_milvus directly
    print(f"\n2. Calling query_milvus()...")
    results = await service.query_milvus(query_vector, limit=10)
    
    print(f"\n3. Results:")
    print(f"   Type: {type(results)}")
    print(f"   Length: {len(results)}")
    
    if results:
        print(f"\n   ✓ Got {len(results)} results!")
        print(f"\n   First result:")
        first = results[0]
        print(f"     Type: {type(first)}")
        print(f"     Has entity: {hasattr(first, 'entity')}")
        if hasattr(first, 'entity'):
            entity = first.entity
            print(f"     Video: {entity.get('video', 'N/A')}")
            print(f"     Path: {entity.get('path', 'N/A')}")
            print(f"     Frame ID: {entity.get('frame_id', 'N/A')}")
    else:
        print(f"   ✗ No results returned!")

if __name__ == "__main__":
    asyncio.run(test_direct())
