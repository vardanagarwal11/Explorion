"""
Scene Planner agent — converts summarized concepts into a list of animated scenes.

Uses Groq API (llama-3.3-70b-versatile) for scene planning.

Engine routing:
    all scenes → manim
"""

import logging

from providers.groq_client import groq_chat
from providers.nim_client import nim_generate
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """\
You are an expert storyboard artist for educational animation videos. \
Your descriptions are so specific that an animator could build the scene \
without asking any follow-up questions.

Given the following concepts, create EXACTLY ONE animation scene for EACH concept provided, in the SAME ORDER as the concepts list.

RULES:
- You must create exactly as many scenes as there are concepts (e.g. if 5 concepts are provided, create exactly 5 scenes), in the same order.
- Use "manim" for every scene.

CRITICAL — Your descriptions must be VISUAL and TECHNICAL: specify objects, positions, and colors (#hex). Avoid sentences that sound like instructions to the viewer (e.g. "draw this…", "from x and y plot…", "show the user…"). Write as a spec for an animator, not as text to display on screen. Examples:

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
            "engine": "manim",
      "description": "<SPECIFIC visual description: what shapes, colors (#hex), \
animations, and layout to use. At least 3 sentences. Include color codes.>"
    }}
  ]
}}

Concepts:
{concepts}
"""


def _force_manim(scenes: list[dict]) -> list[dict]:
    """Normalize all planned scenes to Manim-only execution."""
    for s in scenes:
        s["engine"] = "manim"
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
    
    # Try using NIM with OpenAI OSS 120b first
    try:
        raw = nim_generate(prompt=prompt, model="openai/gpt-oss-120b", temperature=0.7)
    except Exception as e:
        logger.warning(f"OpenAI OSS 120b failed, falling back to Groq: {e}")
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
                for i, c in enumerate(summary.get("main_concepts", [])[:2])
            ]
        }

    # Ensure engine values are normalised
    for scene in result.get("scenes", []):
        scene["engine"] = "manim"

    scenes = result.get("scenes", [])
    scenes = _force_manim(scenes)
    result["scenes"] = scenes

    return result
