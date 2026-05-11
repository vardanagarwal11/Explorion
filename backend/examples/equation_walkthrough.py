"""
Example: Equation Walkthrough Animation

This example shows how to animate mathematical equations,
step by step, with explanations and visualizations.
"""

from manim import *

class EquationExample(Scene):
    def construct(self):
        # Title
        title = Text("Understanding Equations", font_size=48)
        self.play(Write(title))
        self.wait(1)
        
        # Clear and move on
        self.play(FadeOut(title))
        
        # First equation
        eq1 = MathTex(r"y = mx + b")
        self.play(Write(eq1))
        self.wait(2)
        
        # Label the parts
        label_m = Text("slope", font_size=24).next_to(eq1, DOWN)
        self.play(Write(label_m))
        self.wait(1)
        
        self.play(FadeOut(eq1, label_m))
        
        # More complex equation
        eq2 = MathTex(r"\frac{\partial L}{\partial w} = -\eta \nabla L")
        self.play(Write(eq2))
        self.wait(2)
        
        self.play(FadeOut(eq2))
