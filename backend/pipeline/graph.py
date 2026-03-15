"""
LangGraph orchestration graph for the universal AI pipeline.

Graph structure:
  START
   ↓
  extract_content      — fetch/parse any content type (arXiv, GitHub, PDF, text)
   ↓
  summarize            — LLM extracts key concepts
   ↓
  plan_scenes          — LLM turns concepts into scene list
   ↓
  generate_codes       — LLM writes animation code for every scene
   ↓
  render_scenes        — Manim / Remotion renders each scene to MP4
   ↓
  END

Usage:
    from pipeline.graph import run_pipeline

    result = run_pipeline("https://arxiv.org/abs/1706.03762")
    result = run_pipeline("https://github.com/owner/repo")
    result = run_pipeline(content="Some technical text to visualize")
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.graph import StateGraph, START, END

from pipeline.state import PipelineState
from agents.summarizer import run_summarizer
from agents.planner import run_planner
from agents.coder import run_coder
from renderers.manim_renderer import render_manim
from renderers.remotion_renderer import render_remotion

logger = logging.getLogger(__name__)

# Minimum acceptable duration — scenes shorter than this use fallback code
MIN_SCENE_DURATION_SECONDS = 10.0


def _probe_duration_seconds(video_path: str) -> float | None:
    """Return video duration in seconds when probe succeeds."""
    try:
        import av

        with av.open(video_path) as container:
            if container.duration is None:
                return None
            return float(container.duration) / 1_000_000.0
    except Exception:
        return None


# ── Content detection helpers ──────────────────────────────────────────────

def _detect_input_type(url_or_id: str) -> str:
    """Detect what kind of input the user gave us."""
    if not url_or_id:
        return "text"
    s = url_or_id.strip().lower()
    if "github.com" in s:
        return "github"
    if "arxiv.org" in s or re.match(r"^\d{4}\.\d{4,5}", s):
        return "arxiv"
    if s.endswith(".pdf"):
        return "pdf"
    if s.startswith("http"):
        return "url"
    # Bare arXiv ID patterns
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", url_or_id.strip()):
        return "arxiv"
    return "text"


def _fetch_arxiv_content(url_or_id: str) -> dict:
    """Fetch arXiv paper title + abstract."""
    import arxiv

    # Extract bare ID
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", url_or_id)
    paper_id = match.group(1) if match else url_or_id.strip()
    paper_id = re.sub(r"v\d+$", "", paper_id)

    client = arxiv.Client()
    search = arxiv.Search(id_list=[paper_id])
    results = list(client.results(search))
    if not results:
        raise ValueError(f"No arXiv paper found for: {paper_id}")

    paper = results[0]
    return {
        "content_id": paper_id,
        "title": paper.title,
        "content": f"{paper.title}\n\n{paper.summary}",
    }


def _fetch_github_content(url: str) -> dict:
    """Fetch GitHub repo README and description."""
    import asyncio
    from ingestion import ingest_github_repo

    loop = asyncio.new_event_loop()
    try:
        structured = loop.run_until_complete(ingest_github_repo(url))
    finally:
        loop.close()

    # Build text content from sections
    text_parts = [structured.meta.title, structured.meta.description or ""]
    for section in structured.sections[:6]:
        text_parts.append(f"\n## {section.title}\n{section.content[:1500]}")

    content_id = structured.meta.content_id
    return {
        "content_id": content_id,
        "title": structured.meta.title,
        "content": "\n".join(text_parts),
    }


def _fetch_url_content(url: str) -> dict:
    """Fetch content from a generic URL (blog, docs, etc.)."""
    import asyncio
    from ingestion.content_fetcher import ingest_technical_content

    loop = asyncio.new_event_loop()
    try:
        structured = loop.run_until_complete(ingest_technical_content(url=url))
    finally:
        loop.close()

    text_parts = [structured.meta.title]
    for section in structured.sections[:6]:
        text_parts.append(f"\n## {section.title}\n{section.content[:1500]}")

    import hashlib
    content_id = f"content:{hashlib.sha256(url.encode()).hexdigest()[:12]}"
    return {
        "content_id": content_id,
        "title": structured.meta.title,
        "content": "\n".join(text_parts),
    }


# ── Node implementations ───────────────────────────────────────────────────


def extract_content(state: PipelineState) -> dict:
    """Fetch and parse content from any supported source."""
    # If content was pre-injected, use it directly
    if state.get("input_content"):
        logger.info("[Node] extract_content | using pre-injected content (%d chars)", len(state["input_content"]))
        return {
            "content": state["input_content"],
            "content_id": state.get("content_id") or "unknown",
            "content_title": state.get("content_title") or "Content",
        }

    input_url = state.get("input_url", "")
    input_type = state.get("input_type") or _detect_input_type(input_url)
    logger.info("[Node] extract_content | type=%s url=%s", input_type, input_url[:80])

    try:
        if input_type == "arxiv":
            data = _fetch_arxiv_content(input_url)
        elif input_type == "github":
            data = _fetch_github_content(input_url)
        elif input_type in ("url", "pdf"):
            data = _fetch_url_content(input_url)
        elif input_type == "text":
            import hashlib
            data = {
                "content_id": f"text:{hashlib.sha256(input_url[:200].encode()).hexdigest()[:12]}",
                "title": input_url[:80] if len(input_url) < 200 else "Text Content",
                "content": input_url,  # The "url" field contains the raw text
            }
        else:
            raise ValueError(f"Unknown input type: {input_type}")
    except Exception as exc:
        logger.error("[Node] extract_content failed: %s", exc)
        raise

    return {
        "content": data["content"],
        "content_id": data["content_id"],
        "content_title": data["title"],
    }


def summarize(state: PipelineState) -> dict:
    """Run LLM summarizer to extract structured concepts."""
    logger.info("[Node] summarize | content=%s", state.get("content_title", "?"))
    summary = run_summarizer(state["content"])
    return {"summary": summary}


def plan_scenes(state: PipelineState) -> dict:
    """Run LLM planner to convert concepts into a scene list."""
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
    """Generate animation code for every scene."""
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
    """Render each scene to an MP4 file — fail fast, use fallback on error."""
    logger.info("[Node] render_scenes | %d scenes", len(state.get("scenes", [])))
    updated = []
    errors = list(state.get("errors", []))

    for i, scene in enumerate(state["scenes"]):
        if not scene.get("code"):
            updated.append(scene)
            continue

        scene_id = f"{state['content_id']}_{i}"
        engine = scene["engine"]
        rendered_path = ""

        try:
            logger.info(
                "Rendering scene %d/%d | engine=%s | title=%s",
                i + 1, len(state["scenes"]), engine, scene.get("title", ""),
            )

            if engine == "remotion":
                rendered_path = render_remotion(scene["code"], scene_id=scene_id)
            else:
                rendered_path = render_manim(scene["code"], scene_id=scene_id)

            # Check duration — if too short, log warning but keep it
            duration = _probe_duration_seconds(rendered_path)
            if duration is not None and duration < MIN_SCENE_DURATION_SECONDS:
                logger.warning(
                    "Scene %d is short (%.1fs) — keeping it anyway",
                    i, duration,
                )

        except Exception as exc:
            logger.warning("Render failed for scene %r: %s", scene.get("title", ""), exc)
            errors.append(f"Render failed for '{scene['title']}': {exc}")

        if rendered_path:
            updated.append({**scene, "video_path": rendered_path})
            logger.info("Rendered scene %d: %s", i, rendered_path)
        else:
            updated.append({**scene, "video_path": ""})

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


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


# ── Public API ─────────────────────────────────────────────────────────────


def run_pipeline(
    input_url: str = "",
    *,
    content: str = "",
    content_id: str = "",
    content_title: str = "",
    input_type: str = "",
) -> dict:
    """
    Run the full pipeline synchronously.

    Accepts any of:
      - input_url: arXiv URL/ID, GitHub URL, blog URL, or raw text
      - content: Pre-fetched content text (skips extraction)
      - content_id / content_title: Optional metadata
      - input_type: Hint for content type ("arxiv", "github", "text", etc.)

    Returns:
        {
          "title": <str>,
          "content_id": <str>,
          "scenes": [{...}, ...],
          "errors": [<str>, ...]
        }
    """
    initial_state: PipelineState = {
        "input_url": input_url,
        "input_content": content,
        "input_type": input_type,
        "content": "",
        "content_id": content_id,
        "content_title": content_title,
        "summary": {},
        "scenes": [],
        "current_scene_index": 0,
        "errors": [],
    }

    graph = _get_graph()
    final_state = graph.invoke(initial_state)

    return {
        "title": final_state.get("content_title", ""),
        "content_id": final_state.get("content_id", ""),
        "scenes": [
            {
                "title": s["title"],
                "engine": s["engine"],
                "description": s["description"],
                "code": s.get("code", ""),
                "video_path": s.get("video_path", ""),
            }
            for s in final_state.get("scenes", [])
        ],
        "errors": final_state.get("errors", []),
    }
