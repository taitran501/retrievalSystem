"""
Test Vietnamese query translation and execution
"""
import sys
import asyncio

sys.path.insert(0, 'c:/Users/trant/Documents/retrieval_system/retrievalSystem/backend')

from main import VectorSearchService, Config

async def test_vn_pipeline():
    print("=" * 60)
    print("TESTING VIETNAMESE QUERY TRANSLATION")
    print("=" * 60)
    
    # Initialize service
    config = Config('config.json')
    service = VectorSearchService(config)
    
    # Test query: "người đàn ông mặc áo đỏ" (should translate to "man wearing red shirt")
    # This assumes "man wearing red shirt" exists in the database/CLIP space
    query = "người đàn ông mặc áo đỏ"
    print(f"\nInput Vietnamese query: '{query}'")
    
    # Run query
    print(f"\nCalling process_temporal_query()...")
    results = await service.process_temporal_query(
        first_query=query,
        top_k=5
    )
    
    print(f"\nResults: {len(results)}")
    if results:
        print("✓ SUCCESS: Got results")
        print(f"First result: {results[0].get('entity', {}).get('video_path')}")
    else:
        print("✗ FAILURE: No results")

if __name__ == "__main__":
    asyncio.run(test_vn_pipeline())
