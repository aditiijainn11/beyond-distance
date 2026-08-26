import json
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.config import BASE_DIR
from app.database import get_db, init_db, SessionLocal
from app.models import Persona, Memory, Conversation, Message
from app.seed_data import seed_database
from app.schemas import (
    PersonaCreate, PersonaUpdate, PersonaOut,
    MemoryCreate, MemoryUpdate, MemoryOut, BulkMemoryImportRequest,
    ConversationCreate, ConversationOut, MessageOut,
    ChatRequest, ChatResponse, SettingsUpdateRequest
)
import app.crud as crud
from app.engine.retrieval import retrieve_relevant_memories
from app.engine.prompt_builder import format_conversation_history
from app.engine.llm import generate_persona_response

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Beyond Distance",
    description="AI-Powered Personal Connection Space",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & Templates setup
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def serialize_persona(persona: Persona, db: Session) -> dict:
    try:
        catchphrases = json.loads(persona.catchphrases) if persona.catchphrases else []
    except Exception:
        catchphrases = []
    
    mem_count = db.query(Memory).filter(Memory.persona_id == persona.id).count()
    
    return {
        "id": persona.id,
        "name": persona.name,
        "avatar": persona.avatar,
        "relationship": persona.relationship,
        "bio": persona.bio,
        "tone_style": persona.tone_style,
        "catchphrases": catchphrases,
        "empathy_level": persona.empathy_level,
        "humor_level": persona.humor_level,
        "nostalgia_level": persona.nostalgia_level,
        "color": persona.color,
        "memory_count": mem_count,
        "created_at": persona.created_at,
        "updated_at": persona.updated_at,
    }

def serialize_memory(memory: Memory) -> dict:
    try:
        tags = json.loads(memory.tags) if memory.tags else []
    except Exception:
        tags = []
    return {
        "id": memory.id,
        "persona_id": memory.persona_id,
        "title": memory.title,
        "category": memory.category,
        "content": memory.content,
        "tags": tags,
        "importance": memory.importance,
        "date_reference": memory.date_reference,
        "created_at": memory.created_at,
    }

def serialize_message(msg: Message, db: Session) -> dict:
    try:
        evoked_ids = json.loads(msg.evoked_memory_ids) if msg.evoked_memory_ids else []
    except Exception:
        evoked_ids = []

    evoked_memories = []
    if evoked_ids:
        raw_memories = crud.get_memories_by_ids(db, evoked_ids)
        evoked_memories = [serialize_memory(m) for m in raw_memories]

    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender": msg.sender,
        "content": msg.content,
        "evoked_memory_ids": evoked_ids,
        "evoked_memories": evoked_memories,
        "created_at": msg.created_at,
    }

# ================= PAGES =================
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# ================= PERSONAS =================
@app.get("/api/personas")
def list_personas(db: Session = Depends(get_db)):
    personas = crud.get_personas(db)
    return [serialize_persona(p, db) for p in personas]

@app.get("/api/personas/{persona_id}")
def get_persona(persona_id: str, db: Session = Depends(get_db)):
    persona = crud.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return serialize_persona(persona, db)

@app.post("/api/personas")
def create_persona(persona_in: PersonaCreate, db: Session = Depends(get_db)):
    persona = crud.create_persona(db, persona_in)
    return serialize_persona(persona, db)

@app.put("/api/personas/{persona_id}")
def update_persona(persona_id: str, persona_in: PersonaUpdate, db: Session = Depends(get_db)):
    persona = crud.update_persona(db, persona_id, persona_in)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return serialize_persona(persona, db)

@app.delete("/api/personas/{persona_id}")
def delete_persona(persona_id: str, db: Session = Depends(get_db)):
    success = crud.delete_persona(db, persona_id)
    if not success:
        raise HTTPException(status_code=404, detail="Persona not found")
    return {"status": "success", "message": "Persona deleted"}

