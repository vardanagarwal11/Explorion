"""
Coder agent — generates high-quality Manim & Remotion animation code.

Uses NVIDIA NIM (llama-3.3-70b-instruct) with detailed few-shot examples
to produce visually stunning educational animations.

For "manim" scenes  → returns Python code (Manim Scene subclass).
For "remotion" scenes → returns a React/TypeScript Remotion component.
"""

import logging
import re

from providers.nim_client import nim_generate as generate_code
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
REMOTION_FPS = 30
REMOTION_DURATION_FRAMES = 900  # 30 seconds

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MANIM PROMPT — with full working reference example
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANIM_PROMPT = """\
You are a world-class Manim animation developer who creates visually stunning, \
3Blue1Brown-style educational explainer videos. Your animations are famous for \
being beautiful, precise, and deeply informative.

Write a complete, self-contained Manim Python script for the following scene.

═══════════════════════════════════════════════════════════
REFERENCE EXAMPLE — Study this style, then create YOUR scene
═══════════════════════════════════════════════════════════

```python
from manim import *

class MainScene(Scene):
    def construct(self):
        # ── Dark gradient background ──
        bg = Rectangle(width=16, height=9, fill_color="#0f0f23", fill_opacity=1, stroke_width=0)
        self.add(bg)

        # ── Phase 1: Animated title with underline (0-4s) ──
        title = Text("Neural Network Forward Pass", font_size=42, color="#E0E0FF",
                      weight=BOLD)
        underline = Line(LEFT * 3.5, RIGHT * 3.5, color="#6C63FF", stroke_width=3)
        underline.next_to(title, DOWN, buff=0.15)
        self.play(Write(title, run_time=1.5), GrowFromCenter(underline, run_time=1.5))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(underline))
        self.wait(0.5)

        # ── Phase 2: Build a layered network diagram (4-12s) ──
        layers = []
        layer_labels = ["Input\\n(784)", "Hidden\\n(128)", "Hidden\\n(64)", "Output\\n(10)"]
        colors = ["#4FC3F7", "#66BB6A", "#FFA726", "#EF5350"]

        for i, (label, color) in enumerate(zip(layer_labels, colors)):
            nodes = VGroup()
            n_nodes = [5, 4, 3, 2][i]
            for j in range(n_nodes):
                node = Circle(radius=0.22, fill_color=color, fill_opacity=0.85,
                              stroke_color=WHITE, stroke_width=1.5)
                node.shift(UP * (j - (n_nodes - 1) / 2) * 0.7)
                nodes.add(node)
            nodes.shift(RIGHT * (i - 1.5) * 2.8)
            lbl = Text(label, font_size=16, color=WHITE)
            lbl.next_to(nodes, DOWN, buff=0.3)
            layer_group = VGroup(nodes, lbl)
            layers.append(layer_group)

        network = VGroup(*layers)
        network.center()

        for layer in layers:
            self.play(FadeIn(layer, shift=UP * 0.3), run_time=0.8)
        self.wait(1.5)

        # ── Phase 3: Animate data flowing through connections (12-20s) ──
        for i in range(len(layers) - 1):
            src_nodes = layers[i][0]
            dst_nodes = layers[i + 1][0]
            arrows = VGroup()
            for src in src_nodes:
                for dst in dst_nodes:
                    arrow = Line(src.get_right(), dst.get_left(),
                                 stroke_width=1.2, stroke_opacity=0.4, color=YELLOW)
                    arrows.add(arrow)
            self.play(Create(arrows, lag_ratio=0.05), run_time=1.2)

            # Pulse effect on destination layer
            self.play(
                *[node.animate.set_fill(YELLOW, opacity=0.95) for node in dst_nodes],
                run_time=0.5
            )
            self.play(
                *[node.animate.set_fill(layers[i+1][0][0].get_fill_color(), opacity=0.85)
                  for node in dst_nodes],
                run_time=0.5
            )
        self.wait(2)

        # ── Phase 4: Highlight output with result (20-25s) ──
        result_box = RoundedRectangle(
            width=4, height=1.5, corner_radius=0.2,
            fill_color="#1a1a3e", fill_opacity=0.9,
            stroke_color="#6C63FF", stroke_width=2
        )
        result_text = Text("Prediction: Cat (97.3%)", font_size=24, color="#81C784")
        result_group = VGroup(result_box, result_text)
        result_group.to_edge(DOWN, buff=0.8)
        self.play(FadeIn(result_group, shift=UP * 0.5))
        self.wait(3)

        # ── Phase 5: Summary fadeout (25-30s) ──
        summary = Text("Forward propagation transforms input → output",
                       font_size=28, color="#B0BEC5")
        summary.to_edge(UP, buff=0.5)
        self.play(Write(summary))
        self.wait(3)
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        self.wait(1)
```

═══════════════════════════════════════════════════════════
YOUR TASK — Create a scene matching this quality level
═══════════════════════════════════════════════════════════

VISUAL DESIGN RULES (MANDATORY):
1. ALWAYS start with a dark background: Rectangle(width=16, height=9, fill_color="#0f0f23", fill_opacity=1, stroke_width=0)
2. Use a rich color palette: "#6C63FF" (purple), "#4FC3F7" (blue), "#66BB6A" (green), "#FFA726" (orange), "#EF5350" (red), "#E0E0FF" (light text)
3. Use RoundedRectangle for cards/containers, not plain Rectangle
4. Use VGroup to organize related elements
5. Build diagrams with connected shapes — NOT just text on screen
6. Animate elements entering one by one, not all at once
7. Use Transform, ReplacementTransform for morphing between concepts
8. Add visual hierarchy: titles (font_size=42), subtitles (28), labels (18-22)

BANNED PATTERNS (will be rejected):
- Plain Text on empty/white background
- Single Rectangle or Circle without context
- No visual connections between elements (arrows, lines, brackets)
- Static screenshots — everything must animate

DURATION: The video MUST be 25-35 seconds. Include at least 6 `self.wait()` calls.

CODE RULES:
- `from manim import *`
- ONE class: `MainScene(Scene)` with `construct(self)` method
- NO VoiceoverScene, NO `if __name__`
- Must render with: `manim -ql script.py MainScene`

Scene title: {title}
Scene description: {description}

Return ONLY Python code — no explanation, no markdown fences.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REMOTION PROMPT — with full working reference example
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REMOTION_PROMPT = """\
You are a world-class Remotion developer who creates visually stunning, \
motion-graphics-quality educational videos using React. Your work looks like \
professional explainer videos from Kurzgesagt or Fireship.

