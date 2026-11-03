from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ProjectNote(BaseModel):
    id: str
    title: str
    category: str = "General"
    tags: List[str] = Field(default_factory=list)
    content: str
    distance: Optional[float] = None  # Cosine distance from query in ChromaDB
    similarity: Optional[float] = None # 1 - distance

class ProjectNoteCreate(BaseModel):
    title: str
    category: str = "General"
    tags: List[str] = Field(default_factory=list)
    content: str

class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    due_date: str = ""
    priority: str = "Medium"  # Urgent, High, Medium, Low
    priority_reason: Optional[str] = None
    category: str = "General"
    status: str = "pending"   # pending, in_progress, completed
    tags: List[str] = Field(default_factory=list)
    source_notes: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    due_date: str = ""
    priority: str = "Medium"
    priority_reason: Optional[str] = None
    category: str = "General"
    status: str = "pending"
    tags: List[str] = Field(default_factory=list)
    source_notes: List[str] = Field(default_factory=list)

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    priority_reason: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    source_notes: Optional[List[str]] = None

class TaskProposalItem(BaseModel):
    temp_id: str
    title: str
    description: str = ""
    due_date: str = ""
    priority: str = "Medium"
    priority_reason: str = ""
    category: str = "General"
    tags: List[str] = Field(default_factory=list)
    source_notes: List[str] = Field(default_factory=list)
    approved: bool = True

class TaskProposal(BaseModel):
    proposal_id: str
    user_request: str
    summary: str
    retrieved_notes: List[ProjectNote] = Field(default_factory=list)
    proposed_tasks: List[TaskProposalItem] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class ConfirmationRequest(BaseModel):
    proposal_id: Optional[str] = None
    tasks_to_create: List[TaskProposalItem]

class AgentChatRequest(BaseModel):
    message: str
    user_confirmed: bool = False
    confirmed_tasks: Optional[List[TaskProposalItem]] = None

class AgentStep(BaseModel):
    name: str
    status: str = "success"
    details: str
    data: Optional[Any] = None

class AgentChatResponse(BaseModel):
    reply: str
    proposal: Optional[TaskProposal] = None
    created_tasks: Optional[List[Task]] = None
    steps: List[AgentStep] = Field(default_factory=list)
