import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import Persona, Memory, Conversation, Message, Setting
from app.schemas import PersonaCreate, PersonaUpdate, MemoryCreate, MemoryUpdate, BulkMemoryItem

# --- PERSONAS ---
def get_personas(db: Session) -> List[Persona]:
    return db.query(Persona).order_by(desc(Persona.updated_at)).all()

def get_persona(db: Session, persona_id: str) -> Optional[Persona]:
    return db.query(Persona).filter(Persona.id == persona_id).first()

def create_persona(db: Session, persona_in: PersonaCreate) -> Persona:
    persona = Persona(
        name=persona_in.name,
        avatar=persona_in.avatar,
        relationship=persona_in.relationship,
        bio=persona_in.bio,
        tone_style=persona_in.tone_style,
        catchphrases=json.dumps(persona_in.catchphrases),
        empathy_level=persona_in.empathy_level,
        humor_level=persona_in.humor_level,
        nostalgia_level=persona_in.nostalgia_level,
        color=persona_in.color,
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona

def update_persona(db: Session, persona_id: str, persona_in: PersonaUpdate) -> Optional[Persona]:
    persona = get_persona(db, persona_id)
    if not persona:
        return None
    
    update_data = persona_in.model_dump(exclude_unset=True)
    if "catchphrases" in update_data and update_data["catchphrases"] is not None:
        update_data["catchphrases"] = json.dumps(update_data["catchphrases"])

    for field, value in update_data.items():
        setattr(persona, field, value)
        
    db.commit()
    db.refresh(persona)
    return persona

def delete_persona(db: Session, persona_id: str) -> bool:
    persona = get_persona(db, persona_id)
    if not persona:
        return False
    db.delete(persona)
    db.commit()
    return True


# --- MEMORIES ---
def get_memories(db: Session, persona_id: str, category: Optional[str] = None, search: Optional[str] = None) -> List[Memory]:
    query = db.query(Memory).filter(Memory.persona_id == persona_id)
    if category and category != "all":
        query = query.filter(Memory.category == category)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Memory.title.ilike(search_pattern)) | 
            (Memory.content.ilike(search_pattern)) | 
            (Memory.tags.ilike(search_pattern))
        )
    return query.order_by(desc(Memory.importance), desc(Memory.created_at)).all()

def get_memory(db: Session, memory_id: str) -> Optional[Memory]:
    return db.query(Memory).filter(Memory.id == memory_id).first()

def get_memories_by_ids(db: Session, memory_ids: List[str]) -> List[Memory]:
    if not memory_ids:
        return []
    return db.query(Memory).filter(Memory.id.in_(memory_ids)).all()

def create_memory(db: Session, persona_id: str, memory_in: MemoryCreate) -> Memory:
    memory = Memory(
        persona_id=persona_id,
        title=memory_in.title,
        category=memory_in.category,
        content=memory_in.content,
        tags=json.dumps(memory_in.tags),
        importance=memory_in.importance,
        date_reference=memory_in.date_reference or "",
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory

def bulk_create_memories(db: Session, persona_id: str, memories_in: List[BulkMemoryItem]) -> List[Memory]:
    created = []
    for item in memories_in:
        memory = Memory(
            persona_id=persona_id,
            title=item.title,
            category=item.category,
            content=item.content,
            tags=json.dumps(item.tags),
            importance=item.importance,
            date_reference=item.date_reference or "",
        )
        db.add(memory)
        created.append(memory)
    db.commit()
    for m in created:
        db.refresh(m)
    return created

def update_memory(db: Session, memory_id: str, memory_in: MemoryUpdate) -> Optional[Memory]:
    memory = get_memory(db, memory_id)
    if not memory:
        return None
    
    update_data = memory_in.model_dump(exclude_unset=True)
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = json.dumps(update_data["tags"])
        
    for field, value in update_data.items():
        setattr(memory, field, value)
        
    db.commit()
    db.refresh(memory)
    return memory

def delete_memory(db: Session, memory_id: str) -> bool:
    memory = get_memory(db, memory_id)
    if not memory:
        return False
    db.delete(memory)
    db.commit()
    return True


# --- CONVERSATIONS & MESSAGES ---
def get_conversations(db: Session, persona_id: str) -> List[Conversation]:
    return db.query(Conversation).filter(
        Conversation.persona_id == persona_id
    ).order_by(desc(Conversation.updated_at)).all()

def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()

def create_conversation(db: Session, persona_id: str, title: str = "New Conversation") -> Conversation:
    conversation = Conversation(
        persona_id=persona_id,
        title=title
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def delete_conversation(db: Session, conversation_id: str) -> bool:
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        return False
    db.delete(conversation)
    db.commit()
    return True

def create_message(
    db: Session, 
    conversation_id: str, 
    sender: str, 
    content: str, 
    evoked_memory_ids: List[str] = None
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        sender=sender,
        content=content,
        evoked_memory_ids=json.dumps(evoked_memory_ids or []),
    )
    db.add(message)
    
    # Update conversation's updated_at
    conversation = get_conversation(db, conversation_id)
    if conversation:
        from datetime import datetime
        conversation.updated_at = datetime.utcnow()
        if conversation.title == "New Conversation" and sender == "user":
            # Auto-title conversation with snippet of first user message
            snippet = content.strip().split("\n")[0][:40]
            if len(content) > 40:
                snippet += "..."
            conversation.title = snippet
            
    db.commit()
    db.refresh(message)
    return message

def get_conversation_messages(db: Session, conversation_id: str) -> List[Message]:
    return db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()


# --- SETTINGS ---
def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default

def set_setting(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()

def get_all_settings(db: Session) -> dict:
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}
