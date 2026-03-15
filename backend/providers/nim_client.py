"""
NVIDIA NIM API client for animation code generation.

Uses openai/gpt-oss-120b via the NVIDIA NIM cloud API (OpenAI SDK format) for high-quality Manim code generation.
"""

import logging
import os
import sys
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    pass  # We'll fail gracefully later if missing

logger = logging.getLogger(__name__)

NIM_API_KEY = os.getenv("NIM_API_KEY", "")
NIM_API_URL = "https://integrate.api.nvidia.com/v1"
CODE_MODEL = os.getenv("CODE_MODEL", "openai/gpt-oss-120b")

# Retry config
MAX_RETRIES = 5

def nim_generate(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: int = 4096,
) -> str:
    """
    Send a chat completion request to the NVIDIA NIM API using streaming and OpenAI SDK.

    Args:
        prompt:      User message content.
        system:      Optional system message.
        model:       Model override (defaults to CODE_MODEL).
        temperature: Sampling temperature (lower = more deterministic code).
        max_tokens:  Maximum response tokens.

    Returns:
        The model's text response.

    Raises:
        RuntimeError: If the API call fails after retries.
    """
    if "openai" not in sys.modules:
        raise RuntimeError("Please install the 'openai' Python package to use NIM API streaming.")

    if not NIM_API_KEY:
        raise RuntimeError(
            "NIM_API_KEY not set. Add it to your .env file."
        )

    client = OpenAI(
        base_url=NIM_API_URL,
        api_key=NIM_API_KEY
    )

    model = model or CODE_MODEL
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "NIM request | model=%s | attempt=%d | prompt_len=%d",
                model, attempt, len(prompt),
            )
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=1,
                max_tokens=max_tokens,
                stream=True
            )

            full_text = ""
            full_reasoning = ""

            for chunk in completion:
                if not getattr(chunk, "choices", None):
                    continue
                
                # Check for advanced reasoning/thinking output
                reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                if reasoning:
                    full_reasoning += reasoning
                    print(reasoning, end="", flush=True)
                
                # Standard response content
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_text += content
                    print(content, end="", flush=True)

            print("", flush=True) # Send final newline when stream completes
            
            logger.info(
                "NIM response | model=%s | response_len=%d | reasoning_len=%d",
                model, len(full_text), len(full_reasoning)
            )
            return full_text

        except Exception as exc:
            last_error = exc
            logger.warning("NIM error on attempt %d: %s", attempt, exc)
            import time
            time.sleep(3 * attempt)

    raise RuntimeError(f"NIM API failed after {MAX_RETRIES} attempts: {last_error}")
