
import os
import sys
import time
import asyncio
import logging
from pathlib import Path

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.append(str(backend_path))

from core.config import Config
from services.vector_search_service import VectorSearchService

async def main():
    # Configure logging to console
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("QueryLogger")

    config_path = backend_path / "config.json"
    config = Config(str(config_path))
    service = VectorSearchService(config)

    # Queries to test
    # Queries to test (Complex Vietnamese)
    test_queries = [
        "Một nhóm người đang nhảy múa vui vẻ trong công viên vào buổi sáng đẹp trời",
        "Người đàn ông mặc áo vest đen đang cầm ly rượu vang đỏ đứng cạnh cửa sổ kính lớn",
        "Cảnh quay flycam nhìn xuống một con đường kẹt xe với nhiều ô tô và xe máy chen chúc nhau",
        "Những đứa trẻ đang chơi đá bóng trên bãi biển cát trắng dưới ánh hoàng hôn rực rỡ"
    ]

    print("\n" + "="*60)
    print("BACKEND QUERY TIMING REPORT")
    print("="*60)

    for q in test_queries:
        print(f"\nQUERY: {q}")
        
        # Track total time
        start_time = time.time()
        
        # This will trigger:
        # 1. Translation (QueryTranslator)
        # 2. CLIP Encoding (VectorSearchService.encode_clip_text)
        # 3. Milvus Search (VectorSearchService.query_milvus)
        # 4. Reranking (if enabled)
        
        results = await service.process_temporal_query(q, top_k=50)
        
        total_duration = time.time() - start_time
        print(f"TOTAL TIME: {total_duration:.4f} seconds")
        print(f"Results found: {len(results)}")

    print("\n" + "="*60)
    print("END OF REPORT")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
