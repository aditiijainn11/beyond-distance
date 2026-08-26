from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field

# Memory schemas
class MemoryBase(BaseModel):
    title: str
    category: str = "story"  # "story", "habit", "advice", "chat_log", "fact"
    content: str
    tags: List[str] = []
    importance: int = Field(default=3, ge=1, le=5)
    date_reference: Optional[str] = ""

class MemoryCreate(MemoryBase):
    pass

class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    importance: Optional[int] = None
    date_reference: Optional[str] = None

class MemoryOut(MemoryBase):
    id: str
    persona_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class BulkMemoryItem(BaseModel):
    title: str
    category: str = "story"
    content: str
    tags: List[str] = []
    importance: int = 3
    date_reference: str = ""

class BulkMemoryImportRequest(BaseModel):
    raw_text: Optional[str] = None
    memories: Optional[List[BulkMemoryItem]] = None

# Persona schemas
class PersonaBase(BaseModel):
    name: str
    avatar: str = "🌱"
    relationship: str
    bio: str = ""
    tone_style: str = ""
    catchphrases: List[str] = []
    empathy_level: int = Field(default=8, ge=1, le=10)
    humor_level: int = Field(default=5, ge=1, le=10)
    nostalgia_level: int = Field(default=7, ge=1, le=10)
    color: str = "amber"

class PersonaCreate(PersonaBase):
    pass

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    relationship: Optional[str] = None
    bio: Optional[str] = None
    tone_style: Optional[str] = None
    catchphrases: Optional[List[str]] = None
    empathy_level: Optional[int] = None
    humor_level: Optional[int] = None
    nostalgia_level: Optional[int] = None
    color: Optional[str] = None

class PersonaOut(PersonaBase):
    id: str
    created_at: datetime
    updated_at: datetime
    memory_count: Optional[int] = 0

    class Config:
        from_attributes = True

# Conversation & Message schemas
class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    evoked_memory_ids: List[str] = []
    evoked_memories: Optional[List[MemoryOut]] = []
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    persona_id: str
    title: Optional[str] = "New Conversation"

class ConversationOut(BaseModel):
    id: str
    persona_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    persona_id: str
    message: str

class ChatResponse(BaseModel):
    conversation_id: str
    user_message: MessageOut
    persona_message: MessageOut
    evoked_memories: List[MemoryOut]

class SettingItem(BaseModel):
    key: str
    value: str

class SettingsUpdateRequest(BaseModel):
    settings: List[SettingItem]
