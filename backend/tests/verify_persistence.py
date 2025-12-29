
import os
import sys
import time
import json
import asyncio
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

async def test_persistence():
    print("=" * 60)
    print("Verifying Persistent Caching")
    print("=" * 60)

    try:
        from core.config import Config
        from services.vector_search_service import VectorSearchService
        from utils.translator import get_translator
    except ImportError as e:
        print(f"Import error: {e}")
        # Try relative import path if needed
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core.config import Config
        from services.vector_search_service import VectorSearchService
        from utils.translator import get_translator

    config = Config()
    
    # 1. Test Translator Persistence
    print("\n1. Testing Translator Persistence...")
    translator = get_translator()
    query = "một người đàn ông đang đạp xe dưới mưa"
    
    start = time.time()
    translated1 = translator.process_query(query)
    duration1 = time.time() - start
    print(f"First translation: '{translated1}' (took {duration1:.4f}s)")
    
    # Verify file exists
    cache_file = Path(os.path.join(os.path.dirname(__file__), "..", "data", "cache", "translations.json"))
    if cache_file.exists():
        print(f"✅ Persistent translation cache file created: {cache_file}")
    else:
        print(f"❌ Persistent translation cache file NOT found")

    # Simulate restart by creating new translator
    from utils.translator import QueryTranslator
    new_translator = QueryTranslator()
    start = time.time()
    translated2 = new_translator.process_query(query)
    duration2 = time.time() - start
    print(f"Second translation (post-restart): '{translated2}' (took {duration2:.4f}s)")
    
    if duration2 < duration1 or duration2 < 0.01:
        print(f"✅ Translation persistence verified (Speedup: {duration1/max(duration2, 0.0001):.1f}x)")
    else:
        print(f"❌ Translation persistence might not be working as expected")

    # 2. Test Embedding Persistence
    print("\n2. Testing Embedding Persistence...")
    # Note: We don't want to actually load the whole CLIP model if possible for a quick test, 
    # but we need it for encode_clip_text.
    service = VectorSearchService(config)
    
    start = time.time()
    emb1 = service.encode_clip_text("bicycle in rain")
    duration1 = time.time() - start
    print(f"First encoding took {duration1:.4f}s")
    
    emb_file = Path(os.path.join(os.path.dirname(__file__), "..", "data", "cache", "clip_embeddings.json"))
    if emb_file.exists():
        print(f"✅ Persistent embedding cache file created: {emb_file}")
    else:
        print(f"❌ Persistent embedding cache file NOT found")

    # Simulate restart
    new_service = VectorSearchService(config)
    start = time.time()
    emb2 = new_service.encode_clip_text("bicycle in rain")
    duration2 = time.time() - start
    print(f"Second encoding (post-restart) took {duration2:.4f}s")
    
    if duration2 < duration1 or duration2 < 0.01:
        print(f"✅ Embedding persistence verified (Speedup: {duration1/max(duration2, 0.0001):.1f}x)")
    else:
        print(f"❌ Embedding persistence might not be working as expected")

    print("\n" + "=" * 60)
    print("PERSISTENCE VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_persistence())
