import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.config import HOST, PORT, EMBEDDING_MODEL_NAME, CHROMA_COLLECTION_NAME
from backend.models import (
    Task, TaskCreate, TaskUpdate, ProjectNote, ProjectNoteCreate,
    TaskProposal, ConfirmationRequest, AgentChatRequest, AgentChatResponse
)
from backend.vector_store import get_vector_store
from backend.date_parser import get_date_parser
from backend.priority_classifier import get_priority_classifier
from backend.task_crud import get_task_crud
from backend.agent import get_task_agent

# Initialize FastAPI App
app = FastAPI(
    title="Task Management Agent API",
    description="Vector database powered Task Management Agent for Workshop Preparation",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root directory & Frontend paths
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Helper models for tool testing
class DateParseRequest(BaseModel):
    text: str
    context: Optional[str] = ""

class PriorityClassifyRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    due_date: Optional[str] = ""
    category: Optional[str] = "General"

class NoteSearchRequest(BaseModel):
    query: str
    n_results: Optional[int] = 4

# ==================== Health & Info Endpoints ====================
@app.get("/api/health")
def health_check():
    crud = get_task_crud()
    vstore = get_vector_store()
    stats = crud.get_stats()
    note_count = len(vstore.list_all_notes())

    return {
        "status": "healthy",
        "vector_database": "ChromaDB",
        "collection": CHROMA_COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "notes_count": note_count,
        "tasks_count": stats["total"],
        "pending_tasks": stats["pending"],
        "completed_tasks": stats["completed"]
    }

# ==================== Agent Endpoints ====================
@app.post("/api/chat", response_model=AgentChatResponse)
def chat_with_agent(payload: AgentChatRequest):
    """Processes user chat input through the Task Management Agent."""
    agent = get_task_agent()
    response = agent.process_request(
        user_message=payload.message,
        user_confirmed=payload.user_confirmed,
        confirmed_tasks=payload.confirmed_tasks
    )
    return response

@app.post("/api/agent/confirm-tasks")
def confirm_tasks(payload: ConfirmationRequest):
    """Explicit endpoint to confirm and commit a batch of proposed tasks."""
    agent = get_task_agent()
    response = agent.confirm_and_create_tasks(payload.tasks_to_create)
    return response

# ==================== Task CRUD API Endpoints ====================
@app.get("/api/tasks", response_model=List[Task])
def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    crud = get_task_crud()
    return crud.list_tasks(status=status, priority=priority, category=category, search=search)

@app.post("/api/tasks", response_model=Task)
def create_task(task_in: TaskCreate):
    crud = get_task_crud()
    # If priority reason is missing, run classifier
    if not task_in.priority_reason:
        classifier = get_priority_classifier()
        p_res = classifier.classify(task_in.title, task_in.description, task_in.due_date, task_in.category)
        task_in.priority = p_res["priority"]
        task_in.priority_reason = p_res["reason"]

    # If due_date needs formatting
    if task_in.due_date and not any(c in task_in.due_date for c in [",", "-"]):
        parser = get_date_parser()
        d_res = parser.parse(task_in.due_date, task_in.description)
        task_in.due_date = d_res["formatted"]

    return crud.create_task(task_in)

@app.get("/api/tasks/stats")
def get_task_stats():
    crud = get_task_crud()
    return crud.get_stats()

@app.get("/api/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    crud = get_task_crud()
    task = crud.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

@app.put("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: str, updates: TaskUpdate):
    crud = get_task_crud()
    updated = crud.update_task(task_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return updated

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    crud = get_task_crud()
    success = crud.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {"success": True, "id": task_id}

@app.post("/api/tasks/{task_id}/toggle", response_model=Task)
def toggle_task_status(task_id: str):
    crud = get_task_crud()
    updated = crud.toggle_status(task_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return updated

@app.delete("/api/tasks/actions/clear-all")
def clear_all_tasks():
    crud = get_task_crud()
    crud.clear_all()
    return {"success": True, "message": "All tasks cleared"}

# ==================== ChromaDB Project Notes Endpoints ====================
@app.get("/api/notes", response_model=List[ProjectNote])
def get_project_notes():
    vstore = get_vector_store()
    return vstore.list_all_notes()

@app.post("/api/notes", response_model=ProjectNote)
def add_project_note(note_in: ProjectNoteCreate):
    vstore = get_vector_store()
    return vstore.add_note(note_in)

@app.delete("/api/notes/{note_id}")
def delete_project_note(note_id: str):
    vstore = get_vector_store()
    success = vstore.delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return {"success": True, "id": note_id}

@app.post("/api/notes/search", response_model=List[ProjectNote])
def search_project_notes(payload: NoteSearchRequest):
    vstore = get_vector_store()
    return vstore.search_notes(payload.query, n_results=payload.n_results)

# ==================== Tool Testing Sandbox Endpoints ====================
@app.post("/api/tools/parse-date")
def test_parse_date(payload: DateParseRequest):
    parser = get_date_parser()
    return parser.parse(payload.text, context_hint=payload.context or "")

@app.post("/api/tools/classify-priority")
def test_classify_priority(payload: PriorityClassifyRequest):
    classifier = get_priority_classifier()
    return classifier.classify(
        title=payload.title,
        description=payload.description or "",
        due_date_str=payload.due_date or "",
        category=payload.category or "General"
    )

# ==================== Static Frontend Serving ====================
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{catchall:path}")
    def serve_frontend_spa(catchall: str):
        target = FRONTEND_DIR / catchall
        if target.exists() and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
