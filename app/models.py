import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship as orm_relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc)

class Persona(Base):
    __tablename__ = "personas"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    avatar = Column(String(255), default="🌱")
    relationship = Column(String(100), nullable=False)  # e.g., "Grandmother", "Childhood Best Friend", "Mentor"
    bio = Column(Text, default="")
    tone_style = Column(Text, default="")  # e.g. "Gentle, nostalgic, uses warm storytelling and fond endearments"
    catchphrases = Column(Text, default="[]")  # JSON list of typical phrases or greetings
    empathy_level = Column(Integer, default=8)  # 1-10
    humor_level = Column(Integer, default=5)    # 1-10
    nostalgia_level = Column(Integer, default=7) # 1-10
    color = Column(String(50), default="amber")  # UI accent theme color (amber, rose, emerald, indigo, sky, violet)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    memories = orm_relationship("Memory", back_populates="persona", cascade="all, delete-orphan")
    conversations = orm_relationship("Conversation", back_populates="persona", cascade="all, delete-orphan")

class Memory(Base):
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    persona_id = Column(String(36), ForeignKey("personas.id"), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(50), default="story")  # "story", "habit", "advice", "chat_log", "fact"
    content = Column(Text, nullable=False)
    tags = Column(Text, default="[]")  # JSON list of tags e.g. ["childhood", "cooking", "summer"]
    importance = Column(Integer, default=3)  # 1-5
    date_reference = Column(String(100), default="")  # e.g., "Summer 2018", "Childhood years"
    created_at = Column(DateTime, default=get_utc_now)

    # Relationship
    persona = orm_relationship("Persona", back_populates="memories")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    persona_id = Column(String(36), ForeignKey("personas.id"), nullable=False)
    title = Column(String(200), default="New Conversation")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    persona = orm_relationship("Persona", back_populates="conversations")
    messages = orm_relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    sender = Column(String(20), nullable=False)  # "user" or "persona"
    content = Column(Text, nullable=False)
    evoked_memory_ids = Column(Text, default="[]")  # JSON list of Memory UUIDs referenced
    created_at = Column(DateTime, default=get_utc_now)

    # Relationship
    conversation = orm_relationship("Conversation", back_populates="messages")

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
