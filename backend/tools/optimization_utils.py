#!/usr/bin/env python3
"""
Optimization utilities for search system
Includes caching, diversity, and reranking helpers
"""

import time
import hashlib
from typing import List, Dict, Tuple, Any, Optional
from collections import defaultdict
from pathlib import Path
import torch
import torch.nn.functional as F
from PIL import Image


class SearchOptimizer:
    """Helper class for search optimizations"""
    
    def __init__(self, logger):
        self.logger = logger
        self.result_cache: Dict[str, Tuple[float, List]] = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_cache_key(self, first_query: str, second_query: str = "") -> str:
        """Generate cache key for query"""
        query_str = f"{first_query}|{second_query}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def get_cached_results(self, cache_key: str) -> Optional[List]:
        """Get cached results if valid"""
        if cache_key in self.result_cache:
            timestamp, results = self.result_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self.logger.info(f"✅ Cache hit for query: {cache_key[:8]}...")
                return results
            else:
                # Remove expired cache
                del self.result_cache[cache_key]
        return None
    
    def cache_results(self, cache_key: str, results: List):
        """Cache search results"""
        self.result_cache[cache_key] = (time.time(), results)
        
        # Cleanup old cache entries (keep max 1000)
        if len(self.result_cache) > 1000:
            # Remove oldest 100 entries
            sorted_keys = sorted(self.result_cache.items(), key=lambda x: x[1][0])
            for key, _ in sorted_keys[:100]:
                del self.result_cache[key]
        
        self.logger.info(f"📦 Cached results for: {cache_key[:8]}... (total cache: {len(self.result_cache)})")
    
    @staticmethod
    def enforce_diversity(
        results: List[Any],
        min_gap_frames: int = 50,
        max_per_video: int = 5
    ) -> List[Any]:
        """
        Enforce temporal diversity in results
        
        Args:
            results: List of search results
            min_gap_frames: Minimum frame gap within same video
            max_per_video: Maximum results per video
            
        Returns:
            Filtered results with enforced diversity
        """
        selected = []
        video_counts = defaultdict(int)
        last_frames = {}
        
        for result in results:
            # Extract video and frame info
            entity = result.get('entity', {})
            video = entity.get('video', '')
            frame_id = entity.get('frame_id', 0)
            
            # Check video limit
            if video_counts[video] >= max_per_video:
                continue
            
            # Check temporal gap within same video
            if video in last_frames:
                if abs(frame_id - last_frames[video]) < min_gap_frames:
                    continue
            
            selected.append(result)
            video_counts[video] += 1
            last_frames[video] = frame_id
            
            if len(selected) >= 100:
                break
        
        return selected


class CLIPReranker:
    """CLIP-based reranking for search results"""
    
    def __init__(self, clip_model, clip_preprocess, device, logger, keyframes_base_path="/home/ir/retrievalSystem/data/keyframes"):
        self.clip_model = clip_model
        self.clip_preprocess = clip_preprocess
        self.device = device
        self.logger = logger
        self.keyframes_base_path = Path(keyframes_base_path)
    
    async def rerank(self, query_embedding: torch.Tensor, candidates: List[Any], top_k: int = 100) -> List[Any]:
        """
        Rerank candidates using actual CLIP scores
        
        Args:
            query_embedding: Query embedding tensor
            candidates: List of candidate results
            top_k: Number of top results to return
            
        Returns:
            Reranked results
        """
        if not candidates:
            return candidates
        
        reranked = []
        batch_images = []
        batch_candidates = []
        
        # Collect images in batches
        for candidate in candidates[:500]:  # Rerank depth increased to 500
            entity = candidate.get('entity', {})
            keyframe_path = entity.get('keyframe_path', '')
            
            # Build full path
            if keyframe_path:
                full_path = self.keyframes_base_path / keyframe_path
                
                if full_path.exists():
                    batch_candidates.append(candidate)
                    batch_images.append(str(full_path))
                    
                    # Process batch when full
                    if len(batch_images) >= 16:
                        scores = await self._compute_clip_scores_batch(
                            query_embedding, batch_images
                        )
                        
                        for cand, score in zip(batch_candidates, scores):
                            cand['distance'] = float(score)
                            reranked.append(cand)
                        
                        batch_images = []
                        batch_candidates = []
        
        # Process remaining batch
        if batch_images:
            scores = await self._compute_clip_scores_batch(
                query_embedding, batch_images
            )
            for cand, score in zip(batch_candidates, scores):
                cand['distance'] = float(score)
                reranked.append(cand)
        
        # Sort by recomputed scores
        reranked.sort(key=lambda x: x.get('distance', 0), reverse=True)
        
        self.logger.info(f"🔄 Reranked {len(reranked)} candidates (from {len(candidates)})")
        
        return reranked[:top_k]
    
    async def _compute_clip_scores_batch(self, query_embedding: torch.Tensor, image_paths: List[str]) -> List[float]:
        """Compute CLIP similarity scores for a batch of images"""
        try:
            # Load and preprocess images
            images = []
            for path in image_paths:
                try:
                    img = Image.open(path).convert('RGB')
                    images.append(self.clip_preprocess(img))
                except Exception as e:
                    self.logger.warning(f"Failed to load image {path}: {e}")
                    images.append(torch.zeros(3, 224, 224))  # Placeholder
            
            if not images:
                return [0.0] * len(image_paths)
            
            # Batch encode images
            image_batch = torch.stack(images).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_batch)
                image_features = F.normalize(image_features, p=2, dim=-1)
                
                # Compute cosine similarity
                similarities = (query_embedding @ image_features.T).squeeze(0)
                
            return similarities.cpu().tolist()
            
        except Exception as e:
            self.logger.error(f"Error in batch CLIP scoring: {e}")
            return [0.0] * len(image_paths)