# ================= MEMORIES =================
@app.get("/api/personas/{persona_id}/memories")
def list_memories(
    persona_id: str,
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    memories = crud.get_memories(db, persona_id, category=category, search=search)
    return [serialize_memory(m) for m in memories]

@app.get("/api/memories/{memory_id}")
def get_memory(memory_id: str, db: Session = Depends(get_db)):
    memory = crud.get_memory(db, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return serialize_memory(memory)

@app.post("/api/personas/{persona_id}/memories")
def create_memory(persona_id: str, memory_in: MemoryCreate, db: Session = Depends(get_db)):
    persona = crud.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    memory = crud.create_memory(db, persona_id, memory_in)
    return serialize_memory(memory)

@app.post("/api/personas/{persona_id}/memories/bulk")
def bulk_import_memories(persona_id: str, request: BulkMemoryImportRequest, db: Session = Depends(get_db)):
    persona = crud.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    created_memories = []

    # If explicit items provided
    if request.memories:
        created_memories = crud.bulk_create_memories(db, persona_id, request.memories)
    
    # If raw text provided, split into paragraphs/sections
    elif request.raw_text:
        raw_sections = [s.strip() for s in request.raw_text.split("\n\n") if s.strip()]
        bulk_items = []
        for idx, sec in enumerate(raw_sections, 1):
            lines = sec.split("\n")
            first_line = lines[0].strip("#- *")[:60]
            title = first_line if first_line else f"Memory Note #{idx}"
            content = sec
            
            # Simple category detection
            lower_sec = sec.lower()
            category = "story"
            if any(k in lower_sec for k in ["habit", "always", "routine", "every day", "drank", "wore"]):
                category = "habit"
            elif any(k in lower_sec for k in ["advice", "taught me", "lesson", "believed", "said to me"]):
                category = "advice"
            elif any(k in lower_sec for k in ["text", "message", "letter", "email", "dear", "wrote"]):
                category = "chat_log"
            elif any(k in lower_sec for k in ["born", "favorite", "color", "birthday", "lived at", "fact"]):
                category = "fact"

            bulk_items.append(crud.BulkMemoryItem(
                title=title,
                category=category,
                content=content,
                tags=["imported"],
                importance=3,
                date_reference=""
            ))
        created_memories = crud.bulk_create_memories(db, persona_id, bulk_items)

    return [serialize_memory(m) for m in created_memories]

@app.put("/api/memories/{memory_id}")
def update_memory(memory_id: str, memory_in: MemoryUpdate, db: Session = Depends(get_db)):
    memory = crud.update_memory(db, memory_id, memory_in)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return serialize_memory(memory)

@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    success = crud.delete_memory(db, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "success", "message": "Memory deleted"}

# ================= CONVERSATIONS =================
@app.get("/api/personas/{persona_id}/conversations")
def list_conversations(persona_id: str, db: Session = Depends(get_db)):
    convs = crud.get_conversations(db, persona_id)
    result = []
    for c in convs:
        msgs = crud.get_conversation_messages(db, c.id)
        last_msg = msgs[-1].content[:60] if msgs else "No messages"
        result.append({
            "id": c.id,
            "persona_id": c.persona_id,
            "title": c.title,
            "message_count": len(msgs),
            "last_message": last_msg,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        })
    return result

@app.post("/api/personas/{persona_id}/conversations")
def create_conversation(persona_id: str, conv_in: ConversationCreate, db: Session = Depends(get_db)):
    persona = crud.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    conv = crud.create_conversation(db, persona_id, conv_in.title or "New Conversation")
    return {
        "id": conv.id,
        "persona_id": conv.persona_id,
        "title": conv.title,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": []
    }

@app.get("/api/conversations/{conversation_id}")
def get_conversation_detail(conversation_id: str, db: Session = Depends(get_db)):
    conv = crud.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = crud.get_conversation_messages(db, conversation_id)
    return {
        "id": conv.id,
        "persona_id": conv.persona_id,
        "title": conv.title,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": [serialize_message(m, db) for m in messages]
    }

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    success = crud.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": "Conversation deleted"}

# ================= CHAT ORCHESTRATION =================
@app.post("/api/chat")
async def chat_with_persona(req: ChatRequest, db: Session = Depends(get_db)):
    persona = crud.get_persona(db, req.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Get or create conversation
    conversation_id = req.conversation_id
    if not conversation_id:
        conv = crud.create_conversation(db, req.persona_id, "New Conversation")
        conversation_id = conv.id
    else:
        conv = crud.get_conversation(db, conversation_id)
        if not conv:
            conv = crud.create_conversation(db, req.persona_id, "New Conversation")
            conversation_id = conv.id

    # 1. Store user message
    user_msg = crud.create_message(db, conversation_id, "user", req.message)

    # 2. Retrieve relevant memories for the persona
    all_memories = crud.get_memories(db, req.persona_id)
    relevant_memories = retrieve_relevant_memories(all_memories, req.message, top_k=4)
    evoked_ids = [m.id for m, score in relevant_memories]

    # 3. Format history
    past_messages = crud.get_conversation_messages(db, conversation_id)
    history = format_conversation_history(past_messages[:-1])  # exclude the newly added user message

    # 4. Fetch settings
    settings = crud.get_all_settings(db)

    # 5. Generate persona response
    try:
        response_text = await generate_persona_response(
            persona=persona,
            relevant_memories=relevant_memories,
            history=history,
            user_message=req.message,
            settings=settings
        )
    except Exception as e:
        response_text = f"[Connection error: {str(e)}]. Let me reconnect with you in just a moment."

    # 6. Store persona message
    persona_msg = crud.create_message(
        db=db,
        conversation_id=conversation_id,
        sender="persona",
        content=response_text,
        evoked_memory_ids=evoked_ids
    )

    evoked_memories_data = [serialize_memory(m) for m, score in relevant_memories]

    return {
        "conversation_id": conversation_id,
        "user_message": serialize_message(user_msg, db),
        "persona_message": serialize_message(persona_msg, db),
        "evoked_memories": evoked_memories_data
    }

# ================= SETTINGS =================
@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = crud.get_all_settings(db)
    
    # Mask API keys for security in UI output
    masked = {}
    for k, v in settings.items():
        if "key" in k.lower() and len(v) > 8:
            masked[k] = v[:4] + "..." + v[-4:]
        else:
            masked[k] = v
    return {
        "settings": masked,
        "raw_keys_present": {
            "gemini": bool(settings.get("gemini_api_key")),
            "openai": bool(settings.get("openai_api_key")),
            "groq": bool(settings.get("groq_api_key")),
        }
    }

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest, db: Session = Depends(get_db)):
    for item in req.settings:
        if item.value:  # Only update non-empty
            crud.set_setting(db, item.key, item.value.strip())
    return {"status": "success", "message": "Settings updated"}
