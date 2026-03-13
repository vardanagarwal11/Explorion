"""
Text-to-Speech (TTS) engine abstraction for arXivisual.

Provides a unified interface for multiple TTS providers:
- gTTS (Google Text-to-Speech): Free, decent quality, multi-language
- OpenAI TTS: High quality (tts-1, tts-1-hd), 6 voice presets
- ElevenLabs: Premium voices with emotion control

Usage:
    from tts import get_tts_engine
    
    engine = get_tts_engine("openai")
    audio_bytes = await engine.synthesize("Hello world", voice="nova")
"""

import os
import io
import logging
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Base class for all TTS engines."""
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            voice: Voice name (provider-specific)
            language: Language code (ISO 639-1)
            speed: Speech speed multiplier (0.5 = slow, 1.0 = normal, 2.0 = fast)
            
        Returns:
            Audio bytes (MP3 format)
        """
        ...
    
    @abstractmethod
    def list_voices(self) -> list[dict]:
        """List available voices for this engine."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""
        ...


# ═══════════════════════════════════════════════════════════
# gTTS Engine (Free)
# ═══════════════════════════════════════════════════════════

class GTTSEngine(TTSEngine):
    """Google Text-to-Speech engine via gTTS library."""
    
    @property
    def name(self) -> str:
        return "gtts"
    
    async def synthesize(
        self,
        text: str,
        voice: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize using gTTS (runs in thread pool since gTTS is synchronous)."""
        import asyncio
        
        def _synthesize():
            from gtts import gTTS
            tts = gTTS(text=text, lang=language, slow=(speed < 0.8))
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            return buffer.getvalue()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _synthesize)
    
    def list_voices(self) -> list[dict]:
        """gTTS doesn't have distinct voices — just language variants."""
        return [
            {"id": "default", "name": "Default", "language": "en"},
        ]


# ═══════════════════════════════════════════════════════════
# OpenAI TTS Engine
# ═══════════════════════════════════════════════════════════

