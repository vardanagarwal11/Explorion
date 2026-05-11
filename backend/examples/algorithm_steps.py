"""
Example: Algorithm Steps Animation

Shows how to visualize algorithms step-by-step with pseudocode
and intermediate results.
"""

from manim import *

class AlgorithmExample(Scene):
    def construct(self):
        title = Text("Bubble Sort Algorithm", font_size=40)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))
        
        # Create array visualization
        numbers = [3, 1, 4, 1, 5]
        rects = []
        
        for i, num in enumerate(numbers):
            rect = Rectangle(width=0.8, height=0.8, color=BLUE)
            rect.shift(RIGHT * (i - 2) * 1)
            num_text = Text(str(num), font_size=24).move_to(rect)
            rects.append((rect, num_text, num))
            self.play(Create(rect), Write(num_text), run_time=0.3)
        
        self.wait(1)
        
        # Simulate a few swaps
        self.play(
            rects[0][0].animate.set_color(RED),
            rects[1][0].animate.set_color(RED),
        )
        self.wait(0.5)
        
        # Highlight comparison
        comparison = Text("Compare: 3 vs 1", font_size=20).to_edge(UP)
        self.play(Write(comparison))
        self.wait(1)
        
        self.play(FadeOut(comparison))
