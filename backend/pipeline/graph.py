"""
LangGraph orchestration graph for the local AI pipeline.

Graph structure:
  START
   ↓
  extract_content      — fetch arXiv paper text
   ↓
  summarize            — phi3 extracts key concepts
   ↓
  plan_scenes          — phi3 turns concepts into scene list
   ↓
  generate_codes       — qwen2.5-coder writes animation code for every scene
   ↓
  render_scenes        — Manim / Remotion renders each scene to MP4
   ↓
  END

Usage:
    from pipeline.graph import run_pipeline

    result = run_pipeline("https://arxiv.org/abs/1706.03762")
    print(result)   # {"title": ..., "scenes": ["scene1.mp4", ...]}
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from pipeline.state import PipelineState
from extractors.arxiv_extractor import extract_arxiv
from agents.summarizer import run_summarizer
from agents.planner import run_planner
from agents.coder import run_coder
from renderers.manim_renderer import render_manim
from renderers.remotion_renderer import render_remotion

logger = logging.getLogger(__name__)
MIN_SCENE_DURATION_SECONDS = 8.0


def _probe_duration_seconds(video_path: str) -> float | None:
    """Return video duration in seconds when probe succeeds."""
    try:
        import av

        with av.open(video_path) as container:
            if container.duration is None:
                return None
            # container.duration is in microseconds (AV_TIME_BASE = 1,000,000)
            return float(container.duration) / 1_000_000.0
    except Exception:
        return None


# ── Node implementations ───────────────────────────────────────────────────


def extract_content(state: PipelineState) -> dict:
    """Fetch arXiv paper and populate raw content fields."""
    logger.info("[Node] extract_content | url=%s", state["input_url"])
    paper = extract_arxiv(state["input_url"])
    return {
        "content": paper["content"],
        "paper_id": paper["id"],
        "paper_title": paper["title"],
    }


def summarize(state: PipelineState) -> dict:
    """Run phi3 summarizer to extract structured concepts."""
    logger.info("[Node] summarize | paper=%s", state.get("paper_title", "?"))
    summary = run_summarizer(state["content"])
    return {"summary": summary}


def plan_scenes(state: PipelineState) -> dict:
    """Run phi3 planner to convert concepts into a scene list."""
    logger.info("[Node] plan_scenes")
    plan = run_planner(state["summary"])
    scenes = [
        {
            "title": s["title"],
            "engine": s["engine"],
            "description": s["description"],
            "code": "",
            "video_path": "",
        }
        for s in plan.get("scenes", [])
    ]
    return {"scenes": scenes, "current_scene_index": 0}


def generate_codes(state: PipelineState) -> dict:
    """Generate animation code for every scene using qwen2.5-coder."""
    logger.info("[Node] generate_codes | %d scenes", len(state.get("scenes", [])))
    updated = []
    errors = list(state.get("errors", []))

    for scene in state["scenes"]:
        try:
            code = run_coder(scene)
            updated.append({**scene, "code": code})
        except Exception as exc:
            logger.warning("Coder error for scene %r: %s", scene["title"], exc)
            errors.append(f"Coder failed for '{scene['title']}': {exc}")
            updated.append({**scene, "code": ""})

    return {"scenes": updated, "errors": errors}


def render_scenes(state: PipelineState) -> dict:
    """Render each scene to an MP4 file."""
    logger.info("[Node] render_scenes | %d scenes", len(state.get("scenes", [])))
    updated = []
    errors = list(state.get("errors", []))
    max_retries = 3

    for i, scene in enumerate(state["scenes"]):
        if not scene.get("code"):
            updated.append(scene)
            continue
        scene_id = f"{state['paper_id']}_{i}"
        engine = scene["engine"]
        rendered_path = ""
        last_error = None
        working_scene = dict(scene)

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Rendering scene %d/%d | attempt %d | engine=%s | title=%s",
                    i + 1,
                    len(state["scenes"]),
                    attempt,
                    engine,
                    scene.get("title", ""),
                )

                if attempt > 1:
                    # Regenerate code before retry.
                    regenerated = run_coder(working_scene)
                    working_scene["code"] = regenerated

                if engine == "remotion":
                    temp_path = render_remotion(working_scene["code"], scene_id=scene_id)
                else:
                    temp_path = render_manim(working_scene["code"], scene_id=scene_id)

                duration = _probe_duration_seconds(temp_path)
                if duration is not None and duration < MIN_SCENE_DURATION_SECONDS:
                    raise RuntimeError(
                        f"Rendered scene too short ({duration:.2f}s). "
                        f"Minimum required is {MIN_SCENE_DURATION_SECONDS:.0f}s."
                    )
                rendered_path = temp_path
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Render attempt %d failed for scene %r: %s",
                    attempt,
                    scene.get("title", ""),
                    exc,
                )
                # Encourage longer, richer output on retry.
                working_scene["description"] = (
                    working_scene.get("description", "")
                    + "\n\nCRITICAL: The previous render was TOO SHORT. "
                    "You MUST add at least 6 self.wait(3) calls between animation steps. "
                    "Target 20-30 seconds total. Each phase needs a self.wait(3) or self.wait(4) after it."
                )

        if rendered_path:
            updated.append({**working_scene, "video_path": rendered_path})
            logger.info("Rendered scene %d: %s", i, rendered_path)
        else:
            errors.append(f"Render failed for '{scene['title']}' after {max_retries} attempts: {last_error}")
            updated.append({**working_scene, "video_path": ""})

    return {"scenes": updated, "errors": errors}


# ── Graph construction ─────────────────────────────────────────────────────


def _build_graph() -> Any:
    g = StateGraph(PipelineState)

    g.add_node("extract_content", extract_content)
    g.add_node("summarize", summarize)
    g.add_node("plan_scenes", plan_scenes)
    g.add_node("generate_codes", generate_codes)
    g.add_node("render_scenes", render_scenes)

    g.add_edge(START, "extract_content")
    g.add_edge("extract_content", "summarize")
    g.add_edge("summarize", "plan_scenes")
    g.add_edge("plan_scenes", "generate_codes")
    g.add_edge("generate_codes", "render_scenes")
    g.add_edge("render_scenes", END)

    return g.compile()


# Singleton — compiled once at import time
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


# ── Public API ─────────────────────────────────────────────────────────────


def run_pipeline(input_url: str) -> dict:
    """
    Run the full local pipeline synchronously.

    Args:
        input_url: arXiv URL or paper ID.

    Returns:
        {
          "title": <str>,
          "paper_id": <str>,
          "scenes": [
            {
              "title": ..., "engine": ...,
              "description": ..., "video_path": ...
            }, ...
          ],
          "errors": [<str>, ...]
        }
    """
    initial_state: PipelineState = {
        "input_url": input_url,
        "content": "",
        "paper_id": "",
        "paper_title": "",
        "summary": {},
        "scenes": [],
        "current_scene_index": 0,
        "errors": [],
    }

    graph = _get_graph()
    final_state = graph.invoke(initial_state)

    return {
        "title": final_state.get("paper_title", ""),
        "paper_id": final_state.get("paper_id", ""),
        "scenes": [
            {
                "title": s["title"],
                "engine": s["engine"],
                "description": s["description"],
                "video_path": s.get("video_path", ""),
            }
            for s in final_state.get("scenes", [])
        ],
        "errors": final_state.get("errors", []),
    }
