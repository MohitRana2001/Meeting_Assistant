"""
Meeting summariser – Phase 4 will call the agent/task extractor.
"""

import json
from loguru import logger
import google.generativeai as genai
from core.config import settings

# Configure the Gemini client
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.GEMINI_MODEL)

SYSTEM_PROMPT = (
    "You are MeetingMate, an expert note-taker.\n"
    "Return ONLY valid JSON with:\n"
    '  "summary": 2-3 lines summarising the meeting, and\n'
    '  "tasks":   an array of concise action items (max 10, each ≤ 15 words, '
    "imperative verb first).\n"
    "Do not output any additional keys or formatting."
)

def summarise_transcript(transcript: str) -> dict:
    """
    Summarize a meeting transcript and extract action items using Gemini.
    """
    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\n{transcript}"
        result = model.generate_content(full_prompt, generation_config={
                "temperature": 0.2,
                "max_output_tokens": 512,
            },
        )
        content = result.text.strip()
        return json.loads(content)
    except Exception as exc:
        logger.exception("Gemini summarisation failed: %s", exc)
        # Fallback: return truncated transcript with no tasks
        return {
            "summary": transcript[:140] + "...",
            "tasks": [],
        }
