import os
import logging

# Module-level suppression to catch watchfiles logs in the supervisor process
logging.getLogger("watchfiles").setLevel(logging.WARNING)
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import Config
from services.vector_search_service import VectorSearchService
from api.routes import router

def create_app(config_file: str = None) -> FastAPI:
    """Create and configure FastAPI application"""
    config = Config(config_file)
    
    # Setup logging
    log_file = Path(__file__).parent / "data" / "cache" / "backend_server.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress verbose watchfiles logs (prevents "X change detected" spam)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    
    # Ensure uvicorn logs go to our handlers
    for logger_name in ["uvicorn", "uvicorn.error"]:
        l = logging.getLogger(logger_name)
        l.handlers = [file_handler, console_handler]
        l.propagate = False
        
    root_logger.info(f"Backend starting. Global log file: {log_file}")
    
    # Initialize service
    service = VectorSearchService(config)

    app = FastAPI(
        title="Vector Search Service",
        description="Modularized high-performance vector search service",
        version="2.0.0"
    )

    # Store config and service in app state for access in routes
    app.state.config = config
    app.state.service = service

    # Configure CORS
    origins = config.server.cors_origins.split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600,
    )

    # Add GZip compression
    app.add_middleware(
        GZipMiddleware,
        minimum_size=config.server.gzip_minimum_size
    )

    # Mount static files
    base_dir = Path(__file__).parent.parent
    video_path = base_dir / "data" / "video"
    keyframes_path = base_dir / "data" / "keyframes"
    thumbnails_path = base_dir / "data" / "thumbnails"

    if video_path.exists():
        app.mount("/videos", StaticFiles(directory=str(video_path)), name="videos")
    if keyframes_path.exists():
        app.mount("/keyframes", StaticFiles(directory=str(keyframes_path)), name="keyframes")
    
    # Fallback: Serve keyframes at /thumbnails if thumbnails folder is deleted
    if thumbnails_path.exists():
        app.mount("/thumbnails", StaticFiles(directory=str(thumbnails_path)), name="thumbnails")
    elif keyframes_path.exists():
        app.mount("/thumbnails", StaticFiles(directory=str(keyframes_path)), name="thumbnails")

    # Include routes
    app.include_router(router)

    return app

# Module-level app instance
config_file = os.getenv("CONFIG_FILE", os.path.join(os.path.dirname(__file__), "config.json"))
app = create_app(config_file)

if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn logging
    # We want to keep our custom app loggers and suppress uvicorn access logs
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"
    log_config["loggers"]["uvicorn.error"]["level"] = "INFO"
    
    # Also suppress watchfiles in the uvicorn log config
    if "watchfiles" not in log_config["loggers"]:
        log_config["loggers"]["watchfiles"] = {"level": "WARNING"}
    else:
        log_config["loggers"]["watchfiles"]["level"] = "WARNING"
        
    log_config["disable_existing_loggers"] = False
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_config=log_config, reload=True)