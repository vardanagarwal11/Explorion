"""
LLM client utilities — routes to Groq (summarization) and NVIDIA NIM (code gen).

Provides backward-compatible `summarize()` and `generate_code()` functions
that the rest of the codebase uses, now backed by cloud APIs instead of Ollama.
"""

import logging
from typing import Optional

from providers.groq_client import groq_chat
from providers.nim_client import nim_generate

logger = logging.getLogger(__name__)


def chat(model: str, prompt: str, system: Optional[str] = None) -> str:
    """
    Route a chat request to the appropriate cloud API.

    For backward compatibility, this auto-detects whether to use Groq or NIM
    based on the model name.
    """
    # Code models → NVIDIA NIM
    code_keywords = ("llama", "coder", "qwen", "code", "nim")
    if any(k in model.lower() for k in code_keywords):
        return nim_generate(prompt, system=system)

    # Everything else → Groq (summarization, planning)
    return groq_chat(prompt, system=system)


def summarize(text: str) -> str:
    """Call Groq for content summarization / concept extraction."""
    return groq_chat(text)


def generate_code(prompt: str) -> str:
    """Call NVIDIA NIM for animation code generation."""
    return nim_generate(prompt)
