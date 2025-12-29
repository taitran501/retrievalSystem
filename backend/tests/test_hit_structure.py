"""
Debug test to understand the Hit object structure
"""
import sys
import asyncio

sys.path.insert(0, 'c:/Users/trant/Documents/retrieval_system/retrievalSystem/backend')

from main import VectorSearchService, Config

async def debug_hit_structure():
    print("=" * 60)
    print("DEBUG: Understanding Hit object structure")
    print("=" * 60)
    
    # Initialize service
    config = Config('config.json')
    service = VectorSearchService(config)
    
    # Encode query
    query = "person"
    query_vector = service.encode_clip_text(query)
    
    # Call query_milvus
    results = await service.query_milvus(query_vector, limit=5)
    
    print(f"\nGot {len(results)} results")
    
    if results:
        hit = results[0]
        print(f"\nFirst Hit object:")
        print(f"  Type: {type(hit)}")
        print(f"  Has 'id': {hasattr(hit, 'id')}")
        print(f"  Has 'distance': {hasattr(hit, 'distance')}")
        print(f"  Has 'entity': {hasattr(hit, 'entity')}")
        
        if hasattr(hit, 'entity'):
            entity = hit.entity
            print(f"\nEntity type: {type(entity)}")
            print(f"Entity content: {entity}")
            
            # Try to convert to dict
            try:
                entity_dict = dict(entity)
                print(f"\nEntity dict conversion SUCCESS")
                print(f"Entity dict keys: {entity_dict.keys()}")
                print(f"Entity dict: {entity_dict}")
            except Exception as e:
                print(f"\nEntity dict conversion FAILED: {e}")
        
        # Try dict(hit)
        print(f"\n--- Testing dict(hit) ---")
        try:
            hit_dict = dict(hit)
            print(f"dict(hit) SUCCESS: {hit_dict}")
        except Exception as e:
            print(f"dict(hit) FAILED: {e}")
            
        # Try manual extraction
        print(f"\n--- Testing manual extraction ---")
        try:
            manual_dict = {
                'id': hit.id if hasattr(hit, 'id') else None,
                'distance': hit.distance if hasattr(hit, 'distance') else 0.0,
                'entity': dict(hit.entity) if hasattr(hit, 'entity') else {}
            }
            print(f"Manual extraction SUCCESS:")
            print(f"  ID: {manual_dict['id']}")
            print(f"  Distance: {manual_dict['distance']}")
            print(f"  Entity keys: {manual_dict['entity'].keys() if manual_dict['entity'] else 'None'}")
            print(f"  Entity: {manual_dict['entity']}")
        except Exception as e:
            print(f"Manual extraction FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(debug_hit_structure())
