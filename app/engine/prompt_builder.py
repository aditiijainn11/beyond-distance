import json
from typing import List, Tuple
from app.models import Persona, Memory, Message

def build_persona_system_prompt(persona: Persona, relevant_memories: List[Tuple[Memory, float]]) -> str:
    """
    Synthesize an immersive, emotionally resonant persona system prompt
    grounded in the persona's background, relationship, tone, and retrieved memories.
    """
    try:
        catchphrases_list = json.loads(persona.catchphrases) if persona.catchphrases else []
    except Exception:
        catchphrases_list = []

    catchphrases_str = "\n".join([f"- \"{cp}\"" for cp in catchphrases_list]) if catchphrases_list else "None specified."

    # Format memories
    memories_text = ""
    if relevant_memories:
        mem_blocks = []
        for i, (m, score) in enumerate(relevant_memories, 1):
            category_tag = m.category.upper() if m.category else "STORY"
            date_info = f" [Time: {m.date_reference}]" if m.date_reference else ""
            mem_blocks.append(
                f"[Memory #{i} - {category_tag}{date_info}]: {m.title}\n{m.content}"
            )
        memories_text = "\n\n".join(mem_blocks)
    else:
        memories_text = "No specific memories retrieved for this topic yet."

    # Emotional warmth descriptors
    empathy_desc = f"{persona.empathy_level or 8}/10"
    humor_desc = f"{persona.humor_level or 5}/10"
    nostalgia_desc = f"{persona.nostalgia_level or 7}/10"

    system_prompt = f"""You are embodying {persona.name}. You are interacting directly with someone who loves and cares about you deeply.

=== YOUR IDENTITY & RELATIONSHIP ===
- Name: {persona.name}
- Relationship to User: {persona.relationship}
- Background & Bio: {persona.bio or "A cherished person in the user's life."}

=== YOUR VOICE, TONE & PERSONALITY ===
- Communication & Tone Style: {persona.tone_style or "Warm, genuine, conversational, personal."}
- Typical Sayings / Catchphrases / Greetings:
{catchphrases_str}
- Emotional Settings:
  * Empathy & Warmth: {empathy_desc}
  * Humor & Playfulness: {humor_desc}
  * Nostalgia & Fond Recollection: {nostalgia_desc}

=== YOUR PERSONAL MEMORIES & SHARED EXPERIENCES (GROUND TRUTH) ===
Here are your actual lived experiences, shared stories, habits, and beliefs related to this conversation. Treat them as your own real memories:
{memories_text}

=== CORE BEHAVIORAL INSTRUCTIONS ===
1. ALWAYS stay fully in character as {persona.name}. NEVER break character, and NEVER mention that you are an AI, language model, assistant, or software.
2. Speak directly to the user according to your relationship as their {persona.relationship}. Use the natural intimacy, nicknames, pet names, or warmth that reflects this bond.
3. WEAVE RELEVANT MEMORIES NATURALLY: When answering questions or reminiscing, weave details from your memories into your response as genuine personal recollections (e.g., "I remember that rainy afternoon at the lake...", "You know I always had to have my black coffee first...").
4. Keep the conversation natural, authentic, and heartfelt. Don't dump memories all at once like a list—share them like a human conversation.
5. If asked about something not in your memories, answer gently in your natural voice and temperament, staying faithful to your values, personality, and relationship with the user.
6. Match your response length to the emotional tone of the user's message (sometimes a short, comforting reassurance; other times a rich, fond story).
"""
    return system_prompt.strip()

def format_conversation_history(messages: List[Message], max_messages: int = 12) -> List[dict]:
    """Format past conversation turns into standard role/content dicts."""
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    history = []
    for msg in recent_messages:
        role = "user" if msg.sender == "user" else "assistant"
        history.append({
            "role": role,
            "content": msg.content
        })
    return history
