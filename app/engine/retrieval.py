import re
import json
import math
from typing import List, Tuple
from collections import Counter
from app.models import Memory

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into",
    "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's",
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs",
    "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves"
}

def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into meaningful terms."""
    if not text:
        return []
    words = re.findall(r'\b[a-zA-Z0-9_\-\']+\b', text.lower())
    return [w for w in words if len(w) > 1 and w not in STOP_WORDS]

def score_memory(query_tokens: List[str], memory: Memory) -> float:
    """
    Score a single memory's relevance to a query using BM25-inspired keyword frequency,
    title/tag boosts, and memory importance weights.
    """
    if not query_tokens:
        return float(memory.importance or 1) * 0.5

    title_tokens = set(tokenize(memory.title))
    content_tokens = tokenize(memory.content)
    
    try:
        tags = json.loads(memory.tags) if memory.tags else []
        tag_tokens = set(tokenize(" ".join(tags)))
    except Exception:
        tag_tokens = set()

    content_counter = Counter(content_tokens)
    total_content_words = max(len(content_tokens), 1)

    score = 0.0

    for token in query_tokens:
        # Title match (high weight)
        if token in title_tokens:
            score += 5.0

        # Tag match (high weight)
        if token in tag_tokens:
            score += 4.0

        # Content match with term saturation
        count = content_counter.get(token, 0)
        if count > 0:
            # Term frequency saturation
            tf = (count * 2.2) / (count + 1.2 * (0.25 + 0.75 * (total_content_words / 50.0)))
            score += tf * 2.0

        # Partial substring match for root words
        for c_token in content_tokens:
            if (len(token) >= 4 and token in c_token) or (len(c_token) >= 4 and c_token in token):
                score += 0.8
                break

    # Date / Time reference bonus if query mentions time words
    if memory.date_reference:
        date_tokens = set(tokenize(memory.date_reference))
        for token in query_tokens:
            if token in date_tokens:
                score += 3.0

    # Apply base importance multiplier (importance is 1 to 5)
    importance_multiplier = 1.0 + ((memory.importance or 3) - 1) * 0.15
    score = score * importance_multiplier

    return score

def retrieve_relevant_memories(
    memories: List[Memory], 
    user_query: str, 
    top_k: int = 5,
    min_score_threshold: float = 0.5
) -> List[Tuple[Memory, float]]:
    """
    Retrieve and rank top_k most relevant memories for a user query.
    If no memory meets the score threshold, top high-importance memories are returned.
    """
    if not memories:
        return []

    query_tokens = tokenize(user_query)
    
    scored_memories = []
    for memory in memories:
        score = score_memory(query_tokens, memory)
        scored_memories.append((memory, score))

    # Sort descending by score
    scored_memories.sort(key=lambda x: x[1], reverse=True)

    # Filter by threshold if we had valid query tokens
    if query_tokens:
        relevant = [item for item in scored_memories if item[1] >= min_score_threshold][:top_k]
        if relevant:
            return relevant

    # Fallback: Return top memories by importance and recency
    fallback = sorted(
        memories, 
        key=lambda m: (m.importance or 3, m.created_at), 
        reverse=True
    )[:min(top_k, 3)]
    
    return [(m, 0.5) for m in fallback]
