import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, init_db
from app.seed_data import seed_database
import app.crud as crud
from app.engine.retrieval import retrieve_relevant_memories, tokenize, score_memory
from app.engine.prompt_builder import build_persona_system_prompt

def test_full_pipeline():
    print("========================================")
    print("🔍 Testing Beyond Distance MVP Backend")
    print("========================================")

    init_db()
    db = next(get_db())
    seed_database(db)

    with TestClient(app) as client:
        # 2. Test Home Page
        response = client.get("/")
        assert response.status_code == 200, f"Home page failed: {response.status_code}"
        print("✅ Home Page (SPA) served successfully")

        # 3. Test Personas API
        response = client.get("/api/personas")
        assert response.status_code == 200, f"List personas failed: {response.status_code}"
        personas = response.json()
        assert len(personas) >= 2, f"Expected at least 2 seed personas, found {len(personas)}"
        print(f"✅ Personas API: Found {len(personas)} personas ({', '.join(p['name'] for p in personas)})")

        arthur = next(p for p in personas if "Arthur" in p["name"])
        
        # 4. Test Memories API for Arthur
        response = client.get(f"/api/personas/{arthur['id']}/memories")
        assert response.status_code == 200
        memories = response.json()
        assert len(memories) >= 5, f"Expected Arthur to have at least 5 memories, found {len(memories)}"
        print(f"✅ Memories API: Found {len(memories)} memories for {arthur['name']}")

        # 5. Test Memory Retrieval Relevance Engine
        db_memories = crud.get_memories(db, arthur['id'])
        
        # Query about fishing / lake
        fishing_query = "Remember that lake morning when we went fishing?"
        top_fishing = retrieve_relevant_memories(db_memories, fishing_query, top_k=2)
        assert len(top_fishing) > 0
        top_mem = top_fishing[0][0]
        print(f"🔍 Query: '{fishing_query}' -> Evoked Memory: '{top_mem.title}' (Score: {top_fishing[0][1]:.2f})")
        assert "fishing" in top_mem.title.lower() or "lake" in top_mem.title.lower()
        print("✅ Contextual Memory Retrieval: Fishing query matched accurately")

        # Query about coffee / jazz
        coffee_query = "What was your morning coffee routine?"
        top_coffee = retrieve_relevant_memories(db_memories, coffee_query, top_k=2)
        assert len(top_coffee) > 0
        top_coffee_mem = top_coffee[0][0]
        print(f"🔍 Query: '{coffee_query}' -> Evoked Memory: '{top_coffee_mem.title}' (Score: {top_coffee[0][1]:.2f})")
        assert "coffee" in top_coffee_mem.title.lower() or "jazz" in top_coffee_mem.title.lower()
        print("✅ Contextual Memory Retrieval: Coffee query matched accurately")

        # 6. Test Persona Prompt Builder
        db_arthur = crud.get_persona(db, arthur['id'])
        prompt = build_persona_system_prompt(db_arthur, top_fishing)
        assert "Grandpa Arthur" in prompt
        assert "Lake Sebago" in prompt
        assert "Measure twice" in prompt
        print("✅ Persona Prompt Builder: Synthesized comprehensive system instructions")

        # 7. Test Chat API
        chat_payload = {
            "persona_id": arthur['id'],
            "message": "Grandpa, I'm feeling really stressed about work and deadlines today. What should I do?"
        }
        chat_resp = client.post("/api/chat", json=chat_payload)
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert "persona_message" in chat_data
        assert "evoked_memories" in chat_data
        assert len(chat_data["persona_message"]["content"]) > 20
        print("✅ Chat API response generated successfully:")
        print(f"   👤 User: {chat_payload['message']}")
        print(f"   👴🏼 Persona: {chat_data['persona_message']['content'][:120]}...")
        print(f"   ✨ Evoked: {[m['title'] for m in chat_data['evoked_memories']]}")

        # 8. Test Adding a New Memory
        new_mem_payload = {
            "title": "Making Apple Cider in Autumn",
            "category": "story",
            "content": "Pressing fresh McIntosh apples in the wooden cider press every October.",
            "tags": ["autumn", "apples", "cider"],
            "importance": 4,
            "date_reference": "October 2019"
        }
        create_mem_resp = client.post(f"/api/personas/{arthur['id']}/memories", json=new_mem_payload)
        assert create_mem_resp.status_code == 200
        created_mem = create_mem_resp.json()
        assert created_mem["title"] == "Making Apple Cider in Autumn"
        print("✅ Add Memory API: Created new memory successfully")

        # 9. Test Bulk Text Memory Import
        bulk_text = """Sunday Morning Pancakes
We always made blueberry pancakes on Sunday mornings with real maple syrup.

The Golden Watch Gift
Given to you on your 18th birthday, engraved with 'Time is a gift'."""
        bulk_resp = client.post(f"/api/personas/{arthur['id']}/memories/bulk", json={"raw_text": bulk_text})
        assert bulk_resp.status_code == 200
        bulk_items = bulk_resp.json()
        assert len(bulk_items) == 2
        print(f"✅ Bulk Ingestion: Ingested {len(bulk_items)} memories from unstructured text")

        # Clean up test added memory
        client.delete(f"/api/memories/{created_mem['id']}")
        for b in bulk_items:
            client.delete(f"/api/memories/{b['id']}")

    print("========================================")
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    test_full_pipeline()
