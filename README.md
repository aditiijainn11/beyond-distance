# Beyond Distance ✦

> An AI-powered personal connection space to preserve the memories, stories, conversations, and personality of people who matter to you—bridging emotional distance so you can reconnect anytime.

---

## 🌟 Overview & Philosophy

**Beyond Distance** is designed to preserve the essence and voice of cherished people—family members, childhood best friends, mentors, or lost loved ones. By entering text memories (stories, daily habits, life advice, letters, or past chat logs), the AI embodies their personality, relational warmth, and shared history, answering in their authentic conversational voice grounded strictly in those memories.

---

## ✨ Features (MVP)

- **🌱 Persona Studio**:
  - Create and manage distinct persona profiles (e.g. *Grandpa Arthur*, *Maya - Childhood Best Friend*).
  - Define relationship dynamics, tone of voice, typical catchphrases, and emotional warmth sliders (*Empathy*, *Humor*, *Nostalgia*).
- **📖 Rich Text Memory Vault**:
  - Multi-category memory storage:
    - **Stories & Experiences** (e.g., lake fishing trips, road trips)
    - **Habits & Quirks** (e.g., morning coffee rituals, margin doodles)
    - **Advice & Beliefs** (e.g., life philosophies, encouragement)
    - **Chat Logs & Letters** (e.g., old farewell notes, audio transcripts)
    - **Quick Facts** (e.g., favorite foods, birthday milestones)
  - Keyword & tag searching, category filtering, importance ranking (1–5 stars).
  - **Bulk Text Importer**: Paste unformatted letters or notes to auto-generate structured memory cards.
- **✨ Contextual Memory Retrieval Brain**:
  - BM25 & keyword frequency retrieval ranking matching conversation topics to the most relevant memories.
  - Persona Prompt Synthesizer creating high-fidelity system prompts that preserve voice continuity without breaking character.
- **💬 Heartfelt Connection Chat**:
  - **Evoked Memory Badges**: Live indicators below responses showing which memories were referenced.
  - **Memory Inspection Drawer**: Click any evoked memory badge to inspect the underlying memory context.
  - **Reflection Starters**: Contextual conversation prompts for reminiscing and seeking advice.
  - In-chat memory addition: Quickly preserve new memories on the fly.
  - Persistent chat history in local SQLite.
- **⚡ AI Provider Flexibility**:
  - Supports **Google Gemini API** (`gemini-2.5-flash`), **OpenAI API** (`gpt-4o-mini`), and **Groq**.
  - Includes a **built-in offline simulation mode** so the application works out of the box even without an API key!

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
```bash
./run.sh
```
or
```bash
python3 -m uvicorn app.main:app --port 8000 --reload
```

### 3. Open in Browser
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📂 Project Structure

```
beyond-distance/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI server, REST API & static routing
│   ├── config.py                # Database paths & default configurations
│   ├── database.py              # SQLite engine & session management
│   ├── models.py                # SQLAlchemy ORM models (Persona, Memory, Conversation, Message)
│   ├── schemas.py               # Pydantic validation schemas
│   ├── crud.py                  # Database CRUD queries
│   ├── seed_data.py             # Preloaded sample personas and rich memories
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── retrieval.py         # Memory search & BM25 relevance scoring
│   │   ├── prompt_builder.py    # Persona prompt synthesizer
│   │   └── llm.py               # LLM connectors (Gemini, OpenAI, Groq, offline fallback)
│   └── templates/
│       └── index.html           # Single Page Application (Chat, Memory Vault, Studio)
├── static/
│   ├── css/
│   │   └── style.css            # Ambient glow, typography & animations
│   └── js/
│       └── app.js               # Reactive client-side application logic
├── test_app.py                  # Automated backend & engine verification suite
├── requirements.txt             # Python dependencies
├── run.sh                       # Quick launch script
└── README.md                    # Documentation
```

---

## ⚙️ Configuring AI Models & API Keys

1. Click the **⚙️ Settings** icon in the sidebar or top header.
2. Select your provider (**Google Gemini**, **OpenAI**, or **Groq**).
3. Paste your API key (stored securely in local SQLite).
4. Save and start chatting!

---

## 🧪 Running Automated Tests

```bash
python3 test_app.py
```
All tests verify database integrity, memory relevance scoring, persona prompt synthesis, chat generation, and bulk text ingestion.