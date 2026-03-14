"""
Coder agent — uses NVIDIA NIM (llama-3.3-70b-instruct) for animation code generation.

For "manim" scenes  → returns Python code (Manim Scene subclass).
For "remotion" scenes → returns a React/TypeScript Remotion component.

Retries up to MAX_RETRIES times if the generated code looks invalid.
"""

import logging
import re

from providers.nim_client import nim_generate as generate_code
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
REMOTION_FPS = 30
REMOTION_DURATION_FRAMES = 900  # 30 seconds

MANIM_PROMPT = """\
You are an expert Manim animation developer creating educational explainer videos.

Write a complete, self-contained Manim Python script for the following scene.

CRITICAL DURATION RULES — the video MUST be 20 to 30 seconds long:
- You MUST include at least 6 separate `self.wait()` calls throughout the animation.
- Use `self.wait(3)` to `self.wait(5)` between each major phase for the viewer to absorb the content.
- Build the scene in at least 6-8 sequential visual beats:
  1. Title/intro (Write title, wait 3s)
  2. Setup/context (show initial elements, wait 3s)
  3. First concept (animate transformation, wait 3s)
  4. Second concept (add detail, wait 3s)
  5. Key insight (highlight result, wait 3s)
  6. Summary/recap (show final state, wait 4s)

Code rules:
- Import from manim: `from manim import *`
- Define exactly ONE class named `MainScene` that inherits from `Scene`
- Implement the `construct(self)` method with the full animation
- Use only standard Manim objects: Text, MathTex, Arrow, Rectangle, Circle, VGroup, etc.
- Do NOT use VoiceoverScene or any manim-voiceover imports
- Do NOT include `if __name__ == "__main__"` blocks
- The code must be renderable with: `manim -ql script.py MainScene`
- Keep Text font_size between 24 and 48 to stay visible
- Use colors like BLUE, YELLOW, GREEN, RED, WHITE for visual clarity

Scene title: {title}
Scene description: {description}

Return ONLY the Python code — no explanation, no markdown fences.
"""

REMOTION_PROMPT = """\
You are an expert Remotion (React + TypeScript) animation developer creating educational videos.

Write a complete Remotion composition for the following scene.

CRITICAL DURATION RULES — the video is {duration_frames} frames at {fps} fps ({duration_seconds} seconds):
- Spread your animations across the FULL {duration_frames} frames
- Create at least 5-6 distinct visual phases, each lasting 4-6 seconds (120-180 frames)
- Use `interpolate()` with frame ranges that cover the entire timeline
- Phase 1 (frames 0-150): Title and intro
- Phase 2 (frames 150-300): Setup/context
- Phase 3 (frames 300-500): Core concept animation
- Phase 4 (frames 500-700): Key insight or comparison
- Phase 5 (frames 700-{duration_frames}): Summary and conclusion

Code rules:
- Import from "remotion": `import {{ AbsoluteFill, useCurrentFrame, interpolate, spring }} from "remotion"`
- Export a default function component named `MainScene`
- Use inline styles; no external CSS imports
- The component must work as a standalone Remotion composition
- Use modern, visually appealing colors and gradients
- Include smooth transitions between phases using interpolate()

Scene title: {title}
Scene description: {description}

Return ONLY the TypeScript/JSX code — no explanation, no markdown fences.
"""

# Minimum sanity checks
_MANIM_CHECKS = [r"class\s+MainScene", r"def\s+construct"]
_REMOTION_CHECKS = [r"export\s+default", r"AbsoluteFill|useCurrentFrame"]


def _looks_valid(code: str, engine: str) -> bool:
    checks = _MANIM_CHECKS if engine == "manim" else _REMOTION_CHECKS
    return all(re.search(p, code) for p in checks)


def run_coder(scene: dict) -> str:
    """
    Generate animation code for a single scene dict.

    Args:
        scene: {"title": ..., "engine": "manim"|"remotion", "description": ...}

    Returns:
        Source code string (Python for manim, TSX for remotion).

    Raises:
        RuntimeError: if valid code could not be generated after MAX_RETRIES attempts.
    """
    engine = scene.get("engine", "manim").lower()
    title = scene.get("title", "Untitled")
    description = scene.get("description", "")

    template = MANIM_PROMPT if engine == "manim" else REMOTION_PROMPT
    prompt = template.format(
        title=title,
        description=description,
        duration_frames=REMOTION_DURATION_FRAMES,
        fps=REMOTION_FPS,
        duration_seconds=REMOTION_DURATION_FRAMES // REMOTION_FPS,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(
            "Coder attempt %d/%d | engine=%s | scene=%s",
            attempt, MAX_RETRIES, engine, title,
        )
        code = generate_code(prompt)

        # Strip markdown fences if the model wrapped the code anyway
        code = re.sub(r"^```(?:python|typescript|tsx|jsx|js)?\s*", "", code, flags=re.MULTILINE)
        code = re.sub(r"\s*```\s*$", "", code, flags=re.MULTILINE)
        code = code.strip()

        if _looks_valid(code, engine):
            logger.info("Valid %s code generated on attempt %d", engine, attempt)
            return code

        logger.warning("Generated code failed validation on attempt %d; retrying…", attempt)

    # Last resort: return placeholder so the pipeline doesn't crash
    logger.error("All %d coder attempts failed for scene %r", MAX_RETRIES, title)
    if engine == "manim":
        return _fallback_manim(title, description)
    return _fallback_remotion(title, description)


