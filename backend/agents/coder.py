"""
Coder agent - generates high-quality Manim animation code.

For scenes -> returns Python code (Manim Scene subclass).
"""

import logging
import pathlib
import re
from functools import lru_cache

from providers.nim_client import nim_generate as generate_code


@lru_cache(maxsize=1)
def _load_manim_docs() -> str:
    """Load scraped Manim API reference (backend/assets/manim_reference.txt)."""
    p = pathlib.Path(__file__).resolve().parent.parent / "assets" / "manim_reference.txt"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

MANIM_PROMPT = """\
You are a world-class Manim animation developer who creates visually stunning,
3Blue1Brown-style educational explainer videos.

Write a complete, self-contained Manim Python script for the following scene.

CRITICAL RULES:
1. NEVER display the scene description or any instruction text as on-screen text.
   BAD:  Text("Build a 3D graph with x, y, z axes showing...")
   GOOD: Create the actual 3D axes and animate them.
2. The scene description is YOUR PRIVATE BRIEF — it tells you what to build.
   It must NEVER appear as a Manim Text(), MathTex(), or Tex() object.
3. All on-screen text must be short labels that explain what the viewer is seeing
   (e.g. axis names, formula components) — not instructions to yourself.
4. If unsure what to animate, draw a simple geometric representation of the concept
   rather than writing the description as text.

VISUAL DESIGN RULES (MANDATORY):
1. ALWAYS start with a dark background rectangle.
2. Use a rich color palette: "#6C63FF", "#4FC3F7", "#66BB6A", "#FFA726", "#EF5350", "#E0E0FF".
3. NO OVERLAPPING:
   - Position objects with next_to/arrange/arrange_in_grid.
   - Keep generous spacing with buff values.
   - Keep ALL positions inside frame bounds: x in [-6, 6], y in [-3.5, 3.5].
4. SCENE CLEARING:
   - Fade out old groups between major phases.
5. TEXT AND FONT SIZES:
   - Keep labels concise and readable.
   - Avoid dense paragraphs and oversized blocks.
6. Use RoundedRectangle for cards/containers.
7. Use VGroup to organize related elements.
8. Build connected visual diagrams (arrows/links), not plain text slides.
9. Animate elements in sequence with lag_ratio where relevant.
10. Use Transform/ReplacementTransform for state changes.
11. PROFESSIONAL STYLE ONLY:
   - Technical, publication-grade visuals.
   - No emoji, no sticker/cartoony motifs.

BANNED PATTERNS (will be rejected):
- Plain text on empty/white background
- Isolated shape without context
- No visual connections between elements
- Static screenshot-like output
- Emoji characters or cartoon motifs

DURATION: The video MUST be 25-35 seconds and include multiple waits.

CODE RULES:
- from manim import *
- ONE class: MainScene(Scene) with construct(self)
- NO VoiceoverScene, NO if __name__
- Use only Manim Community API (no deprecated or custom methods).
- Must render with: manim -ql script.py MainScene

Scene title: {title}
Scene description: {description}

--- MANIM API REFERENCE ---
{manim_docs}
--- END REFERENCE ---

RULES:
- Only use methods that appear in the reference above.
- Never call .set_glow() — it does not exist.
- scale() takes a float only, never a list.
- Transform(a, b) is one mobject to one mobject only.
- ThreeDAxes/Dot3D/Surface require class MainScene(ThreeDScene).
- Never display the scene description as on-screen Text().
- To grow something from nothing use GrowFromCenter(), not scale(0) then scale(1).

Return ONLY Python code - no explanation, no markdown fences.
"""

_MANIM_CHECKS = [r"class\s+MainScene", r"def\s+construct"]

BANNED_PATTERNS = [
    (r"\.set_glow\(", "set_glow() does not exist in Manim"),
    (r"\.animate\.scale\(\[", "scale() takes a float, not a list"),
    (r"Transform\s*\([^,]+,\s*VGroup\s*\(", "Cannot Transform into a VGroup"),
]


