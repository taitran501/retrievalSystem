"""
Complete end-to-end test simulating the /TextQuery endpoint
This will tell us EXACTLY where results are lost
"""
import sys
import asyncio
import json

sys.path.insert(0, 'c:/Users/trant/Documents/retrieval_system/retrievalSystem/backend')

from main import VectorSearchService, Config

async def test_full_pipeline():
    print("=" * 60)
    print("FULL PIPELINE TEST - Simulating /TextQuery endpoint")
    print("=" * 60)
    
    # Initialize exactly as backend does
    config = Config('config.json')
    service = VectorSearchService(config)
    
    # Simulate the exact request
    query = "person"
    top_k = 5
    
    print(f"\nInput: query='{query}', top_k={top_k}")
    print(f"Config diversity filter enabled: {getattr(config, 'enable_diversity_filter', False)}")
    print(f"Config diversity_max_results: {getattr(config, 'diversity_max_results', 'N/A')}")
    
    # Call process_temporal_query (same as /TextQuery endpoint)
    print(f"\nCalling process_temporal_query()...")
    result = await service.process_temporal_query(
        first_query=query,
        second_query="",
        top_k=top_k
    )
    
    print(f"\n{'='*60}")
    print(f"RESULT:")
    print(f"  Type: {type(result)}")
    print(f"  Length: {len(result)}")
    
    if result:
        print(f"\n  ✓ SUCCESS - Got {len(result)} results!")
        print(f"\n  First result:")
        first = result[0]
        print(f"    Type: {type(first)}")
        if isinstance(first, dict):
            entity = first.get('entity', {})
            print(f"    Video: {entity.get('video', 'N/A')}")
            print(f"    Path: {entity.get('path', 'N/A')}")
    else:
        print(f"\n  ✗ FAILURE - Empty results!")
        print(f"\n  This means the bug is in process_temporal_query() or its filters")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