# ── Fallback templates ────────────────────────────────────────────────────────

def _fallback_manim(title: str, description: str) -> str:
    safe_title = title.replace('"', '\\"')
    safe_desc = description[:80].replace('"', '\\"')
    return f'''\
from manim import *

class MainScene(Scene):
    def construct(self):
        # Phase 1: Title (0-5s)
        title = Text("{safe_title}", font_size=40, color=BLUE)
        self.play(Write(title), run_time=2)
        self.wait(3)

        # Phase 2: Description (5-10s)
        desc = Text("{safe_desc}", font_size=24)
        desc.next_to(title, DOWN, buff=0.5)
        self.play(FadeIn(desc, shift=UP))
        self.wait(3)

        # Phase 3: Visual element (10-16s)
        self.play(FadeOut(title), FadeOut(desc))
        box = Rectangle(width=8, height=3, color=BLUE, fill_opacity=0.2)
        label = Text("Core Concept", font_size=28, color=YELLOW)
        label.move_to(box)
        self.play(Create(box), Write(label))
        self.wait(4)

        # Phase 4: Arrow flow (16-21s)
        arrow = Arrow(LEFT * 3, RIGHT * 3, buff=0.2, color=GREEN)
        arrow.next_to(box, DOWN, buff=0.5)
        self.play(GrowArrow(arrow))
        self.wait(3)

        # Phase 5: Summary (21-27s)
        self.play(FadeOut(box), FadeOut(label), FadeOut(arrow))
        recap = Text("Key Takeaway", font_size=36, color=GREEN)
        self.play(Write(recap))
        self.wait(4)
        self.play(FadeOut(recap))
        self.wait(1)
'''


def _fallback_remotion(title: str, description: str) -> str:
    safe_title = title.replace("`", "'").replace('"', "'")
    safe_desc = description[:80].replace("`", "'").replace('"', "'")
    return f'''\
import {{ AbsoluteFill, useCurrentFrame, interpolate }} from "remotion";

export default function MainScene() {{
  const frame = useCurrentFrame();
  const totalFrames = {REMOTION_DURATION_FRAMES};

  // Phase 1: Title intro (frames 0-150)
  const titleOpacity = interpolate(frame, [0, 40], [0, 1], {{ extrapolateRight: "clamp" }});
  const titleY = interpolate(frame, [0, 40], [30, 0], {{ extrapolateRight: "clamp" }});

  // Phase 2: Description (frames 150-300)
  const descOpacity = interpolate(frame, [150, 190], [0, 1], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  // Phase 3: Concept (frames 300-500)
  const conceptOpacity = interpolate(frame, [300, 340], [0, 1], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});
  const conceptScale = interpolate(frame, [300, 380], [0.8, 1], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  // Phase 4: Insight (frames 500-700)
  const insightOpacity = interpolate(frame, [500, 540], [0, 1], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  // Phase 5: Outro (frames 700-900)
  const outroOpacity = interpolate(frame, [700, 740, 860, totalFrames], [0, 1, 1, 0], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  return (
    <AbsoluteFill style={{{{ background: "linear-gradient(135deg, #0d1b2a, #1b263b)", justifyContent: "center", alignItems: "center", fontFamily: "Segoe UI, sans-serif" }}}}>
      <div style={{{{ textAlign: "center", color: "white", width: 900 }}}}>
        <h1 style={{{{ fontSize: 52, opacity: titleOpacity, transform: `translateY(${{titleY}}px)`, marginBottom: 20 }}}}>{safe_title}</h1>
        <p style={{{{ fontSize: 24, opacity: descOpacity, lineHeight: 1.6 }}}}>{safe_desc}</p>
        <div style={{{{ marginTop: 40, opacity: conceptOpacity, transform: `scale(${{conceptScale}})` }}}}>
          <div style={{{{ background: "rgba(255,255,255,0.1)", borderRadius: 16, padding: "30px 40px", display: "inline-block" }}}}>
            <p style={{{{ fontSize: 28, color: "#64B5F6" }}}}>▶ Core Concept</p>
          </div>
        </div>
        <p style={{{{ fontSize: 22, opacity: insightOpacity, marginTop: 30, color: "#81C784" }}}}>💡 Key Insight</p>
        <p style={{{{ fontSize: 20, opacity: outroOpacity, marginTop: 20, color: "#FFB74D" }}}}>✨ Summary &amp; Takeaway</p>
      </div>
    </AbsoluteFill>
  );
}}
'''
