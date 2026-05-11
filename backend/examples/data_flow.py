"""
Example: Data Flow Animation

Demonstrates how to visualize data flowing through a system,
transformations, and the processing pipeline.
"""

from manim import *

class DataFlowExample(Scene):
    def construct(self):
        title = Text("Data Processing Pipeline", font_size=40)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))
        
        # Create stages
        stages = []
        labels = ["Input", "Process", "Output"]
        for i, label in enumerate(labels):
            x = -4 + i * 4
            circle = Circle(radius=0.5, color=BLUE_B).shift(RIGHT * x)
            text = Text(label, font_size=18).move_to(circle)
            stages.append((circle, text))
            self.play(Create(circle), Write(text), run_time=0.5)
        
        self.wait(0.5)
        
        # Draw arrows between stages
        for i in range(len(stages) - 1):
            arrow = Arrow(
                stages[i][0].get_right(),
                stages[i+1][0].get_left(),
                color=GREEN
            )
            self.play(Create(arrow), run_time=0.5)
        
        self.wait(2)
        
        # Animate data flow
        dot = Dot(color=RED)
        dot.move_to(stages[0][0])
        self.play(Create(dot))
        
        for i in range(len(stages) - 1):
            self.play(
                dot.animate.move_to(stages[i+1][0]),
                run_time=1
            )
            self.wait(0.5)
