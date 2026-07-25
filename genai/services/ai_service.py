import requests
from datetime import datetime

from genai.services.realtime_service import needs_realtime, fetch_realtime_context
from genai.services.cache_service import get_cache, set_cache

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL = "mistral"

def call_ollama(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 300
        }
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json().get("response", "")

def get_ai_response(user_query):
    # Cache check (only for non-realtime)
    if not needs_realtime(user_query):
        cached = get_cache(user_query)
        if cached:
            return cached

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if needs_realtime(user_query):
        realtime_context = fetch_realtime_context(user_query)

        if not realtime_context:
            return "I could not fetch live data at this moment. Please try again shortly."

        final_prompt = f"""
You MUST answer ONLY using the real-time context below.
Do NOT guess. Do NOT use your training data.

Current date/time: {now}

Real-time context:
{realtime_context}

User question:
{user_query}
"""
    else:
        final_prompt = f"""
Current date/time: {now}

User question:
{user_query}
"""

    answer = call_ollama(final_prompt)

    if not needs_realtime(user_query):
        set_cache(user_query, answer, ttl=300)

    return answer