Write a complete Remotion composition for the following scene.

═══════════════════════════════════════════════════════════
REFERENCE EXAMPLE — Study this style, then create YOUR scene
═══════════════════════════════════════════════════════════

```tsx
import {{ AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig }} from "remotion";

export default function MainScene() {{
  const frame = useCurrentFrame();
  const {{ fps }} = useVideoConfig();

  // ── Animated gradient background ──
  const bgHue = interpolate(frame, [0, 900], [220, 260], {{ extrapolateRight: "clamp" }});

  // ── Phase 1: Title with spring animation (0-150 frames / 0-5s) ──
  const titleProgress = spring({{ frame, fps, config: {{ damping: 12, stiffness: 100 }} }});
  const titleY = interpolate(titleProgress, [0, 1], [60, 0]);
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], {{ extrapolateRight: "clamp" }});
  const titleExit = interpolate(frame, [120, 150], [1, 0], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  // ── Phase 2: Data flow cards (150-400 frames / 5-13s) ──
  const cards = [
    {{ label: "Input Layer", icon: "\U0001f4e5", color: "#4FC3F7", delay: 150 }},
    {{ label: "Processing", icon: "\u2699\ufe0f", color: "#66BB6A", delay: 200 }},
    {{ label: "Output", icon: "\U0001f4ca", color: "#FFA726", delay: 250 }},
  ];

  // ── Phase 3: Connecting arrows (400-550 frames / 13-18s) ──
  const arrowProgress = interpolate(frame, [400, 500], [0, 1], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  // ── Phase 4: Result highlight (550-750 frames / 18-25s) ──
  const resultScale = spring({{ frame: Math.max(0, frame - 550), fps, config: {{ damping: 10 }} }});
  const resultOpacity = interpolate(frame, [550, 590], [0, 1], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  // ── Phase 5: Summary (750-900 frames / 25-30s) ──
  const summaryOpacity = interpolate(frame, [750, 790, 860, 900], [0, 1, 1, 0], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});

  return (
    <AbsoluteFill style={{{{
      background: `linear-gradient(135deg, hsl(${{bgHue}}, 35%, 8%), hsl(${{bgHue + 20}}, 40%, 14%))`,
      fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
      justifyContent: "center",
      alignItems: "center",
      overflow: "hidden"
    }}}}>

      {{/* Subtle grid pattern */}}
      <div style={{{{ position: "absolute", inset: 0, backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "40px 40px" }}}} />

      {{/* Title */}}
      <div style={{{{
        position: "absolute", top: 60,
        opacity: titleOpacity * titleExit,
        transform: `translateY(${{titleY}}px)`,
        textAlign: "center", width: "100%"
      }}}}>
        <h1 style={{{{ fontSize: 56, fontWeight: 800, color: "white", margin: 0, letterSpacing: -1 }}}}>
          Data Pipeline Architecture
        </h1>
        <div style={{{{ width: 120, height: 4, background: "linear-gradient(90deg, #6C63FF, #4FC3F7)", borderRadius: 2, margin: "16px auto" }}}} />
      </div>

      {{/* Flow cards */}}
      <div style={{{{ display: "flex", gap: 40, alignItems: "center" }}}}>
        {{cards.map((card, i) => {{
          const cardProgress = spring({{ frame: Math.max(0, frame - card.delay), fps, config: {{ damping: 14 }} }});
          const cardScale = interpolate(cardProgress, [0, 1], [0.5, 1]);
          const cardOpacity = interpolate(frame, [card.delay, card.delay + 30], [0, 1], {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }});
          return (
            <div key={{i}} style={{{{
              opacity: cardOpacity,
              transform: `scale(${{cardScale}})`,
            }}}}>
              {{/* Arrow between cards */}}
              {{i > 0 && (
                <div style={{{{
                  position: "absolute", left: -30, top: "50%",
                  width: 20, height: 3,
                  background: `linear-gradient(90deg, transparent, ${{card.color}})`,
                  opacity: arrowProgress,
                  transform: "translateY(-50%)"
                }}}} />
              )}}
              <div style={{{{
                background: "rgba(255,255,255,0.06)",
                backdropFilter: "blur(20px)",
                border: `1px solid ${{card.color}}33`,
                borderRadius: 20, padding: "32px 28px",
                textAlign: "center", width: 180,
                boxShadow: `0 8px 32px ${{card.color}}22`
              }}}}>
                <div style={{{{ fontSize: 48, marginBottom: 12 }}}}>{{card.icon}}</div>
                <div style={{{{ fontSize: 18, fontWeight: 600, color: card.color }}}}>{{card.label}}</div>
              </div>
            </div>
          );
        }})}}
      </div>

      {{/* Result box */}}
      <div style={{{{
        position: "absolute", bottom: 100,
        opacity: resultOpacity,
        transform: `scale(${{interpolate(resultScale, [0, 1], [0.8, 1])}})`,
        background: "rgba(108, 99, 255, 0.15)",
        border: "1px solid rgba(108, 99, 255, 0.4)",
        borderRadius: 16, padding: "20px 40px",
      }}}}>
        <span style={{{{ fontSize: 22, color: "#81C784", fontWeight: 600 }}}}>
          \u2713 Pipeline Complete — 99.2% Accuracy
        </span>
      </div>

      {{/* Summary */}}
      <div style={{{{
        position: "absolute", bottom: 30,
        opacity: summaryOpacity,
        fontSize: 16, color: "rgba(255,255,255,0.5)"
      }}}}>
        Scalable data processing with distributed architecture
      </div>
    </AbsoluteFill>
  );
}}
```

