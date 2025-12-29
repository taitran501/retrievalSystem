#!/usr/bin/env python3
"""
Mock DRES Server for Testing
Minimal implementation of DRES API v2 for testing frontend login/submit
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
from datetime import datetime
import os

app = FastAPI(title="Mock DRES Server", version="2.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
sessions = {}
submissions = []
log_file = "dres_submissions.log"

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class SubmissionAnswerKIS(BaseModel):
    mediaItemName: str
    start: int  # milliseconds
    end: int

class SubmissionAnswerQA(BaseModel):
    text: str

class SubmissionAnswerSet(BaseModel):
    answers: List[dict]

class SubmissionRequest(BaseModel):
    session: str
    answerSets: List[SubmissionAnswerSet]

# Mock data
MOCK_EVALUATION = {
    "id": "eval-vsc2024-kis",
    "name": "VSC 2024 KIS Mock Evaluation",
    "description": "Known-Item Search test evaluation",
    "status": "ACTIVE",
    "type": "SYNCHRONOUS",
    "currentTask": {
        "id": "task-001",
        "name": "KIS Task 1",
        "duration": 300
    }
}

# Test query (will be displayed to user)
TEST_QUERY = {
    "query": "Bản tin đưa thông tin về cuộc thi bơi lội tại một bể bơi trong nhà. Một trong những phân cảnh đầu tiên là các vận động viên đang chuẩn bị xuất phát trên bục.",
    "target_video": "V017",
    "target_frame": 6396,
    "target_time": "00:04:15.840"
}

@app.get("/")
async def root():
    return {
        "service": "Mock DRES Server",
        "version": "2.0.0",
        "status": "running",
        "test_query": TEST_QUERY
    }

@app.post("/api/v2/login")
async def login(request: Request):
    """Login endpoint - accepts any credentials"""
    try:
        body = await request.json()
        username = body.get("username", "guest")
        password = body.get("password", "")
        
        session_id = f"session-{username}-{datetime.now().timestamp()}"
        
        sessions[session_id] = {
            "username": username,
            "userId": f"user-{username}",
            "role": "PARTICIPANT",
            "loginTime": datetime.now().isoformat()
        }
        
        print(f"✅ Login: {username} → Session: {session_id}")
        
        return {
            "sessionId": session_id,
            "userId": sessions[session_id]["userId"],
            "username": username,
            "role": "PARTICIPANT"
        }
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v2/client/evaluation/list")
async def list_evaluations():
    """List active evaluations"""
    print("📋 Evaluation list requested")
    return [MOCK_EVALUATION]

@app.get("/api/v2/client/evaluation/current")
async def current_evaluation():
    """Get current active evaluation"""
    print("📋 Current evaluation requested")
    return MOCK_EVALUATION

@app.post("/api/v2/submit/{evaluation_id}")
async def submit_answer(evaluation_id: str, request: Request):
    """Submit answer endpoint"""
    try:
        body = await request.json()
        
        timestamp = datetime.now().isoformat()
        submission = {
            "timestamp": timestamp,
            "evaluation_id": evaluation_id,
            "body": body
        }
        
        submissions.append(submission)
        
        # Log to file
        with open(log_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Submission at {timestamp}\n")
            f.write(f"Evaluation ID: {evaluation_id}\n")
            f.write(f"{json.dumps(body, indent=2)}\n")
        
        # Pretty print to console
        print(f"\n{'='*80}")
        print(f"📤 SUBMISSION RECEIVED - {timestamp}")
        print(f"{'='*80}")
        print(f"Evaluation ID: {evaluation_id}")
        
        if "answerSets" in body and len(body["answerSets"]) > 0:
            answers = body["answerSets"][0]["answers"]
            for idx, answer in enumerate(answers, 1):
                print(f"\nAnswer {idx}:")
                if "mediaItemName" in answer:
                    # KIS format
                    print(f"  Type: KIS (Video Segment)")
                    print(f"  Video: {answer['mediaItemName']}")
                    print(f"  Start: {answer['start']}ms ({answer['start']/1000:.1f}s)")
                    print(f"  End: {answer['end']}ms ({answer['end']/1000:.1f}s)")
                    print(f"  Duration: {(answer['end']-answer['start'])/1000:.1f}s")
                elif "text" in answer:
                    # QA format
                    print(f"  Type: QA (Text Answer)")
                    print(f"  Text: {answer['text']}")
        
        print(f"{'='*80}\n")
        
        return {
            "status": "OK",
            "submissionId": f"sub-{len(submissions)}",
            "timestamp": timestamp,
            "message": "Submission accepted"
        }
        
    except Exception as e:
        print(f"❌ Submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/submissions")
async def get_submissions():
    """View all submissions"""
    return {
        "total": len(submissions),
        "submissions": submissions
    }

@app.get("/api/v2/test-query")
async def get_test_query():
    """Get the test query for manual testing"""
    return TEST_QUERY

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🎯 Mock DRES Server Starting")
    print("="*80)
    print(f"\n📍 Server URL: http://localhost:8888")
    print(f"📝 Login endpoint: POST http://localhost:8888/api/v2/login")
    print(f"📋 Evaluation list: GET http://localhost:8888/api/v2/client/evaluation/list")
    print(f"📤 Submit endpoint: POST http://localhost:8888/api/v2/submit/{{eval_id}}")
    print(f"\n📊 Submissions will be logged to: {log_file}")
    print("\n" + "="*80)
    print("\n🧪 TEST QUERY:")
    print("="*80)
    print(f"Query: {TEST_QUERY['query']}")
    print(f"Target: {TEST_QUERY['target_video']} @ {TEST_QUERY['target_time']}")
    print("="*80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="info")
