"""
Scene Planner agent — converts summarized concepts into a list of animated scenes.

Uses Groq API (llama-3.3-70b-versatile) for classification and scene description.

Engine routing:
  math / equations / graphs / algorithms  →  manim
  architecture / pipelines / system flows →  remotion
"""

import logging
import os

from providers.groq_client import groq_chat
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

# Keep Remotion enabled by default to satisfy mixed-engine output requirements.
ENABLE_REMOTION = os.getenv("ENABLE_REMOTION", "true").lower() == "true"

PLANNER_PROMPT = """\
You are an expert at planning educational animation videos.

Given the following key concepts from a research paper, create a list of animation scenes.

Requirements:
- Create 5 to 7 scenes.
- Ensure at least one scene uses "manim" and at least one uses "remotion".
- Keep each scene focused on one concept and make descriptions concrete and visual.

For each concept decide which engine to use:
- Use "manim" for: math, equations, graphs, algorithms, matrices, proofs
- Use "remotion" for: architecture diagrams, pipelines, system workflows, UI flows

Return ONLY a JSON object in this exact format — no explanation, no markdown, just the JSON:

{{
  "scenes": [
    {{
      "title": "<short scene title>",
      "engine": "<manim or remotion>",
      "description": "<detailed description of what the animation should show>"
    }}
  ]
}}

Concepts:
{concepts}
"""


def _rebalance_engines(scenes: list[dict]) -> list[dict]:
    """Guarantee a mixed-engine plan when Remotion is enabled."""
    if not scenes or not ENABLE_REMOTION:
        for s in scenes:
            s["engine"] = "manim"
        return scenes

    has_manim = any((s.get("engine") or "").lower() == "manim" for s in scenes)
    has_remotion = any((s.get("engine") or "").lower() == "remotion" for s in scenes)

    if has_manim and has_remotion:
        return scenes

    # Promote architecture/pipeline/system scenes to Remotion first.
    remotion_keywords = ("architecture", "pipeline", "workflow", "system", "component", "framework")
    for s in scenes:
        text = f"{s.get('title', '')} {s.get('description', '')}".lower()
        if any(k in text for k in remotion_keywords):
            s["engine"] = "remotion"
            has_remotion = True
            break

    # If still no remotion and we have at least 2 scenes, force one scene to remotion.
    if not has_remotion and len(scenes) >= 2:
        scenes[1]["engine"] = "remotion"

    # Keep first scene as Manim for mathematical grounding.
    scenes[0]["engine"] = "manim"
    return scenes


def run_planner(summary: dict) -> dict:
    """
    Plan animation scenes from a summarized paper.

    Args:
        summary: Output of the summarizer agent (has "title" and "main_concepts")

    Returns:
        {"scenes": [{"title": ..., "engine": ..., "description": ...}, ...]}
    """
    concepts_text = "\n".join(
        f"- {c['name']}: {c['explanation']} | Viz idea: {c['visualization_opportunity']}"
        for c in summary.get("main_concepts", [])
    )

    prompt = PLANNER_PROMPT.format(concepts=concepts_text)

    logger.info("Running planner for %d concepts", len(summary.get("main_concepts", [])))
    raw = groq_chat(prompt)
    logger.debug("Planner raw response: %s", raw[:500])

    try:
        result: dict = extract_json(raw)
    except ValueError:
        logger.warning("Planner JSON parse failed; generating fallback scenes")
        result = {
            "scenes": [
                {
                    "title": c["name"],
                    "engine": "manim",
                    "description": c["visualization_opportunity"],
                }
                for c in summary.get("main_concepts", [])[:3]
            ]
        }

    # Ensure engine values are normalised
    for scene in result.get("scenes", []):
        if scene.get("engine", "").lower() not in ("manim", "remotion"):
            scene["engine"] = "manim"

    scenes = result.get("scenes", [])
    scenes = _rebalance_engines(scenes)
    result["scenes"] = scenes

    return result
