from pydantic import BaseModel, Field
from typing import Optional


# ===== Chat =====
class ChatRequest(BaseModel):
    prompt: str
    conversation_id: Optional[int] = None
    tool_hint: Optional[str] = None  # 用户手动选择的工具名称


class SourceCitation(BaseModel):
    rank: int
    source: str
    page: Optional[int] = None
    section_path: str = ""
    content_type: str = "text"
    chunk_type: str = "unknown"
    table_number: Optional[int] = None
    caption: str = ""
    preview: str = ""


class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    sources: list[SourceCitation] = Field(default_factory=list)


# ===== Conversation =====
class ConversationCreate(BaseModel):
    title: str = "New Chat"


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: str


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: str


# ===== Knowledge =====
class KnowledgeUploadResponse(BaseModel):
    filename: str
    chunks: int
    message: str


class KnowledgeDocOut(BaseModel):
    filename: str
    chunks: int


class KnowledgeStats(BaseModel):
    total_chunks: int
    embedding_model: str = ""
    embedding_collection: str = ""
