"""Base agent class — Modal GLM-5.1 primary, NIM fallback, GROQ tertiary, Gemini quaternary.

Provider priority (first key found in .env wins):
  1. MODAL_API_KEY     → Modal GLM-5.1-FP8 (OpenAI-compatible, free research tier)
  2. NIM_API_KEY       → NVIDIA NIM        (OpenAI-compatible, free tier)
  3. GROQ_API_KEY      → Groq Cloud        (free, ultra-fast Llama 3)
  4. GEMINI_API_KEY    → Google Gemini     (free tier)
"""

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


# ─────────────────────────────────────────────
# Model defaults per provider
# ─────────────────────────────────────────────

OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"

# Resolved once at first use
_provider: str | None = "ollama"

# Retry/backoff settings for LLM calls
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_BACKOFF_BASE = float(os.getenv("LLM_BACKOFF_BASE", "2"))


# ─────────────────────────────────────────────
# Provider resolution
# ─────────────────────────────────────────────

def _resolve_provider() -> str:
    return "ollama"


def get_provider() -> str:
    return "ollama"


def get_model_name(model: str | None = None) -> str:
    return model or "llama3.1:8b"


def _get_client() -> None:
    """Compatibility shim — kept so existing agent code that stores self.client doesn't break."""
    return None


# ─────────────────────────────────────────────
# Ollama
# ─────────────────────────────────────────────

async def _call_ollama(prompt: str, model: str, system_prompt: str, max_tokens: int) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "300"))
    t0 = time.monotonic()
    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens, temperature=0.2,
            ),
            timeout=timeout,
        )
        logger.info("[Ollama] %.1fs | %s", time.monotonic() - t0, model)
        return resp.choices[0].message.content or ""
    except asyncio.TimeoutError:
        raise TimeoutError(f"Ollama timed out after {timeout}s")


# ─────────────────────────────────────────────
# Unified async call
# ─────────────────────────────────────────────

async def call_llm(
    prompt: str,
    model: str | None = None,
    system_prompt: str = "",
    max_tokens: int = 4096,
) -> str:
    effective_model = model or get_model_name()
    provider = "ollama"

    input_words = len(prompt.split())
    logger.info("[LLM] %s | %s | %d input words | max_tokens=%d",
                provider, effective_model, input_words, max_tokens)

    # Perform the call with simple retry/backoff for rate limits and timeouts
    last_exc: Exception | None = None
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            result = await _call_ollama(prompt, effective_model, system_prompt, max_tokens)
            break
        except Exception as e:
            last_exc = e
            msg = str(e).lower()
            if "429" in msg or "rate" in msg or isinstance(e, TimeoutError):
                backoff = LLM_BACKOFF_BASE ** (attempt)
                logger.warning("LLM call failed (attempt %s/%s): %s — retrying in %.1fs", attempt, LLM_MAX_RETRIES, e, backoff)
                await asyncio.sleep(backoff)
                continue
            raise
    else:
        raise RuntimeError(f"LLM call failed after {LLM_MAX_RETRIES} attempts: {last_exc}")

    try:
        log_file = Path(__file__).parent.parent / "llm_outputs.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"TIMESTAMP: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"PROVIDER: {provider} | MODEL: {effective_model}\n")
            f.write(f"SYSTEM PROMPT:\n{system_prompt}\n")
            f.write(f"{'-'*80}\n")
            f.write(f"USER PROMPT:\n{prompt[:2000]}... [truncated]\n")
            f.write(f"{'-'*80}\n")
            f.write(f"RESPONSE:\n{result}\n")
            f.write(f"{'='*80}\n")
    except Exception as e:
        logger.error(f"Failed to log LLM output: {e}")

    return result


def call_llm_sync(
    prompt: str,
    model: str | None = None,
    system_prompt: str = "",
    max_tokens: int = 4096,
) -> str:
    return asyncio.run(call_llm(prompt, model=model, system_prompt=system_prompt, max_tokens=max_tokens))


# ─────────────────────────────────────────────
# BaseAgent
# ─────────────────────────────────────────────

class BaseAgent:
    """
    Base class for all AI agents in the pipeline.

    Automatically routes LLM calls to NIM → GROQ → Gemini
    based on which API key is present in the environment.
    No paid or third-party routing layer required.
    """

    def __init__(
        self,
        prompt_file: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ):
        self._provider = "ollama"
        if model:
            self.model = model
        else:
            # Route coding/technical tasks to qwen2.5-coder:7b
            coding_keywords = ["manim", "code", "render", "spatial"]
            if any(k in prompt_file for k in coding_keywords):
                self.model = "qwen2.5-coder:7b"
            else:
                self.model = "llama3.1:8b"
                
        self.max_tokens = max_tokens
        self.system_prompt = self._load_system_prompt()
        self.prompt_template = self._load_prompt(prompt_file)
        self.client = _get_client()

        logger.info("[%s] %s — model: %s", self.__class__.__name__, self._provider, self.model)

    def _get_prompts_dir(self) -> Path:
        return Path(__file__).parent.parent / "prompts"

    def _load_system_prompt(self) -> str:
        path = self._get_prompts_dir() / "system" / "manim_reference.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _load_prompt(self, filename: str) -> str:
        path = self._get_prompts_dir() / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def _format_prompt(self, **kwargs: Any) -> str:
        result = self.prompt_template
        for key, value in kwargs.items():
            result = result.replace("{" + key + "}", str(value))
        result = result.replace("{{", "{").replace("}}", "}")
        return result

    def _parse_json_response(self, content: str) -> dict:
        for pattern in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"]:
            match = re.search(pattern, content)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    continue
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from response: {e}\nContent: {content[:500]}")

    def _extract_code_block(self, content: str, language: str = "python") -> str:
        for pattern in [rf"```{language}\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"]:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        return content.strip()

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        return await call_llm(
            prompt=prompt,
            model=self.model,
            system_prompt=system_prompt if system_prompt is not None else self.system_prompt,
            max_tokens=max_tokens or self.max_tokens,
        )

    def _call_llm_sync(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        return call_llm_sync(
            prompt=prompt,
            model=self.model,
            system_prompt=system_prompt if system_prompt is not None else self.system_prompt,
            max_tokens=max_tokens or self.max_tokens,
        )

    async def run(self, **kwargs: Any) -> dict:
        prompt = self._format_prompt(**kwargs)
        text = await self._call_llm(prompt)
        return self._parse_json_response(text)

    def run_sync(self, **kwargs: Any) -> dict:
        prompt = self._format_prompt(**kwargs)
        text = self._call_llm_sync(prompt)
        return self._parse_json_response(text)
