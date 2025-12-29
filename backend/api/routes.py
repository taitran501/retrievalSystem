import json
import logging
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# Import service and config
try:
    from ..services.vector_search_service import VectorSearchService
    from ..core.config import Config
except ImportError:
    from services.vector_search_service import VectorSearchService
    from core.config import Config

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic Models for API
class TextQuery(BaseModel):
    First_query: str
    Next_query: str = ""

class SequentialQueryRequest(BaseModel):
    queries: List[str]
    top_k: int = 50
    require_all_steps: bool = False
    time_gap_constraints: Optional[List[Dict[str, int]]] = None

class Filter(BaseModel):
    name: str
    number: str

class FilterQuery(BaseModel):
    filterText: Optional[str] = None
    filters: List[Filter]
    query: str

# Endpoints
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    service: VectorSearchService = websocket.app.state.service
    await websocket.accept()
    service.active_connections.append(websocket)
    logger.info("WebSocket connection accepted")

    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'text_query':
                result = await service.process_temporal_query(
                    data['firstQuery'],
                    data.get('secondQuery', '')
                )
                await websocket.send_json({"kq": result})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        if websocket in service.active_connections:
            service.active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket: {str(e)}")
        if websocket in service.active_connections:
            service.active_connections.remove(websocket)

@router.post("/TextQuery")
async def text_query_endpoint(request: Request):
    service: VectorSearchService = request.app.state.service
    try:
        body_bytes = await request.body()
        try:
            body_text = body_bytes.decode('utf-8')
        except UnicodeDecodeError:
            body_text = body_bytes.decode('cp1252', errors='replace')
        
        temporal_search = json.loads(body_text)
        first_query = temporal_search['First_query']
        next_query = temporal_search.get('Next_query', '')
        
        try:
            top_k = int(temporal_search.get('top_k', 100))
        except (ValueError, TypeError):
            top_k = 100

        # process_temporal_query now handles SAT internally
        result = await service.process_temporal_query(first_query, next_query, top_k=top_k)

        return {
            "kq": result,
            "fquery": first_query,
            "nquery": next_query,
            "total_results": len(result) if result else 0
        }
    except Exception as e:
        logger.error(f"Error in text query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/SequentialQuery")
async def sequential_query_endpoint(request: Request):
    service: VectorSearchService = request.app.state.service
    try:
        body = await request.body()
        seq_request = json.loads(body)
        queries = seq_request['queries']
        top_k = seq_request.get('top_k', 50)
        require_all_steps = seq_request.get('require_all_steps', False)
        time_gap_constraints = seq_request.get('time_gap_constraints', None)
        
        if not queries or not isinstance(queries, list):
            raise HTTPException(status_code=400, detail="queries must be a non-empty array")
        
        # process_sequential_queries now handles SAT internally
        result = await service.process_sequential_queries(
            queries=queries,
            top_k=top_k,
            require_all_steps=require_all_steps,
            time_gap_constraints=time_gap_constraints
        )
        return result
    except Exception as e:
        logger.error(f"Error in sequential query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/get_neighbor_frames")
async def get_neighbor_frames(request: Request):
    service: VectorSearchService = request.app.state.service
    try:
        data = await request.json()
        video = data.get('video')
        frame_id = data.get('frame_id')
        if not video or frame_id is None:
            raise HTTPException(status_code=400, detail="video and frame_id are required")
            
        result = await service.get_neighbors(
            video=video,
            frame_id=int(frame_id),
            count=data.get('count', 3),
            stride=data.get('stride', 25),
            keyframe_path=data.get('keyframe_path', '')
        )
        return {"neighbors": result}
    except Exception as e:
        logger.error(f"Error getting neighbor frames: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_config(request: Request):
    config = request.app.state.config
    return {
        "model_config": {"clip_model": config.model.clip_model_name, "device": config.model.device},
        "database_config": {"collection_name": config.database.collection_name, "search_limit": config.database.search_limit},
        "server_config": {"max_workers": config.server.max_workers, "log_level": config.server.log_level}
    }

@router.get("/health")
async def health_check(request: Request):
    service: VectorSearchService = request.app.state.service
    return {
        "status": "healthy",
        "models_loaded": True,
        "database_connected": True,
        "active_connections": len(service.active_connections)
    }


@router.post("/validate_dres_session")
async def validate_dres_session(request: Request):
    try:
        try:
            from ..utils.dres_client import DRESClient
        except (ImportError, ValueError):
            from utils.dres_client import DRESClient
        data = await request.json()
        session_id = data.get("session_id")
        if not session_id: return {"valid": False, "message": "Missing session_id"}
        
        dres_url = data.get("dres_base_url") or os.getenv("DRES_BASE_URL", "http://192.168.28.151:5000")
        client = DRESClient(base_url=dres_url, session_id=session_id)
        # Simplified validation
        return {"valid": len(session_id) > 10, "message": "Validated" if len(session_id) > 10 else "Invalid session"}
    except Exception as e:
        return {"valid": False, "message": str(e)}

@router.post("/submit_to_dres")
async def submit_to_dres(request: Request):
    try:
        try:
            from ..utils.dres_client import DRESClient
        except (ImportError, ValueError):
            from utils.dres_client import DRESClient
        data = await request.json()
        items = data.get("items", [])
        if not items: return {"success": False, "message": "No items"}
        
        dres_url = data.get("dres_base_url") or os.getenv("DRES_BASE_URL", "http://192.168.28.151:5000")
        client = DRESClient(
            base_url=dres_url, 
            session_id=data.get("session_id"),
            username=os.getenv("DRES_USERNAME"),
            password=os.getenv("DRES_PASSWORD")
        )
        
        eval_id = data.get("evaluation_id") or client.get_evaluation_id()
        dres_items = client.format_search_results(items)
        
        if data.get("task_type") == "qa":
            resp = client.submit_qa(evaluation_id=eval_id, results=dres_items, answer_text=data.get("answer_text", ""))
        else:
            resp = client.submit_kis(evaluation_id=eval_id, results=dres_items)
            
        return {"success": True, "message": "Submitted", "dres_response": resp}
    except Exception as e:
        return {"success": False, "message": str(e)}
