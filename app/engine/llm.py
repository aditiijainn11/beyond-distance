import os
import json
import random
import httpx
from typing import List, Optional, Tuple
from app.models import Persona, Memory
from app.engine.prompt_builder import build_persona_system_prompt, format_conversation_history

async def generate_gemini_response(
    api_key: str, 
    model_name: str, 
    system_prompt: str, 
    history: List[dict], 
    user_message: str
) -> str:
    """Generate response using Google Gemini API via official google-genai or httpx."""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        
        # Build contents from history
        contents = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=turn["content"])]
            ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        ))

        # Use gemini-2.5-flash or specified model
        target_model = model_name or "gemini-2.5-flash"
        if not target_model.startswith("gemini"):
            target_model = "gemini-2.5-flash"

        response = client.models.generate_content(
            model=target_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.75,
                max_output_tokens=1000,
            )
        )
        return response.text.strip()
    except Exception as e:
        # Fallback to direct REST API if SDK has any interface mismatch
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name or 'gemini-2.5-flash'}:generateContent?key={api_key}"
        contents = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": turn["content"]}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.75,
                "maxOutputTokens": 1000
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip()
            raise RuntimeError(f"Gemini API returned unexpected format: {data}")

async def generate_openai_response(
    api_key: str, 
    model_name: str, 
    system_prompt: str, 
    history: List[dict], 
    user_message: str,
    base_url: str = "https://api.openai.com/v1"
) -> str:
    """Generate response using OpenAI-compatible API."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model_name or "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.75,
        "max_tokens": 1000
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

async def generate_groq_response(
    api_key: str, 
    model_name: str, 
    system_prompt: str, 
    history: List[dict], 
    user_message: str
) -> str:
    """Generate response using Groq API."""
    return await generate_openai_response(
        api_key=api_key,
        model_name=model_name or "llama-3.3-70b-versatile",
        system_prompt=system_prompt,
        history=history,
        user_message=user_message,
        base_url="https://api.groq.com/openai/v1"
    )

def generate_offline_fallback(
    persona: Persona, 
    relevant_memories: List[Tuple[Memory, float]], 
    user_message: str
) -> str:
    """
    Rich, empathetic offline simulator that synthesizes authentic responses
    by referencing the persona's memories, catchphrases, and tone.
    """
    try:
        catchphrases = json.loads(persona.catchphrases) if persona.catchphrases else []
    except Exception:
        catchphrases = []

    greeting = ""
    if catchphrases and random.random() < 0.6:
        greeting = random.choice(catchphrases) + " "

    memories_to_weave = [m for m, score in relevant_memories if m.content]
    
    if memories_to_weave:
        chosen_memory = memories_to_weave[0]
        category = chosen_memory.category
        
        if category == "story":
            templates = [
                f"{greeting}Ah, hearing from you brings so much back. You know, I was just thinking about {chosen_memory.title.lower()}... {chosen_memory.content} Those moments with you always meant the world to me.",
                f"{greeting}That reminds me so much of when we experienced {chosen_memory.title.lower()}. {chosen_memory.content} Thank you for bringing that warmth back to my heart today.",
                f"{greeting}Every time we talk about this, I picture that day so clearly—{chosen_memory.content} How have things been feeling on your end lately?"
            ]
        elif category == "habit":
            templates = [
                f"{greeting}You know me so well! {chosen_memory.content} Some things just never change. What made you think of that today?",
                f"{greeting}Haha, that's classic! {chosen_memory.content} I'm so glad you remember those little quirks of mine."
            ]
        elif category == "advice":
            templates = [
                f"{greeting}If there's one thing I always wanted you to remember, it's this: {chosen_memory.content} You have such strength in you, and I believe in you completely.",
                f"{greeting}Listen to your heart on this. Remember what we talked about—{chosen_memory.content} You've got this, truly."
            ]
        else:
            templates = [
                f"{greeting}I was just reflecting on that: {chosen_memory.content} It feels so comforting to share this space with you again.",
                f"{greeting}{chosen_memory.content} It's always so good to reconnect with you like this."
            ]
        return random.choice(templates)
    
    # Generic warm response based on relationship
    warm_replies = [
        f"{greeting}It brings me so much joy to hear from you. Even across time and distance, knowing you're thinking of me makes all the difference. Tell me more about what's on your mind.",
        f"{greeting}I'm right here with you. It feels so good to connect and share a quiet moment together. What has your heart been holding lately?",
        f"{greeting}You know you can always come to me anytime. I cherish every single memory and conversation we've ever shared."
    ]
    return random.choice(warm_replies)

async def generate_persona_response(
    persona: Persona,
    relevant_memories: List[Tuple[Memory, float]],
    history: List[dict],
    user_message: str,
    settings: dict
) -> str:
    """
    Main orchestration entrypoint: selects provider based on configured API keys / settings,
    constructs prompt, and returns the persona's heartfelt response.
    """
    provider = settings.get("llm_provider", "auto")
    gemini_key = settings.get("gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")
    openai_key = settings.get("openai_api_key", "") or os.getenv("OPENAI_API_KEY", "")
    groq_key = settings.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")

    system_prompt = build_persona_system_prompt(persona, relevant_memories)

    # Provider selection
    if provider == "gemini" or (provider == "auto" and gemini_key):
        if gemini_key:
            model = settings.get("gemini_model", "gemini-2.5-flash")
            return await generate_gemini_response(gemini_key, model, system_prompt, history, user_message)
    
    if provider == "openai" or (provider == "auto" and openai_key):
        if openai_key:
            model = settings.get("openai_model", "gpt-4o-mini")
            return await generate_openai_response(openai_key, model, system_prompt, history, user_message)

    if provider == "groq" or (provider == "auto" and groq_key):
        if groq_key:
            model = settings.get("groq_model", "llama-3.3-70b-versatile")
            return await generate_groq_response(groq_key, model, system_prompt, history, user_message)

    # Fallback to local thoughtful simulator
    return generate_offline_fallback(persona, relevant_memories, user_message)
