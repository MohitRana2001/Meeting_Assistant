"""
Gemini-powered summariser & task extractor using Google ADK.

Switching from OpenAI to Gemini only affects this file.
"""

from __future__ import annotations

import json
from typing import Dict, Any

from loguru import logger
import google.generativeai as genai
from google.adk.agents import Agent

from core.config import settings

# --------------------------------------------------------------------------- #
# Gemini client initialization
# --------------------------------------------------------------------------- #
# Configure the Gemini Developer API client with your API key
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

# --------------------------------------------------------------------------- #
# ADK Tool definition (plain function)
# --------------------------------------------------------------------------- #
def summarize_meeting(transcript: str) -> Dict[str, Any]:
    """
    Summarize a meeting transcript and extract action items using Gemini.
    """
    try:
        result = model.generate_content(
            [
                {"role": "system", "parts": [SYSTEM_PROMPT]},
                {"role": "user", "parts": [transcript]},
            ],
            generation_config={
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

# --------------------------------------------------------------------------- #
# Single-tool Agent instance
# --------------------------------------------------------------------------- #
agent = Agent(
    name="MeetingSummarizer",
    model=settings.GEMINI_MODEL,
    description="Summarize a meeting transcript and extract action items.",
    instruction=SYSTEM_PROMPT,
    tools=[summarize_meeting],
)
