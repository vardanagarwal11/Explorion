"""
Sample Manim code templates for demo visualizations.

These are used when Teams 1 & 2 aren't available yet.
Replace with real generated code when integration is ready.
"""

# Simple circle animation
CIRCLE_ANIMATION = '''
from manim import *

class CircleDemo(Scene):
    def construct(self):
        circle = Circle(color=BLUE, fill_opacity=0.5)
        self.play(Create(circle))
        self.play(circle.animate.scale(2))
        self.wait()
'''

# Attention mechanism visualization
ATTENTION_DEMO = '''
from manim import *

class AttentionDemo(Scene):
    def construct(self):
        # Query, Key, Value vectors
        q = Arrow(ORIGIN, RIGHT * 2, color=RED, buff=0)
        k = Arrow(ORIGIN, UP * 2, color=GREEN, buff=0)
        v = Arrow(ORIGIN, RIGHT * 2 + UP * 2, color=BLUE, buff=0)

        q_label = Text("Q", font_size=24).next_to(q, DOWN)
        k_label = Text("K", font_size=24).next_to(k, LEFT)
        v_label = Text("V", font_size=24).next_to(v, UP)

        self.play(Create(q), Write(q_label))
        self.play(Create(k), Write(k_label))
        self.play(Create(v), Write(v_label))

        # Show attention computation
        dot = Dot(color=YELLOW).scale(2)
        self.play(FadeIn(dot))
        self.play(dot.animate.move_to(v.get_end()))
        self.wait()
'''

# Multi-head attention visualization
MULTIHEAD_DEMO = '''
from manim import *

class MultiHeadDemo(Scene):
    def construct(self):
        # Create multiple attention heads
        heads = VGroup()
        colors = [RED, GREEN, BLUE, YELLOW]

        for i, color in enumerate(colors):
            head = Circle(radius=0.5, color=color, fill_opacity=0.3)
            head.shift(RIGHT * (i - 1.5) * 1.5)
            heads.add(head)

        title = Text("Multi-Head Attention", font_size=36).to_edge(UP)

        self.play(Write(title))
        self.play(LaggedStart(*[Create(h) for h in heads], lag_ratio=0.2))

        # Combine heads
        combined = Circle(radius=1.5, color=WHITE, fill_opacity=0.2)
        combined.shift(DOWN * 2)

        self.play(*[h.animate.move_to(combined.get_center()) for h in heads])
        self.play(Create(combined))
        self.wait()
'''

# Map arxiv_id to visualization templates
SAMPLE_VISUALIZATIONS = {
    "1706.03762": [  # Attention Is All You Need
        {
            "section_id": "section-3-2",
            "concept": "Scaled Dot-Product Attention",
            "manim_code": ATTENTION_DEMO,
        },
        {
            "section_id": "section-3-3",
            "concept": "Multi-Head Attention",
            "manim_code": MULTIHEAD_DEMO,
        },
    ],
    "default": [  # Fallback for any paper
        {
            "section_id": "section-1",
            "concept": "Demo Visualization",
            "manim_code": CIRCLE_ANIMATION,
        },
    ],
}


def get_sample_visualizations(arxiv_id: str) -> list[dict]:
    """Get sample visualization templates for a paper."""
    return SAMPLE_VISUALIZATIONS.get(arxiv_id, SAMPLE_VISUALIZATIONS["default"])


# Sections to skip for visualization
SKIP_TITLES = {
    "abstract", "introduction", "related work", "related works",
    "conclusion", "conclusions", "future work",
    "acknowledgments", "acknowledgements", "references", "bibliography",
}

MAX_VISUALIZATIONS = 5


def get_visualizations_for_sections(arxiv_id: str, db_sections: list) -> list[dict]:
    """
    Pick which sections to visualize and return Manim code for each.

    For known papers (e.g., 1706.03762), returns curated visualizations
    if the section IDs match. For unknown papers, auto-picks sections
    based on content heuristics and uses the circle demo.
    """
    # Check if we have curated visualizations with matching section IDs
    if arxiv_id in SAMPLE_VISUALIZATIONS:
        curated = SAMPLE_VISUALIZATIONS[arxiv_id]
        real_ids = {s.id for s in db_sections}
        valid_curated = [v for v in curated if v["section_id"] in real_ids]
        if valid_curated:
            return valid_curated

    # Auto-pick sections to visualize
    candidates = []
    for section in db_sections:
        title_lower = section.title.lower().strip()

        if title_lower in SKIP_TITLES:
            continue

        eq_count = len(section.equations) if section.equations else 0
        content_len = len(section.content) if section.content else 0

        if content_len < 100:
            continue

        score = eq_count * 10 + (1 if content_len > 200 else 0)
        candidates.append((score, section))

    candidates.sort(key=lambda x: x[0], reverse=True)
    selected = [s for _, s in candidates[:MAX_VISUALIZATIONS]]

    # Fallback: first non-skipped section
    if not selected:
        for section in db_sections:
            if section.title.lower().strip() not in SKIP_TITLES:
                selected = [section]
                break

    # Last resort: first section
    if not selected and db_sections:
        selected = [db_sections[0]]

    return [
        {
            "section_id": section.id,
            "concept": section.title,
            "manim_code": CIRCLE_ANIMATION,
        }
        for section in selected
    ]
