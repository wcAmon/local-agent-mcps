"""Gemini AI service — chat, JSON chat, search-grounded chat, and image generation."""

import asyncio
import json
import logging
import os
import re

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
CHAT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
def _get_client():
    return genai.Client(api_key=GOOGLE_API_KEY)


def _search_config(system: str | None = None) -> types.GenerateContentConfig:
    cfg = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    if system:
        cfg.system_instruction = system
    return cfg


async def chat(prompt: str, system: str = "You are a helpful research assistant.") -> str:
    """Simple Gemini chat."""
    def _call():
        client = _get_client()
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.7,
            ),
        )
        text = response.text or ""
        # Handle list-of-blocks format
        if not text and response.candidates:
            parts = response.candidates[0].content.parts
            text = " ".join(p.text for p in parts if hasattr(p, "text") and p.text)
        return text.strip()

    return await asyncio.to_thread(_call)


async def chat_json(prompt: str, system: str = "You are a helpful research assistant. Always respond with valid JSON.") -> dict:
    """Gemini chat that returns parsed JSON."""
    text = await chat(prompt, system)
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)


async def chat_with_search(prompt: str, system: str = "You are a helpful research assistant.") -> str:
    """Gemini chat with Google Search grounding for real-time data."""
    def _call():
        client = _get_client()
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=_search_config(system),
        )
        text = response.text or ""
        if not text and response.candidates:
            parts = response.candidates[0].content.parts
            text = " ".join(p.text for p in parts if hasattr(p, "text") and p.text)
        return text.strip()

    return await asyncio.to_thread(_call)