def validate_manim_code(code: str) -> list[str]:
    """Return list of validation error messages. Empty list = code is acceptable."""
    errors = []
    for pattern, message in BANNED_PATTERNS:
        if re.search(pattern, code, re.DOTALL):
            errors.append(message)
    has_3d = bool(re.search(r"Dot3D|ThreeDAxes|Surface\(", code))
    uses_scene = bool(re.search(r"class\s+\w+\s*\(\s*Scene\s*\)", code))
    if has_3d and uses_scene:
        errors.append("3D objects require ThreeDScene not Scene")
    return errors


def _looks_valid(code: str) -> bool:
    return all(re.search(p, code) for p in _MANIM_CHECKS)


def run_coder(scene: dict, extra_instruction: str = "") -> str:
    """
    Generate Manim code for a single scene dict.

    Args:
        scene: {"title": ..., "engine": "manim", "description": ...}
        extra_instruction: Optional string prepended to the prompt (e.g. validation retry nudge).

    Returns:
        Python source code string for Manim.
    """
    title = scene.get("title", "Untitled")
    description = scene.get("description", "")

    manim_docs = _load_manim_docs()
    prompt = MANIM_PROMPT.format(title=title, description=description, manim_docs=manim_docs)
    if extra_instruction:
        prompt = extra_instruction.strip() + "\n\n" + prompt

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("Coder attempt %d/%d | scene=%s", attempt, MAX_RETRIES, title)
        code = generate_code(prompt, max_tokens=8192, temperature=0.45)

        code = re.sub(r"^```(?:python)?\s*", "", code, flags=re.MULTILINE)
        code = re.sub(r"\s*```\s*$", "", code, flags=re.MULTILINE)
        code = code.strip()

        if _looks_valid(code):
            validation_errors = validate_manim_code(code)
            if validation_errors:
                error_str = "\n".join(f"- {e}" for e in validation_errors)
                logger.warning("Manim validation errors on attempt %d: %s", attempt, validation_errors)
                if attempt < MAX_RETRIES:
                    retry_prompt = prompt + "\n\nYour previous code was rejected. Fix these issues:\n" + error_str
                    code = generate_code(retry_prompt, max_tokens=8192, temperature=0.45)
                    code = re.sub(r"^```(?:python)?\s*", "", code, flags=re.MULTILINE)
                    code = re.sub(r"\s*```\s*$", "", code, flags=re.MULTILINE)
                    code = code.strip()
                    if _looks_valid(code) and not validate_manim_code(code):
                        logger.info("Valid Manim code after validation retry (%d chars)", len(code))
                        return code
                else:
                    logger.warning("Returning code despite validation errors (no retries left)")
                return code
            logger.info("Valid Manim code generated on attempt %d (%d chars)", attempt, len(code))
            return code

        logger.warning("Generated code failed validation on attempt %d; retrying", attempt)

    logger.error("All %d coder attempts failed for scene %r", MAX_RETRIES, title)
    return _fallback_manim(title, description)


_MANIM_FALLBACK = '''\
from manim import *

class MainScene(Scene):
    def construct(self):
        bg = Rectangle(width=16, height=9, fill_color="#0f0f23", fill_opacity=1, stroke_width=0)
        self.add(bg)

        title = Text("TITLE_PH", font_size=42, color="#E0E0FF", weight=BOLD)
        accent = Line(LEFT * 3, RIGHT * 3, color="#6C63FF", stroke_width=3)
        accent.next_to(title, DOWN, buff=0.15)
        self.play(Write(title, run_time=1.5), GrowFromCenter(accent))
        self.wait(2)

        card = RoundedRectangle(
            width=9.5, height=2.0, corner_radius=0.2,
            fill_color="#1a1a3e", fill_opacity=0.9,
            stroke_color="#4FC3F7", stroke_width=2,
        )
        text = Text("DESC_PH", font_size=24, color="#B0BEC5")
        content = VGroup(card, text)
        content.to_edge(DOWN, buff=0.8)

        self.play(FadeIn(content, shift=UP * 0.4))
        self.wait(3)

        self.play(*[FadeOut(mob) for mob in self.mobjects])
        self.wait(1)
'''


def _fallback_manim(title: str, description: str) -> str:
    safe_title = title.replace('"', '\\"')[:50]
    safe_desc = description[:100].replace('"', '\\"')
    return _MANIM_FALLBACK.replace("TITLE_PH", safe_title).replace("DESC_PH", safe_desc)
