"""
Example: Architecture Diagram Animation

Shows how to create and animate system architecture diagrams,
component relationships, and data flow between modules.
"""

from manim import *

class ArchitectureExample(Scene):
    def construct(self):
        # Title
        title = Text("System Architecture", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))
        
        # Create components
        comp1 = Rectangle(width=2, height=1, color=BLUE).shift(LEFT * 3)
        label1 = Text("API", font_size=20).move_to(comp1)
        
        comp2 = Rectangle(width=2, height=1, color=GREEN).shift(RIGHT * 3)
        label2 = Text("Database", font_size=20).move_to(comp2)
        
        # Draw components
        self.play(Create(comp1), Write(label1))
        self.play(Create(comp2), Write(label2))
        self.wait(1)
        
        # Connection arrow
        arrow = Arrow(comp1.get_right(), comp2.get_left(), color=WHITE)
        self.play(Create(arrow))
        self.wait(1)
        
        # Highlight data flow
        data_label = Text("Data", font_size=16).move_to(arrow)
        self.play(Write(data_label))
        self.wait(2)
        
        # Cleanup
        self.play(
            FadeOut(comp1, comp2, label1, label2, arrow, data_label)
        )
