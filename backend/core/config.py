import os
import json
import logging
from dataclasses import dataclass
from typing import Optional
import torch

@dataclass
class ModelConfig:
    """Configuration for ML models"""
    clip_model_name: str = "ViT-H-14-378-quickgelu"
    clip_pretrained: str = "dfn5b"
    device: str = "cuda"  # auto-detected if cuda available
    clip_checkpoint_path: Optional[str] = None  # Path to local checkpoint file

@dataclass
class DatabaseConfig:
    """Configuration for Milvus vector database"""
    host: str = "192.168.20.156"
    port: int = 19530
    database: str = "default"
    collection_name: str = "AIC_2024_1"
    search_limit: int = 3000
    replica_number: int = 1

@dataclass
class ServerConfig:
    """Configuration for FastAPI server"""
    cors_origins: str = "http://localhost:8007,https://localhost:8005,https://localhost:8443"
    max_workers: int = 4
    log_level: str = "INFO"
    gzip_minimum_size: int = 1000

class Config:
    """Main configuration class that loads from environment variables or config file"""

    def __init__(self, config_file: str = None):
        # Load from config file if provided
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = {}

        # Initialize configurations with env variables or config file values
        self.model = ModelConfig(
            clip_model_name=os.getenv("CLIP_MODEL_NAME", config_data.get("clip_model_name", "ViT-H-14-378-quickgelu")),
            clip_pretrained=os.getenv("CLIP_PRETRAINED", config_data.get("clip_pretrained", "dfn5b")),
            device=os.getenv("DEVICE", config_data.get("device", "cuda")),
            clip_checkpoint_path=os.getenv("CLIP_CHECKPOINT_PATH", config_data.get("clip_checkpoint_path"))
        )

        self.database = DatabaseConfig(
            host=os.getenv("MILVUS_HOST", config_data.get("milvus_host", "192.168.20.156")),
            port=int(os.getenv("MILVUS_PORT", config_data.get("milvus_port", 19530))),
            database=os.getenv("MILVUS_DATABASE", config_data.get("milvus_database", "default")),
            collection_name=os.getenv("COLLECTION_NAME", config_data.get("collection_name", "AIC_2024_1")),
            search_limit=int(os.getenv("SEARCH_LIMIT", config_data.get("search_limit", 3000))),
            replica_number=int(os.getenv("REPLICA_NUMBER", config_data.get("replica_number", 1)))
        )

        self.server = ServerConfig(
            cors_origins=os.getenv("CORS_ORIGINS", config_data.get("cors_origins", "http://localhost:8007,https://localhost:8005,https://localhost:8443")),
            max_workers=int(os.getenv("MAX_WORKERS", config_data.get("max_workers", 4))),
            log_level=os.getenv("LOG_LEVEL", config_data.get("log_level", "INFO")),
            gzip_minimum_size=int(os.getenv("GZIP_MIN_SIZE", config_data.get("gzip_minimum_size", 1000)))
        )

        # Auto-detect device if cuda specified but not available
        if self.model.device == "cuda" and not torch.cuda.is_available():
            self.model.device = "cpu"
            logging.warning("CUDA requested but not available, falling back to CPU")
        
        # Load optimization settings
        self.enable_query_caching = config_data.get("enable_query_caching", False)
        self.enable_diversity_filter = config_data.get("enable_diversity_filter", False)
        self.enable_clip_reranking = config_data.get("enable_clip_reranking", False)
        self.use_ocr_search = config_data.get("use_ocr_search", False)  # OCR hybrid search
        self.use_ram_tags = config_data.get("use_ram_tags", False)  # RAM tags search
        self.diversity_min_gap_frames = config_data.get("diversity_min_gap_frames", 50)
        self.diversity_max_per_video = config_data.get("diversity_max_per_video", 5)
        self.diversity_max_results = config_data.get("diversity_max_results", 100) 
        self.cache_ttl_seconds = config_data.get("cache_ttl_seconds", 300)
        self.google_api_key = config_data.get("google_api_key")
        self.google_search_engine_id = config_data.get("google_search_engine_id")