class OpenAITTSEngine(TTSEngine):
    """OpenAI Text-to-Speech engine (tts-1 / tts-1-hd)."""
    
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    DEFAULT_VOICE = "nova"  # Warm and natural
    
    def __init__(self, model: str = "tts-1"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set — OpenAI TTS will fail on synthesize")
    
    @property
    def name(self) -> str:
        return "openai"
    
    async def synthesize(
        self,
        text: str,
        voice: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize using OpenAI TTS API."""
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        
        import httpx
        
        voice = voice if voice in self.VOICES else self.DEFAULT_VOICE
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": text,
                    "voice": voice,
                    "speed": max(0.25, min(4.0, speed)),
                    "response_format": "mp3",
                },
            )
            response.raise_for_status()
            return response.content
    
    def list_voices(self) -> list[dict]:
        return [
            {"id": "alloy", "name": "Alloy", "description": "Neutral and balanced"},
            {"id": "echo", "name": "Echo", "description": "Warm and grounded"},
            {"id": "fable", "name": "Fable", "description": "Expressive, British accent"},
            {"id": "onyx", "name": "Onyx", "description": "Deep and authoritative"},
            {"id": "nova", "name": "Nova", "description": "Warm and natural (default)"},
            {"id": "shimmer", "name": "Shimmer", "description": "Bright and energetic"},
        ]


# ═══════════════════════════════════════════════════════════
# ElevenLabs TTS Engine
# ═══════════════════════════════════════════════════════════

class ElevenLabsTTSEngine(TTSEngine):
    """ElevenLabs Text-to-Speech engine (premium)."""
    
    DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY not set — ElevenLabs TTS will fail")
    
    @property
    def name(self) -> str:
        return "elevenlabs"
    
    async def synthesize(
        self,
        text: str,
        voice: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize using ElevenLabs API."""
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set")
        
        import httpx
        
        voice_id = voice or self.DEFAULT_VOICE_ID
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            )
            response.raise_for_status()
            return response.content
    
    def list_voices(self) -> list[dict]:
        return [
            {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "description": "Deep, American male"},
            {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "description": "Soft, American female"},
            {"id": "jsCqWAovK2LkecY7zXl4", "name": "Freya", "description": "American female"},
            {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "description": "Australian male"},
        ]


# ═══════════════════════════════════════════════════════════
# Narration Styles
# ═══════════════════════════════════════════════════════════

NARRATION_STYLES = {
    "educational": {
        "description": "Clear, structured, and informative — default style",
        "speed": 1.0,
        "pause_between_scenes": 0.5,
        "prompt_modifier": (
            "Narrate this in a clear, educational style. "
            "Use precise language and explain concepts step by step. "
            "Keep sentences concise and well-structured."
        ),
    },
    "teacher": {
        "description": "Slow, clear, beginner-friendly explanation",
        "speed": 0.85,
        "pause_between_scenes": 1.0,
        "prompt_modifier": (
            "Narrate this as a patient teacher explaining to a beginner. "
            "Use simple language, repeat key concepts, and provide analogies. "
            "Pause between ideas to let them sink in."
        ),
    },
    "quick_summary": {
        "description": "Fast-paced overview hitting key points",
        "speed": 1.15,
        "pause_between_scenes": 0.3,
        "prompt_modifier": (
            "Narrate a quick summary hitting only the main points. "
            "Be concise and direct. No filler words. "
            "Focus on the 'what' and 'why', skip the details."
        ),
    },
    "youtube": {
        "description": "Engaging YouTube explainer style",
        "speed": 1.05,
        "pause_between_scenes": 0.4,
        "prompt_modifier": (
            "Narrate this like an engaging YouTube tech explainer. "
            "Be enthusiastic but informative. Use conversational language. "
            "Include transitions like 'Now here's where it gets interesting...' "
            "and 'Let me break this down for you...'"
        ),
    },
    "podcast": {
        "description": "Conversational, deep-dive discussion",
        "speed": 0.95,
        "pause_between_scenes": 0.6,
        "prompt_modifier": (
            "Narrate this like a podcast host having a deep conversation. "
            "Be conversational and thoughtful. Share insights and opinions. "
            "Use phrases like 'What I find fascinating is...' "
            "and 'Think about it this way...'"
        ),
    },
}


def get_narration_style(style_name: str) -> dict:
    """Get narration style configuration."""
    return NARRATION_STYLES.get(style_name, NARRATION_STYLES["educational"])


# ═══════════════════════════════════════════════════════════
# Subtitle Generator
# ═══════════════════════════════════════════════════════════

def generate_srt(
    narration_segments: list[dict],
) -> str:
    """
    Generate SRT subtitle file from narration segments.
    
    Each segment should have:
    - text: str — narration text
    - start: float — start time in seconds
    - end: float — end time in seconds
    
    Returns:
        SRT formatted string
    """
    lines = []
    for i, seg in enumerate(narration_segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    
    return "\n".join(lines)


def generate_vtt(
    narration_segments: list[dict],
) -> str:
    """
    Generate WebVTT subtitle file from narration segments.
    
    Returns:
        VTT formatted string
    """
    lines = ["WEBVTT\n"]
    for i, seg in enumerate(narration_segments, 1):
        start = _format_vtt_time(seg["start"])
        end = _format_vtt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    
    return "\n".join(lines)


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT time format: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_vtt_time(seconds: float) -> str:
    """Format seconds to VTT time format: HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def estimate_narration_timing(
    narration_lines: list[str],
    words_per_minute: float = 150,
    pause_between: float = 0.5,
) -> list[dict]:
    """
    Estimate timing for narration segments based on word count.
    
    Args:
        narration_lines: List of narration text segments
        words_per_minute: Speaking speed (default 150 wpm)
        pause_between: Pause between segments in seconds
    
    Returns:
        List of dicts with text, start, and end times
    """
    segments = []
    current_time = 0.0
    
    for text in narration_lines:
        word_count = len(text.split())
        duration = (word_count / words_per_minute) * 60
        duration = max(duration, 1.0)  # Minimum 1 second
        
        segments.append({
            "text": text,
            "start": current_time,
            "end": current_time + duration,
        })
        
        current_time += duration + pause_between
    
    return segments


# ═══════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════

# Engine singleton cache
_engines: dict[str, TTSEngine] = {}


def get_tts_engine(provider: str = "gtts") -> TTSEngine:
    """
    Get a TTS engine instance by provider name.
    
    Supported providers: gtts, openai, elevenlabs
    
    Args:
        provider: TTS provider name
        
    Returns:
        TTSEngine instance
    """
    provider = provider.lower().strip()
    
    if provider in _engines:
        return _engines[provider]
    
    if provider == "gtts":
        engine = GTTSEngine()
    elif provider == "openai":
        engine = OpenAITTSEngine()
    elif provider == "openai_hd":
        engine = OpenAITTSEngine(model="tts-1-hd")
    elif provider == "elevenlabs":
        engine = ElevenLabsTTSEngine()
    else:
        logger.warning(f"Unknown TTS provider '{provider}', falling back to gTTS")
        engine = GTTSEngine()
    
    _engines[provider] = engine
    logger.info(f"Initialized TTS engine: {engine.name}")
    return engine


__all__ = [
    "TTSEngine",
    "GTTSEngine",
    "OpenAITTSEngine",
    "ElevenLabsTTSEngine",
    "get_tts_engine",
    "NARRATION_STYLES",
    "get_narration_style",
    "generate_srt",
    "generate_vtt",
    "estimate_narration_timing",
]
