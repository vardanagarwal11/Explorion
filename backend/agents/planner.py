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
You are an expert storyboard artist for educational animation videos. \
Your descriptions are so specific that an animator could build the scene \
without asking any follow-up questions.

Given the following concepts, create exactly 3 animation scenes.

RULES:
- Exactly 3 scenes, no more, no less.
- At least one "manim" scene and at least one "remotion" scene.
- Use "manim" for: math equations, graphs, algorithms, matrices, geometric proofs, data transformations
- Use "remotion" for: architecture diagrams, pipelines, system workflows, comparisons, timelines

CRITICAL — Your descriptions must be SPECIFIC and VISUAL. Examples:

BAD description: "Visualize the attention mechanism"
GOOD description: "Build a 4x4 grid of colored cells representing token embeddings. \
Animate spotlight highlights sweeping across rows to show query-key attention. \
Draw weighted arrows between cells — thicker arrows = higher attention weight. \
Show the final weighted sum collecting into a single output vector on the right side. \
Use blue (#4FC3F7) for queries, green (#66BB6A) for keys, orange (#FFA726) for values."

BAD description: "Show the model architecture"
GOOD description: "Create a vertical stack of 3 glassmorphism cards: 'Encoder', 'Attention', 'Decoder'. \
Animate data flowing as glowing particles from top card through connecting arrows to bottom card. \
Each card expands on hover to reveal internal components as smaller sub-cards. \
Add a progress bar at the bottom filling up as data moves through the pipeline."

Return ONLY a JSON object — no explanation, no markdown:

{{
  "scenes": [
    {{
      "title": "<short scene title, max 5 words>",
      "engine": "<manim or remotion>",
      "description": "<SPECIFIC visual description: what shapes, colors (#hex), \
animations, and layout to use. At least 3 sentences. Include color codes.>"
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
                    "engine": "manim" if i == 0 else "remotion",
                    "description": c["visualization_opportunity"],
                }
                for i, c in enumerate(summary.get("main_concepts", [])[:2])
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
