"""Base agent class with Groq/NIM LLM support."""

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
    pass  # python-dotenv not installed, use system env vars

# Default model falls back to Groq Llama unless overridden by a subclass
DEFAULT_MODEL = "llama-3.3-70b-versatile"

def get_model_name(model: str | None = None) -> str:
    """Get the model name."""
    return model or DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Standalone LLM call helpers (usable outside BaseAgent, e.g. validators)
# ---------------------------------------------------------------------------

async def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str = "",
    max_tokens: int = 8192,
) -> str:
    """Async LLM call routed through Nim for NVIDIA models, or Groq for anything else."""
    import asyncio
    
    # Use Nim client for specified models (Kimi, meta, openai)
    lower_model = model.lower()
    if "moonshotai" in lower_model or "meta/" in lower_model or "kimi" in lower_model or "openai" in lower_model:
        from providers.nim_client import nim_generate
        return await asyncio.to_thread(
            nim_generate,
            prompt=prompt,
            system=system_prompt,
            model=model,
            temperature=0.7,
            max_tokens=max_tokens
        )
        
    from providers.groq_client import groq_chat
    return await asyncio.to_thread(
        groq_chat,
        prompt=prompt,
        system=system_prompt,
        model=model,
        temperature=0.7,
        max_tokens=max_tokens
    )

def call_llm_sync(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str = "",
    max_tokens: int = 8192,
) -> str:
    """Synchronous LLM call routed through Nim or Groq."""
    
    lower_model = model.lower()
    if "moonshotai" in lower_model or "meta/" in lower_model or "kimi" in lower_model or "openai" in lower_model:
        from providers.nim_client import nim_generate
        return nim_generate(
            prompt=prompt,
            system=system_prompt,
            model=model,
            temperature=0.7,
            max_tokens=max_tokens
        )
        
    from providers.groq_client import groq_chat
    return groq_chat(
        prompt=prompt,
        system=system_prompt,
        model=model,
        temperature=0.7,
        max_tokens=max_tokens
    )


class BaseAgent:
    """
    Base class for all AI agents in the pipeline.
    """

    def __init__(
        self,
        prompt_file: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ):
        self.model = get_model_name(model)
        self.max_tokens = max_tokens
        self.system_prompt = self._load_system_prompt()
        self.prompt_template = self._load_prompt(prompt_file)

        # Log active provider route
        if "openai" in self.model.lower() or "kimi" in self.model.lower() or "meta/" in self.model.lower():
            print(f"🔮 NVIDIA NIM SDK → {self.model}")
        else:
            print(f"🔮 Groq SDK → {self.model}")

    def _get_prompts_dir(self) -> Path:
        """Get the prompts directory path."""
        return Path(__file__).parent.parent / "prompts"

    def _load_system_prompt(self) -> str:
        """Load the curated Manim reference as system prompt."""
        path = self._get_prompts_dir() / "system" / "manim_reference.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template file."""
        path = self._get_prompts_dir() / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def _format_prompt(self, **kwargs: Any) -> str:
        """
        Format the prompt template with provided variables.

        Uses str.replace() instead of str.format() to avoid issues with
        content containing curly braces (like LaTeX's \\begin{pmatrix}).
        Also handles {{ and }} escape sequences like str.format() does.
        """
        result = self.prompt_template

        # Replace all placeholders first
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))

        # Convert escaped braces ({{ -> {, }} -> }) like str.format() does
        result = result.replace("{{", "{").replace("}}", "}")

        return result

    def _parse_json_response(self, content: str) -> dict:
        """
        Extract and parse JSON from the response.

        Handles both raw JSON and JSON wrapped in markdown code blocks.
        """
        # Try to extract JSON from markdown code blocks
        json_patterns = [
            r"```json\s*([\s\S]*?)\s*```",  # ```json ... ```
            r"```\s*([\s\S]*?)\s*```",       # ``` ... ```
        ]

        for pattern in json_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    continue

        # Try parsing the whole content as JSON
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from response: {e}\nContent: {content[:500]}")

    def _extract_code_block(self, content: str, language: str = "python") -> str:
        """
        Extract code from a markdown code block.

        Args:
            content: Response content
            language: Language tag to look for

        Returns:
            Extracted code or empty string
        """
        # Try language-specific block first
        pattern = rf"```{language}\s*([\s\S]*?)\s*```"
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()

        # Try generic code block
        pattern = r"```\s*([\s\S]*?)\s*```"
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()

        # Return content as-is if no code blocks found
        return content.strip()

    # ------------------------------------------------------------------
    # LLM call helpers — route to the active provider
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Call the LLM via the configured provider (async)."""
        return await call_llm(
            prompt=prompt,
            model=self.model,
            system_prompt=system_prompt or self.system_prompt,
            max_tokens=max_tokens or self.max_tokens,
        )

    def _call_llm_sync(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Call the LLM via the configured provider (sync)."""
        return call_llm_sync(
            prompt=prompt,
            model=self.model,
            system_prompt=system_prompt or self.system_prompt,
            max_tokens=max_tokens or self.max_tokens,
        )

    # ------------------------------------------------------------------
    # Default run methods
    # ------------------------------------------------------------------

    async def run(self, **kwargs: Any) -> dict:
        """
        Run the agent with the given parameters.

        This method should be overridden by subclasses for specific behavior.
        Default implementation formats the prompt and returns parsed JSON.
        """
        prompt = self._format_prompt(**kwargs)
        text = await self._call_llm(prompt)
        return self._parse_json_response(text)

    def run_sync(self, **kwargs: Any) -> dict:
        """Synchronous version of run() for testing."""
        prompt = self._format_prompt(**kwargs)
        text = self._call_llm_sync(prompt)
        return self._parse_json_response(text)
