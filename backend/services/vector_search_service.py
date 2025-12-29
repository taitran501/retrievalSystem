import os
import json
import time
import logging
import asyncio
import hashlib
import re
from io import BytesIO
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import concurrent.futures

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import open_clip
from pymilvus import MilvusClient
from fastapi import HTTPException, WebSocket

# Import configuration and translator
try:
    from .core.config import Config
except ImportError:
    from core.config import Config

try:
    from .utils.translator import get_translator
except (ImportError, ValueError):
    from utils.translator import get_translator

def log_execution_time(func):
    """Decorator to log function execution time"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.getLogger(__name__).info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper

class VectorSearchService:
    """Main service class that encapsulates all functionality"""

    def __init__(self, config: Config):
        self.config = config
        self.device = torch.device(self.config.model.device)

        # Initialize thread pool for CPU-bound tasks
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.server.max_workers)

        # WebSocket connections
        self.active_connections: List[WebSocket] = []

        # Common query cache for performance
        self.common_queries = ["person", "car", "building"]
        self.precomputed_tokens = {}
        
        # Result caching for performance
        self.result_cache: Dict[str, Tuple[float, List]] = {}  # query_hash -> (timestamp, results)
        self.cache_ttl = getattr(config, 'cache_ttl_seconds', 3600 * 24) # Default to 24h for persistence
        
        # Persistent Cache Directory
        self.cache_dir = Path(os.path.join(os.path.dirname(__file__), "..", "data", "cache")).absolute()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        log_level = getattr(logging, self.config.server.log_level)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Add file handler for persistent logging
        log_file = self.cache_dir / "app.log"
        if not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
            
        # Add console handler if not present
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(console_handler)
            
        self.logger.info(f"Logging initialized. Log file: {log_file}")

        self.query_cache_dir = self.cache_dir / "queries"
        self.query_cache_dir.mkdir(exist_ok=True)
        self.embedding_cache_file = self.cache_dir / "clip_embeddings.json"
        self.embedding_cache = {}
        self._load_embedding_cache()
        self.history_file = self.cache_dir / "history.json"
        
        # Copy optimization flags from config to service
        self.enable_diversity_filter = getattr(config, 'enable_diversity_filter', False)
        self.enable_clip_reranking = getattr(config, 'enable_clip_reranking', False)
        self.diversity_min_gap_frames = getattr(config, 'diversity_min_gap_frames', 50)
        self.diversity_max_per_video = getattr(config, 'diversity_max_per_video', 5)
        self.diversity_max_results = getattr(config, 'diversity_max_results', 50)

        # Initialize models and database connection
        self._initialize_models()
        self._initialize_database()
        
        # Initialize translator
        self.translator = get_translator(backend='auto')

        # Optimization: Cache path bases to avoid redundant calculations
        self.thumbnails_base = Path(os.path.join(os.path.dirname(__file__), "..", "..", "data", "thumbnails")).absolute()
        self.keyframes_base = Path(os.path.join(os.path.dirname(__file__), "..", "..", "data", "keyframes")).absolute()

        # Load video FPS map
        self.video_fps_map = {}
        fps_map_path = Path(__file__).parent.parent / "video_fps_map.json"
        if fps_map_path.exists():
            try:
                with open(fps_map_path, 'r', encoding='utf-8') as f:
                    self.video_fps_map = json.load(f)
                self.logger.info(f"Loaded {len(self.video_fps_map)} entries from {fps_map_path.name}")
            except Exception as e:
                self.logger.error(f"Failed to load video FPS map: {e}")
        else:
            self.logger.warning(f"Video FPS map not found at {fps_map_path}")

    def _load_embedding_cache(self):
        """Load CLIP embeddings from disk"""
        if self.embedding_cache_file.exists():
            try:
                import torch
                with open(self.embedding_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert lists back to tensors
                    self.embedding_cache = {k: torch.tensor(v).to(self.device).float() for k, v in data.items()}
                    self.logger.info(f"Loaded {len(self.embedding_cache)} embeddings from persistent cache")
            except Exception as e:
                self.logger.warning(f"Failed to load persistent embedding cache: {e}")

    def _save_embedding_cache(self):
        """Save CLIP embeddings to disk"""
        try:
            # Convert tensors to lists for JSON serialization
            data = {k: v.cpu().numpy().tolist() for k, v in self.embedding_cache.items()}
            with open(self.embedding_cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            self.logger.warning(f"Failed to save persistent embedding cache: {e}")

    def _initialize_models(self):
        """Initialize ML models (CLIP)"""
        self.logger.info("Initializing ML models...")

        checkpoint_path = self.config.model.clip_checkpoint_path
        
        # Check for local checkpoint first (avoids network calls to HuggingFace)
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.logger.info(f"Loading CLIP from local checkpoint: {checkpoint_path}")
            self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                self.config.model.clip_model_name,
                pretrained=checkpoint_path
            )
        else:
            # Try to load from HuggingFace (requires network)
            try:
                self.logger.info("Loading CLIP from HuggingFace...")
                self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                    self.config.model.clip_model_name,
                    pretrained=self.config.model.clip_pretrained
                )
            except Exception as e:
                self.logger.error(f"Failed to load CLIP model: {e}")
                raise RuntimeError(
                    "Cannot download CLIP model. Either:\n"
                    "1. Fix network connectivity to huggingface.co\n"
                    "2. Set clip_checkpoint_path in config.json to a local .bin/.safetensors file\n"
                    "3. Copy cached model from ~/.cache/huggingface/hub/"
                )
        
        self.clip_model = self.clip_model.to(self.device)
        
        # PERFORMANCE: Force Eval mode and FP16 for much faster inference on GPU
        self.clip_model.eval()
        if 'cuda' in str(self.device):
            self.logger.info("Casting CLIP model to FP16 (Half Precision)")
            self.clip_model.half()
            
        self.clip_tokenizer = open_clip.get_tokenizer(self.config.model.clip_model_name)

        # Precompute common query tokens for performance
        self.precomputed_tokens = {
            query: self.clip_tokenizer([query]).to(self.device)
            for query in self.common_queries
        }

        self.logger.info("Models initialized successfully")

    def _initialize_database(self):
        """Initialize Milvus database connection"""
        self.logger.info("Initializing database connection...")

        # Create Milvus client
        self.milvus_client = MilvusClient(
            uri=f"http://{self.config.database.host}:{self.config.database.port}",
            db=self.config.database.database
        )

        # Load collection
        try:
            self.milvus_client.load_collection(
                collection_name=self.config.database.collection_name,
                replica_number=self.config.database.replica_number
            )

            # Check load state
            load_state = self.milvus_client.get_load_state(
                collection_name=self.config.database.collection_name
            )
            self.logger.info(f"Collection {self.config.database.collection_name} load state: {load_state}")

        except Exception as e:
            self.logger.error(f"Failed to load collection: {e}")
            raise

        self.logger.info("Database connection initialized successfully")

    @lru_cache(maxsize=1000)
    def encode_clip_text(self, query: str) -> torch.Tensor:
        """Encode text using CLIP model with caching"""
        # 1. Check in-memory lru_cache (handled by decorator)
        # 2. Check persistent embedding cache
        if query in self.embedding_cache:
            return self.embedding_cache[query]

        # 3. Check precomputed tokens (extra optimization)
        cached_token = self.precomputed_tokens.get(query)
        if cached_token is not None:
            text_inputs = cached_token
        else:
            text_inputs = self.clip_tokenizer([query]).to(self.device)

        with torch.no_grad():
            text_features = self.clip_model.encode_text(text_inputs)
            result = F.normalize(text_features, p=2, dim=-1)
            
            # Save to persistent cache
            self.embedding_cache[query] = result
            self._save_embedding_cache()
            
            return result

    def encode_clip_image(self, image: Image.Image) -> torch.Tensor:
        """Encode image using CLIP model"""
        image_input = self.clip_preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            image_features = self.clip_model.encode_image(image_input)
            return F.normalize(image_features, p=2, dim=-1)

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from OCR query text"""
        if not text or not text.strip():
            return []
        
        vietnamese_stopwords = {
            'và', 'của', 'có', 'được', 'cho', 'với', 'trong', 'từ', 'đã', 'sẽ',
            'các', 'này', 'đó', 'những', 'một', 'để', 'là', 'như', 'về', 'ở',
            'khi', 'bị', 'vào', 'ra', 'đến', 'thì', 'hoặc', 'nhưng', 'mà',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be'
        }
        
        text = re.sub(r'[^\w\sÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂưăạảấầẩẫậắằẳẵặẹẻẽềềểỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪễệỉịọỏốồổỗộớờởỡợụủứừỬỮỰỲỴÝỶỸửữựỳỵýỷỹ]', ' ', text)
        tokens = text.lower().split()
        return [w for w in tokens if len(w) > 1 and w not in vietnamese_stopwords]
    
    def calculate_text_match_score(self, ocr_text: str, keywords: List[str]) -> float:
        """Calculate text matching score based on keyword overlap"""
        if not keywords or not ocr_text:
            return 0.0
        
        def normalize_vietnamese(text):
            replacements = {
                'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a', 'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
                'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
                'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e', 'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
                'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
                'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o', 'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
                'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
                'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u', 'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
                'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y', 'đ': 'd'
            }
            result = text.lower()
            for viet, latin in replacements.items():
                result = result.replace(viet, latin)
            return result
        
        ocr_lower = ocr_text.lower()
        ocr_normalized = normalize_vietnamese(ocr_text)
        
        match_score = 0.0
        for kw in keywords:
            kw_lower = kw.lower()
            kw_normalized = normalize_vietnamese(kw)
            if kw_lower in ocr_lower: match_score += 1.0
            elif kw_normalized in ocr_normalized: match_score += 0.9
            elif any(kw_normalized in word or word in kw_normalized for word in ocr_normalized.split()): match_score += 0.7
            elif len(kw_normalized) >= 4 and any(kw_normalized in word or word in kw_normalized for word in ocr_normalized.split() if len(word) >= 4): match_score += 0.5
        
        return min(match_score / len(keywords), 1.0)

    @log_execution_time
    async def query_milvus(self, query_vector: torch.Tensor, milvus_filter=None, limit: int = None, include_ocr: bool = True) -> List[Any]:
        """Query Milvus vector database"""
        if limit is None: limit = self.config.database.search_limit
        output_fields = ['keyframe_path', 'frame_id', 'video']
        if include_ocr and self.config.use_ocr_search: output_fields.extend(['ocr_text', 'has_text'])
        if include_ocr and self.config.use_ram_tags: output_fields.extend(['ram_tags', 'has_ram_tags'])

        results = await asyncio.to_thread(
            self.milvus_client.search,
            collection_name=self.config.database.collection_name,
            anns_field="vector",
            data=[query_vector.tolist()[0]],
            limit=limit,
            output_fields=output_fields,
            search_params={"metric_type": "COSINE", "params": {"nprobe": 64}},
            filter=milvus_filter
        )
        
        if not results: return []
        processed_results = []
        for hit in results[0]:
            entity = hit.entity if hasattr(hit, 'entity') else hit
            if 'keyframe_path' in entity: entity['path'] = entity['keyframe_path']
            # REMOVED: Premature 25fps time calculation. 
            # Time is now accurately calculated in _format_single_result using per-batch FPS.
            processed_results.append(hit)
        return processed_results

    async def process_temporal_query(self, first_query: str, second_query: str = "", top_k: int = None) -> List[Any]:
        """Process temporal query with two text queries using SAT translation"""
        start_time = time.time()
        
        # USE SMART TRANSLATION (SAT)
        t_trans_start = time.time()
        first_query_en = self.translator.process_query(first_query)
        second_query_en = self.translator.process_query(second_query) if second_query else ""
        t_trans = time.time() - t_trans_start
        
        if first_query_en != first_query:
            self.logger.info(f"SAT Translated (1): '{first_query}' -> '{first_query_en}' in {t_trans:.4f}s")
        if second_query_en != second_query and second_query:
            self.logger.info(f"SAT Translated (2): '{second_query}' -> '{second_query_en}' in {t_trans:.4f}s")
        
        cache_key = self._get_cache_key(first_query_en, second_query_en, top_k)
        cached_results = self._get_cached_results(cache_key)
        if cached_results is not None: 
            self.logger.info(f"Cache Hit for '{first_query_en}' in {time.time() - start_time:.4f}s")
            return cached_results

        try:
            t_enc_start = time.time()
            if second_query_en and second_query_en.strip():
                first_encoded, second_encoded = await asyncio.gather(
                    asyncio.to_thread(self.encode_clip_text, first_query_en),
                    asyncio.to_thread(self.encode_clip_text, second_query_en)
                )
                self.logger.info(f"CLIP Encoding (Temporal) took {time.time() - t_enc_start:.4f}s")
                fkq, nkq = await asyncio.gather(self.query_milvus(first_encoded), self.query_milvus(second_encoded))
                result = self._process_temporal_relationships(fkq, nkq)
            else:
                first_encoded = await asyncio.to_thread(self.encode_clip_text, first_query_en)
                self.logger.info(f"CLIP Encoding took {time.time() - t_enc_start:.4f}s")
                fkq = await self.query_milvus(first_encoded)
                initial_slice = max(top_k or 1000, 1000)
                result = list(fkq[:initial_slice])

            # Apply diversity filter
            t_div_start = time.time()
            if self.enable_diversity_filter and len(result) > 0:
                max_results = top_k if top_k is not None else self.diversity_max_results
                result = self._enforce_diversity(result, min_gap_frames=self.diversity_min_gap_frames, max_per_video=self.diversity_max_per_video, max_results=max_results)
            elif top_k is not None and len(result) > top_k:
                result = result[:top_k]
            
            if top_k is not None and len(result) > top_k: result = result[:top_k]
            self.logger.info(f"Diversity filtering took {time.time() - t_div_start:.4f}s")
            
            # Apply CLIP reranking
            t_rerank_start = time.time()
            if self.enable_clip_reranking and len(result) > 0:
                result = await self._clip_rerank(first_query_en, result, top_k=top_k or 100)
            self.logger.info(f"CLIP reranking took {time.time() - t_rerank_start:.4f}s")
            
            formatted_results = self._format_results_for_frontend_lite(result)
            
            # Pass query info for history and persistent cache metadata
            query_info = {
                "type": "text_temporal",
                "first_query": first_query,
                "first_query_en": first_query_en,
                "second_query": second_query,
                "second_query_en": second_query_en,
                "top_k": top_k
            }
            self._cache_results(cache_key, formatted_results, query_info=query_info)
            return formatted_results

        except Exception as e:
            self.logger.error(f"Error in temporal query: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            self.logger.info(f"Temporal query finished in {time.time() - start_time:.4f}s")

    def _get_cache_key(self, first_query: str, second_query: str = "", top_k: int = None) -> str:
        query_str = f"{first_query}|{second_query}|{top_k}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _get_cached_results(self, cache_key: str) -> Optional[List]:
        # 1. Check in-memory cache
        if cache_key in self.result_cache:
            timestamp, results = self.result_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl: return results
        
        # 2. Check disk-based persistent cache
        cache_file = self.query_cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    timestamp = data.get('timestamp', 0)
                    results = data.get('results', [])
                    
                    # Validate TTL
                    if time.time() - timestamp < self.cache_ttl:
                        self.logger.info(f"📂 Persistent cache hit: {cache_key}")
                        # Load into memory for next time
                        self.result_cache[cache_key] = (timestamp, results)
                        return results
            except Exception as e:
                self.logger.warning(f"Failed to load cache from disk: {e}")
                
        return None
    
    def _cache_results(self, cache_key: str, results: List, query_info: Dict = None):
        timestamp = time.time()
        
        # 1. Update in-memory cache
        self.result_cache[cache_key] = (timestamp, results)
        if len(self.result_cache) > 1000:
            sorted_keys = sorted(self.result_cache.items(), key=lambda x: x[1][0])
            for key, _ in sorted_keys[:100]: del self.result_cache[key]
        
        # 2. Update disk-based persistent cache
        cache_file = self.query_cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'query_info': query_info or {},
                    'results': results
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache to disk: {e}")
            
        # 3. Update history log (Optional but useful)
        if query_info:
            self._log_history(query_info)

    def _log_history(self, query_info: Dict):
        try:
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # Add to history (limit to last 1000 items)
            query_info['timestamp'] = time.time()
            history.insert(0, query_info)
            history = history[:1000]
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to log history: {e}")
    
    def _enforce_diversity(self, results: List[Any], min_gap_frames: int = 50, max_per_video: int = 5, max_results: int = 50) -> List[Any]:
        selected = []
        video_counts = defaultdict(int)
        last_frames = {}
        for result in results:
            entity = result.get('entity', {})
            video = entity.get('video', '')
            frame_id = entity.get('frame_id', 0)
            if video_counts[video] >= max_per_video: continue
            if video in last_frames and abs(frame_id - last_frames[video]) < min_gap_frames: continue
            selected.append(result)
            video_counts[video] += 1
            last_frames[video] = frame_id
            if len(selected) >= max_results: break
        
        if len(selected) < max_results:
            for result in results:
                if result in selected: continue
                video = result.get('entity', {}).get('video', '')
                if video_counts[video] < max_per_video + 5:
                    selected.append(result); video_counts[video] += 1
                    if len(selected) >= max_results: break
        return selected
    
    async def _clip_rerank(self, query: str, candidates: List[Any], top_k: int = 100) -> List[Any]:
        if not candidates: return candidates
        query_embedding = self.encode_clip_text(query)
        
        # Use config depth or default
        rerank_depth = getattr(self.config, 'rerank_top_k', top_k * 3)
        rerank_depth = max(50, min(rerank_depth, 500))
        
        reranked = []
        to_rerank = candidates[:rerank_depth]
        
        # INSTRUMENTATION: Log start of reranking
        self.logger.info(f"Starting rerank of {len(to_rerank)} candidates (max depth: {rerank_depth})")
        
        # Pre-collect valid paths to avoid inner loop overhead
        batch_images = []
        batch_candidates = []
        
        # PERFORMANCE: Optimal batch size for 4GB VRAM
        OPTIMAL_BATCH_SIZE = 8 
        
        for i, candidate in enumerate(to_rerank):
            keyframe_path = candidate.get('entity', {}).get('keyframe_path', '')
            if not keyframe_path: continue
            
            # PERFORMANCE: Skip thumbnails check (deleted for space)
            # Directly use keyframes for CLIP reranking
            full_path = self.keyframes_base / keyframe_path
            
            if full_path.exists():
                batch_candidates.append(candidate)
                batch_images.append(str(full_path))
                
                # Process in optimal batches
                if len(batch_images) >= OPTIMAL_BATCH_SIZE:
                    scores = await self._compute_clip_scores_batch(query_embedding, batch_images)
                    for cand, score in zip(batch_candidates, scores):
                        cand['distance'] = float(score)
                        reranked.append(cand)
                    batch_images = []
                    batch_candidates = []
                    
        if batch_images:
            scores = await self._compute_clip_scores_batch(query_embedding, batch_images)
            for cand, score in zip(batch_candidates, scores):
                cand['distance'] = float(score)
                reranked.append(cand)
                
        reranked.sort(key=lambda x: x.get('distance', 0), reverse=True)
        return reranked[:top_k]

    async def _compute_clip_scores_batch(self, query_embedding: torch.Tensor, image_paths: List[str]) -> List[float]:
        try:
            t_start = time.time()
            # OPTIMIZATION: Reuse the persistent thread pool for parallel disk I/O
            loop = asyncio.get_event_loop()
            
            def load_and_preprocess_batch(paths):
                results = []
                for path in paths:
                    try:
                        # Convert to RGB explicitly and preprocess
                        img = Image.open(path).convert('RGB')
                        results.append(self.clip_preprocess(img))
                    except Exception as e:
                        print(f"Error loading {path}: {e}")
                        results.append(torch.zeros(3, 224, 224))
                return results

            # Run batch loading in existing thread pool
            images = await loop.run_in_executor(self.thread_pool, load_and_preprocess_batch, image_paths)
            t_load = time.time() - t_start

            if not images: return [0.0] * len(image_paths)
            
            t_inference_start = time.time()
            image_batch = torch.stack(images).to(self.device).half()
            
            # Ensure GPU completes previous work for accurate timing
            if 'cuda' in str(self.device): torch.cuda.synchronize()
            t_after_stack = time.time()
            
            # OPTIMIZATION: Use NEW Mixed Precision (FP16) syntax
            with torch.no_grad(), torch.amp.autocast(device_type='cuda' if 'cuda' in str(self.device) else 'cpu'):
                image_features = self.clip_model.encode_image(image_batch)
                image_features = F.normalize(image_features, p=2, dim=-1)
                similarities = (query_embedding @ image_features.T).squeeze(0)
            
            if 'cuda' in str(self.device): torch.cuda.synchronize()
            t_inference = time.time() - t_after_stack
            
            # INSTRUMENTATION: Change to DEBUG to reduce console noise (only summary is usually needed)
            self.logger.debug(f"Batch of {len(image_paths)}: Load={t_load:.3f}s, Stack={t_after_stack - t_inference_start:.3f}s, Inference={t_inference:.3f}s")
            
            return similarities.cpu().tolist()
        except Exception as e:
            self.logger.error(f"Batch score error: {e}")
            return [0.0] * len(image_paths)

    async def process_sequential_queries(self, queries: List[str], top_k: int = 50, require_all_steps: bool = False, time_gap_constraints: Optional[List[Dict[str, int]]] = None) -> Dict[str, Any]:
        """Process sequential queries with SAT translation"""
        start_time = time.time()
        # USE SMART TRANSLATION (SAT)
        translated_queries = [self.translator.process_query(q) for q in queries]
        self.logger.info(f"Sequential SAT: {queries} -> {translated_queries}")
        
        cache_key = hashlib.md5(f"{'|'.join(translated_queries)}|{top_k}".encode()).hexdigest()
        cached = self._get_cached_results(cache_key)
        if cached is not None: return cached
        
        try:
            encoded_queries = await asyncio.gather(*[asyncio.to_thread(self.encode_clip_text, q) for q in translated_queries])
            search_limit = getattr(self.config, 'sequential_search_limit_per_step', 1000)
            step_results = await asyncio.gather(*[self.query_milvus(enc, limit=search_limit) for enc in encoded_queries])
            paths = self._build_sequential_paths(step_results, translated_queries, time_gap_constraints)
            scored_paths = self._score_sequential_paths(paths, len(queries), require_all_steps)
            final_results = scored_paths[:top_k]
            
            formatted_results = []
            for path_data in final_results:
                hit = path_data['result']
                hit_dict = {'id': getattr(hit, 'id', None), 'distance': getattr(hit, 'distance', 0.0), 'entity': dict(hit.entity) if hasattr(hit, 'entity') else {}}
                if 'entity' in hit_dict['entity'] and isinstance(hit_dict['entity']['entity'], dict): hit_dict['entity'].update(hit_dict['entity']['entity'])
                hit_dict.update({'matched_steps': path_data['matched_steps'], 'completeness': path_data['completeness'], 'sequential_score': path_data['score']})
                if 'path' in hit_dict['entity'] and 'keyframe_path' not in hit_dict['entity']: hit_dict['entity']['keyframe_path'] = hit_dict['entity']['path']
                formatted_results.append(self._format_single_result(hit_dict))
            
            response = {'kq': formatted_results, 'total_results': len(formatted_results), 'num_steps': len(queries), 'queries': translated_queries, 'execution_time': time.time() - start_time}
            self._cache_results(cache_key, response)
            return response
        except Exception as e:
            self.logger.error(f"Sequential error: {e}"); raise HTTPException(status_code=500, detail=str(e))

    def _build_sequential_paths(self, step_results, queries, time_gap_constraints):
        num_steps = len(step_results)
        video_frames = defaultdict(lambda: defaultdict(list))
        for step_idx, results in enumerate(step_results):
            for hit in results:
                video = hit.entity['video']
                frame_id = int(hit.entity['frame_id'])
                video_frames[video][step_idx].append({'frame_id': frame_id, 'result': hit, 'score': hit.score, 'step': step_idx})
        
        paths = []
        for video, steps_data in video_frames.items():
            if 0 not in steps_data: continue
            for first_hit in steps_data[0]:
                matched_steps = [0]; last_frame = first_hit['frame_id']
                for step_idx in range(1, num_steps):
                    if step_idx not in steps_data: continue
                    candidates = [h for h in steps_data[step_idx] if h['frame_id'] > last_frame]
                    if not candidates: continue
                    if time_gap_constraints and step_idx - 1 < len(time_gap_constraints):
                        constraint = time_gap_constraints[step_idx - 1]
                        min_gap, max_gap = constraint.get('min', 0)*25, constraint.get('max', 1500)*25
                        candidates = [h for h in candidates if min_gap <= (h['frame_id']-last_frame) <= max_gap]
                    if candidates:
                        best = max(candidates, key=lambda x: x['score'])
                        matched_steps.append(step_idx); last_frame = best['frame_id']
                paths.append({'result': first_hit['result'], 'video': video, 'matched_steps': matched_steps, 'num_matched': len(matched_steps), 'completeness': len(matched_steps)/num_steps})
        return paths

    def _score_sequential_paths(self, paths, num_steps, require_all_steps):
        scored = []
        for path in paths:
            if require_all_steps and path['num_matched'] < num_steps: continue
            similarity = 1.0 - path['result'].distance
            consecutive_bonus = 0.0
            if path['num_matched'] > 1:
                steps = path['matched_steps']
                consecutive_count = sum(1 for i in range(len(steps)-1) if steps[i+1] == steps[i]+1)
                consecutive_bonus = consecutive_count / (num_steps - 1)
            score = (path['completeness'] * 0.5) + (similarity * 0.4) + (consecutive_bonus * 0.1)
            path.update({'score': score, 'similarity': similarity, 'coherence': consecutive_bonus})
            scored.append(path)
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored

    def _process_temporal_relationships(self, first_results: List[Any], second_results: List[Any]) -> List[Any]:
        fkq_data = torch.tensor([[int(item.entity['frame_id']), item.score, hash(item.entity['video'])] for item in first_results], device=self.device)
        nkq_data = torch.tensor([[int(item.entity['frame_id']), item.score, hash(item.entity['video'])] for item in second_results], device=self.device)
        frame_diff = nkq_data[:, None, 0] - fkq_data[None, :, 0]
        same_video_mask = fkq_data[None, :, 2] == nkq_data[:, None, 2]
        valid_frame_diff_mask = (frame_diff > 0) & (frame_diff <= 1500) & same_video_mask
        score_increase = nkq_data[:, None, 1] * (1500 - frame_diff) / 1500
        score_increase = torch.where(valid_frame_diff_mask, score_increase, torch.zeros_like(score_increase))
        fkq_data[:, 1] += score_increase.max(dim=0).values
        scores = fkq_data[:, 1].cpu().numpy()
        sorted_indices = np.argsort(scores)[::-1][:1000]
        return [first_results[i] for i in sorted_indices]

    def _format_results_for_frontend_lite(self, results):
        formatted = []
        for hit in results:
            # 1. Normalize hitting format (Hit object vs Dict)
            if isinstance(hit, dict):
                # MilvusClient return
                id_val = hit.get('id')
                dist_val = hit.get('distance', 0.0)
                entity = hit.get('entity', hit).copy() # Use copy to avoid modifying original
            else:
                # pymilvus Hit object
                id_val = getattr(hit, 'id', None)
                dist_val = getattr(hit, 'distance', 0.0)
                entity = dict(hit.entity) if hasattr(hit, 'entity') else {}

            # 2. Aggressive flattening of entity
            # Some indexing scripts might nest 'entity' inside hit.entity
            while 'entity' in entity and isinstance(entity['entity'], dict):
                inner = entity.pop('entity')
                entity.update(inner)
            
            # 3. Clean up entity (remove redundant fields)
            entity.pop('vector', None)
            entity.pop('distance', None)
            
            # 4. Construct clean hit_dict
            hit_dict = {
                'id': id_val,
                'distance': dist_val,
                'entity': entity
            }
                
            formatted.append(self._format_single_result(hit_dict))
        return formatted

    def get_fps_for_video(self, video_id):
        """Return FPS for a given video ID using the precomputed map."""
        # Handle potential prefixes or extensions
        vid = video_id.replace('.mp4', '')
        # Special case: L16_V001 -> vid is already normalized
        return self.video_fps_map.get(vid, 25.0)

    def _format_single_result(self, hit_dict):
        """Format a single search result for the frontend"""
        if 'entity' in hit_dict:
            entity = hit_dict['entity']
            
            # Ensure 'keyframe_path' exists
            if 'path' in entity and 'keyframe_path' not in entity:
                entity['keyframe_path'] = entity['path']
            
            # Use keyframes as thumbnails (thumbnails deleted for space)
            if 'keyframe_path' in entity:
                entity['thumbnail_path'] = entity['keyframe_path']
                # 1. Video path extraction and batch identification
                batch = "L01" # Default
                parts = entity['keyframe_path'].split('/')
                if len(parts) >= 2:
                    batch = parts[0].replace('/', '')
                    video_name = parts[1]
                    
                    # Normalize video ID for frontend compatibility (L01_V001)
                    entity['video'] = f"{batch}_{video_name}"
                    entity['video_path'] = f"{batch}_{video_name}.mp4"
                
                # 2. Frame ID extraction/validation - FILENAME IS TRUTH
                try:
                    filename = os.path.basename(entity['keyframe_path'])
                    filename_frame_id = int(filename.split('.')[0])
                    # FORCE filename frame_id to avoid DB misalignment
                    entity['frame_id'] = filename_frame_id
                except (ValueError, IndexError):
                    pass
                
                # 3. Time calculation based on VERIFIED frame_id and PRECISE video FPS
                fid = entity.get('frame_id', 0)
                # Correct video ID extraction (Batch_Video)
                v_id = entity.get('video', '')
                fps = self.get_fps_for_video(v_id)
                entity['fps'] = fps # Send FPS to frontend
                
                # Calculate REAL time from frame_id (Always accurate regardless of metadata corruption)
                entity['time_seconds'] = float(fid) / fps
                
                # Format display time string HH:MM:SS.mmm
                t_float = entity['time_seconds']
                m, s = divmod(t_float, 60)
                h, m = divmod(m, 60)
                entity['time'] = f"{int(h):02d}:{int(m):02d}:{s:06.3f}"
                
                # 4. KIS segment for DRES submission
                entity['kis_segment'] = self.calculate_kis_segment(int(fid), entity['time_seconds'], fps=fps)
                
            return hit_dict

    async def get_neighbors(self, video: str, frame_id: int, count: int = 3, stride: int = 25, keyframe_path: str = ''):
        """Find temporal neighbors for a frame from disk"""
        try:
            batch_folder = None
            if keyframe_path:
                parts = keyframe_path.split('/')
                if len(parts) >= 2: batch_folder = parts[0]
            
            if not batch_folder: return []
            
            keyframes_base = Path(os.path.join(os.path.dirname(__file__), "..", "..", "data", "keyframes"))
            
            # If video has batch prefix (e.g. L16_V021), strip it for directory resolution
            v_dir_name = video
            if '_' in video and batch_folder and video.startswith(batch_folder):
                v_dir_name = video[len(batch_folder)+1:]
            
            video_dir = keyframes_base / batch_folder / v_dir_name
            if not video_dir.exists():
                self.logger.warning(f"Video directory not found: {video_dir}")
                # Fallback: try raw video name
                video_dir = keyframes_base / batch_folder / video
                if not video_dir.exists(): return []
            
            all_files = os.listdir(video_dir)
            all_frame_ids = []
            for f in all_files:
                if f.endswith('.jpg'):
                    try: all_frame_ids.append(int(f[:-4]))
                    except: pass
            all_frame_ids.sort()
            
            import bisect
            curr_idx = bisect.bisect_left(all_frame_ids, frame_id)
            
            neighbors_before = []
            scan_idx = curr_idx - 1
            last_val = frame_id
            while len(neighbors_before) < count and scan_idx >= 0:
                cid = all_frame_ids[scan_idx]
                if abs(last_val - cid) >= stride:
                    # Construct normalized video ID (L01_V001)
                    norm_video = video
                    if '_' not in video and batch_folder:
                        norm_video = f"{batch_folder}_{video}"
                    
                    # accurate time calculation based on precise video FPS
                    fps = self.get_fps_for_video(norm_video)
                    est_time_seconds = float(cid) / fps
                    m, s = divmod(est_time_seconds, 60)
                    h, m = divmod(m, 60)
                    time_str = f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

                    neighbors_before.append({
                        "keyframe_path": f"{batch_folder}/{v_dir_name}/{cid}.jpg",
                        "thumbnail_path": f"{batch_folder}/{v_dir_name}/{cid}.jpg",
                        "frame_id": cid, 
                        "video": norm_video, 
                        "time": time_str, 
                        "time_seconds": est_time_seconds,
                        "video_path": f"{norm_video}.mp4",
                        "offset": cid - frame_id
                    })
                    last_val = cid
                scan_idx -= 1
            
            neighbors_after = []
            scan_idx = curr_idx + 1 if (curr_idx < len(all_frame_ids) and all_frame_ids[curr_idx] == frame_id) else curr_idx
            last_val = frame_id
            while len(neighbors_after) < count and scan_idx < len(all_frame_ids):
                cid = all_frame_ids[scan_idx]
                if abs(cid - last_val) >= stride:
                    # Construct normalized video ID (L01_V001)
                    norm_video = video
                    if '_' not in video and batch_folder:
                        norm_video = f"{batch_folder}_{video}"

                    # Accurate time calculation
                    fps = self.get_fps_for_video(norm_video)
                    est_time_seconds = float(cid) / fps
                    m, s = divmod(est_time_seconds, 60)
                    h, m = divmod(m, 60)
                    time_str = f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

                    neighbors_after.append({
                        "keyframe_path": f"{batch_folder}/{v_dir_name}/{cid}.jpg",
                        "thumbnail_path": f"{batch_folder}/{v_dir_name}/{cid}.jpg",
                        "frame_id": cid, 
                        "video": norm_video, 
                        "time": time_str, 
                        "time_seconds": est_time_seconds,
                        "video_path": f"{norm_video}.mp4",
                        "offset": cid - frame_id
                    })
                    last_val = cid
                scan_idx += 1
                
            return list(reversed(neighbors_before)) + neighbors_after
        except Exception as e:
            self.logger.error(f"Error in get_neighbors: {e}")
            return []

    def calculate_kis_segment(self, frame_id: int, time_seconds: float, window_seconds: float = 0.5, fps: float = 25.0):
        # Dynamically determine frame rate for the segment (default to 25 if unknown)
        # However, for KIS we mostly care about time_seconds
        # Adjust window to +/- 0.5s for higher precision (1s total)
        ts = max(0, time_seconds - window_seconds)
        te = time_seconds + window_seconds
        
        # We also provide approximate start/end frames
        # usage of precise FPS ensures the segment marker is accurate for systems relying on frames
        start_frame = max(0, frame_id - (window_seconds * fps))
        end_frame = frame_id + (window_seconds * fps)
        
        return {
            'start_ms': int(ts*1000), 
            'end_ms': int(te*1000), 
            'start_seconds': ts, 
            'end_seconds': te, 
            'start_frame': start_frame, 
            'end_frame': end_frame
        }
