"""
Test to see what format results are actually in
"""
import sys
import asyncio

sys.path.insert(0, 'c:/Users/trant/Documents/retrieval_system/retrievalSystem/backend')

from main import VectorSearchService, Config

async def test_result_format():
    print("=" * 60)
    print("TESTING RESULT FORMAT")
    print("=" * 60)
    
    config = Config('config.json')
    service = VectorSearchService(config)
    
    query = "person"
    print(f"\n1. Encoding and querying...")
    query_vector = service.encode_clip_text(query)
    results = await service.query_milvus(query_vector, limit=3)
    
    print(f"\n2. Results format:")
    print(f"   Length: {len(results)}")
    
    if results:
        first = results[0]
        print(f"\n3. First result:")
        print(f"   Type: {type(first)}")
        print(f"   Is dict: {isinstance(first, dict)}")
        print(f"   Has .entity: {hasattr(first, 'entity')}")
        print(f"   Has .get: {hasattr(first, 'get')}")
        
        # Test .get() method
        try:
            entity_via_get = first.get('entity', {})
            print(f"   ✓ result.get('entity') works: {type(entity_via_get)}")
            print(f"     Video via .get: {entity_via_get.get('video', 'N/A') if hasattr(entity_via_get, 'get') else 'NO GET METHOD'}")
        except Exception as e:
            print(f"   ✗ result.get('entity') FAILED: {e}")
        
        # Test .entity attribute
        if hasattr(first, 'entity'):
            try:
                entity_via_attr = first.entity
                print(f"   ✓ result.entity works: {type(entity_via_attr)}")
                print(f"     Has .get: {hasattr(entity_via_attr, 'get')}")
                if hasattr(entity_via_attr, 'get'):
                    print(f"     Video via entity.get: {entity_via_attr.get('video', 'N/A')}")
                elif hasattr(entity_via_attr, '__getitem__'):
                    print(f"     Video via entity['video']: {entity_via_attr['video']}")
            except Exception as e:
                print(f"   ✗ result.entity access FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_result_format())