═══════════════════════════════════════════════════════════
YOUR TASK — Create a scene matching this quality level
═══════════════════════════════════════════════════════════

VISUAL DESIGN RULES (MANDATORY):
1. Animated gradient background using HSL and frame-based hue shift
2. Glassmorphism cards: `background: "rgba(255,255,255,0.06)"`, `backdropFilter: "blur(20px)"`, rounded corners (16-20px)
3. Use `spring()` for bouncy entrances, `interpolate()` for smooth transitions
4. Rich color palette: "#6C63FF" (purple), "#4FC3F7" (blue), "#66BB6A" (green), "#FFA726" (orange)
5. Subtle grid/dot pattern background overlay for depth
6. Box shadows with colored tints: `boxShadow: "0 8px 32px rgba(color, 0.2)"`
7. Build visual DIAGRAMS — connected cards, flowcharts, node graphs — not just text
8. 5-6 distinct phases across the full {duration_frames} frames timeline

BANNED PATTERNS (will be rejected):
- Plain text fading in on dark background with nothing else
- No visual structure (cards, boxes, diagrams, charts)
- Everything appearing at once — must be sequenced across timeline
- Generic placeholder content ("Core Concept", "Key Insight")

DURATION: {duration_frames} frames at {fps} fps = {duration_seconds} seconds total.

