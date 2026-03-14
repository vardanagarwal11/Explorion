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
    input_url: str           # arXiv URL / ID supplied by the user

    # ── Extraction ─────────────────────────────────────────────────────────
    content: str             # raw title + abstract text
    paper_id: str            # bare arXiv ID
    paper_title: str         # human-readable title

    # ── Summarization ──────────────────────────────────────────────────────
    summary: dict            # {"title": ..., "main_concepts": [...]}

    # ── Scene planning ────────────────────────────────────────────────────
    scenes: list[Scene]      # populated by planner; enriched by later nodes

    # ── Progress ──────────────────────────────────────────────────────────
    current_scene_index: int # which scene is currently being processed
    errors: list[str]        # non-fatal errors accumulated during the run
