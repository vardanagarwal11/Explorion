"""
LangGraph pipeline state definition.

The TypedDict below is the single shared state object that flows through every
node in the graph.  Each node reads what it needs and writes its outputs back
into the same dict.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class Scene(TypedDict):
    """A single planned animation scene."""
    title: str
    engine: str          # "manim" or "remotion"
    description: str
    code: str            # populated by the coder node
    video_path: str      # populated by the render node


class PipelineState(TypedDict):
    """Complete mutable state for one pipeline run."""

    # ── Input ──────────────────────────────────────────────────────────────
    input_url: str           # URL / ID supplied by the user (may be empty)
    input_content: str       # Pre-fetched content text (if already ingested)
    input_type: str          # "arxiv" | "github" | "pdf" | "text" | ""

    # ── Extraction ─────────────────────────────────────────────────────────
    content: str             # raw text for summarization
    content_id: str          # unique ID (arXiv ID, gh:owner/repo, hash, etc.)
    content_title: str       # human-readable title

    # ── Summarization ──────────────────────────────────────────────────────
    summary: dict            # {"title": ..., "main_concepts": [...]}

    # ── Scene planning ────────────────────────────────────────────────────
    scenes: list[Scene]      # populated by planner; enriched by later nodes

    # ── Progress ──────────────────────────────────────────────────────────
    current_scene_index: int # which scene is currently being processed
    errors: list[str]        # non-fatal errors accumulated during the run