CODE RULES:
- Import from "remotion": AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig
- Export default function `MainScene`
- Inline styles only — no external CSS
- Must work as standalone Remotion composition

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
        code = generate_code(prompt, max_tokens=8192)

        # Strip markdown fences if the model wrapped the code anyway
        code = re.sub(r"^```(?:python|typescript|tsx|jsx|js)?\s*", "", code, flags=re.MULTILINE)
        code = re.sub(r"\s*```\s*$", "", code, flags=re.MULTILINE)
        code = code.strip()

        if _looks_valid(code, engine):
            logger.info("Valid %s code generated on attempt %d (%d chars)", engine, attempt, len(code))
            return code

        logger.warning("Generated code failed validation on attempt %d; retrying…", attempt)

    # Last resort: return high-quality placeholder so the pipeline doesn't crash
    logger.error("All %d coder attempts failed for scene %r", MAX_RETRIES, title)
    if engine == "manim":
        return _fallback_manim(title, description)
    return _fallback_remotion(title, description)


# ── Fallback templates ───────────────────────────────────────────────────────

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
        self.wait(2.5)
        self.play(FadeOut(title), FadeOut(accent))
        self.wait(0.5)

        concepts = [
            ("Step 1", "#4FC3F7", "Input"),
            ("Step 2", "#66BB6A", "Process"),
            ("Step 3", "#FFA726", "Transform"),
            ("Step 4", "#EF5350", "Output"),
        ]
        cards = VGroup()
        for i, (label, color, sub) in enumerate(concepts):
            card = RoundedRectangle(
                width=2.2, height=1.6, corner_radius=0.15,
                fill_color=color, fill_opacity=0.2,
                stroke_color=color, stroke_width=2
            )
            card_title = Text(label, font_size=22, color=color, weight=BOLD)
            card_sub = Text(sub, font_size=16, color="#B0BEC5")
            card_title.move_to(card.get_center() + UP * 0.25)
            card_sub.move_to(card.get_center() + DOWN * 0.25)
            cards.add(VGroup(card, card_title, card_sub))

        cards.arrange(RIGHT, buff=0.5)
        cards.center()

        for card in cards:
            self.play(FadeIn(card, shift=UP * 0.3), run_time=0.6)
        self.wait(2)

        arrows = VGroup()
        for i in range(len(cards) - 1):
            arrow = Arrow(
                cards[i].get_right(), cards[i + 1].get_left(),
                buff=0.15, color=YELLOW, stroke_width=2.5
            )
            arrows.add(arrow)
            self.play(GrowArrow(arrow), run_time=0.5)
        self.wait(2)

        desc_box = RoundedRectangle(
            width=10, height=1.5, corner_radius=0.15,
            fill_color="#1a1a3e", fill_opacity=0.9,
            stroke_color="#6C63FF", stroke_width=1.5
        )
        desc_text = Text("DESC_PH", font_size=20, color="#B0BEC5")
        desc_group = VGroup(desc_box, desc_text)
        desc_group.to_edge(DOWN, buff=0.8)
        self.play(FadeIn(desc_group, shift=UP * 0.3))
        self.wait(4)

        check = Text("Complete", font_size=32, color="#81C784")
        check.to_edge(UP, buff=0.5)
        self.play(Write(check))
        self.wait(3)
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        self.wait(1)
'''

_REMOTION_FALLBACK = r'''
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export default function MainScene() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const bgHue = interpolate(frame, [0, DUR_PH], [220, 260], { extrapolateRight: "clamp" });
  const titleProgress = spring({ frame, fps, config: { damping: 12 } });
  const titleY = interpolate(titleProgress, [0, 1], [50, 0]);
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const titleExit = interpolate(frame, [120, 150], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const steps = [
    { label: "Analyze", icon: "\u{1F50D}", color: "#4FC3F7", delay: 160 },
    { label: "Process", icon: "\u2699\uFE0F", color: "#66BB6A", delay: 220 },
    { label: "Visualize", icon: "\u{1F4CA}", color: "#FFA726", delay: 280 },
  ];
  const connProgress = interpolate(frame, [400, 500], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const resultScale = spring({ frame: Math.max(0, frame - 560), fps, config: { damping: 10 } });
  const resultOpacity = interpolate(frame, [550, 590], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const summaryOpacity = interpolate(frame, [750, 790, 860, DUR_PH], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, hsl(${bgHue}, 35%, 8%), hsl(${bgHue + 20}, 40%, 14%))`,
      fontFamily: "'Segoe UI', system-ui, sans-serif",
      justifyContent: "center", alignItems: "center", overflow: "hidden",
    }}>
      <div style={{ position: "absolute", inset: 0, backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
      <div style={{ position: "absolute", top: 50, opacity: titleOpacity * titleExit, transform: `translateY(${titleY}px)`, textAlign: "center", width: "100%" }}>
        <h1 style={{ fontSize: 52, fontWeight: 800, color: "white", margin: 0, letterSpacing: -1 }}>TITLE_PH</h1>
        <div style={{ width: 100, height: 4, background: "linear-gradient(90deg, #6C63FF, #4FC3F7)", borderRadius: 2, margin: "14px auto" }} />
      </div>
      <div style={{ display: "flex", gap: 50, alignItems: "center" }}>
        {steps.map((step, i) => {
          const p = spring({ frame: Math.max(0, frame - step.delay), fps, config: { damping: 14 } });
          const sc = interpolate(p, [0, 1], [0.5, 1]);
          const op = interpolate(frame, [step.delay, step.delay + 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, opacity: op, transform: `scale(${sc})` }}>
              <div style={{ background: "rgba(255,255,255,0.06)", backdropFilter: "blur(20px)", border: `1px solid ${step.color}44`, borderRadius: 20, padding: "28px 24px", textAlign: "center", width: 160, boxShadow: `0 8px 32px ${step.color}22` }}>
                <div style={{ fontSize: 44, marginBottom: 10 }}>{step.icon}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: step.color }}>{step.label}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 90, opacity: resultOpacity, transform: `scale(${interpolate(resultScale, [0, 1], [0.85, 1])})`, background: "rgba(108,99,255,0.12)", border: "1px solid rgba(108,99,255,0.35)", borderRadius: 14, padding: "16px 36px" }}>
        <span style={{ fontSize: 20, color: "#81C784", fontWeight: 600 }}>DESC_PH</span>
      </div>
      <div style={{ position: "absolute", bottom: 30, opacity: summaryOpacity, fontSize: 15, color: "rgba(255,255,255,0.4)" }}>
        Powered by AI-driven visualization
      </div>
    </AbsoluteFill>
  );
}
'''.strip()


def _fallback_manim(title: str, description: str) -> str:
    safe_title = title.replace('"', '\\"')[:50]
    safe_desc = description[:100].replace('"', '\\"')
    return _MANIM_FALLBACK.replace("TITLE_PH", safe_title).replace("DESC_PH", safe_desc)


def _fallback_remotion(title: str, description: str) -> str:
    safe_title = title.replace('`', "'").replace('"', "'")[:50]
    safe_desc = description[:100].replace('`', "'").replace('"', "'")
    dur = str(REMOTION_DURATION_FRAMES)
    return (_REMOTION_FALLBACK
            .replace("TITLE_PH", safe_title)
            .replace("DESC_PH", safe_desc)
            .replace("DUR_PH", dur))
