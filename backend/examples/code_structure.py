"""
Example: Code Structure Visualization

Visualizes code hierarchies, class relationships, and function calls.
"""

from manim import *

class CodeStructureExample(Scene):
    def construct(self):
        title = Text("Class Hierarchy", font_size=40)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))
        
        # Base class
        base_box = Rectangle(width=2, height=0.6, color=PURPLE)
        base_label = Text("Animal", font_size=18).move_to(base_box)
        self.play(Create(base_box), Write(base_label))
        self.wait(0.5)
        
        # Derived classes
        dog_box = Rectangle(width=1.5, height=0.6, color=BLUE).shift(DOWN * 2 + LEFT * 2)
        dog_label = Text("Dog", font_size=16).move_to(dog_box)
        
        cat_box = Rectangle(width=1.5, height=0.6, color=GREEN).shift(DOWN * 2 + RIGHT * 2)
        cat_label = Text("Cat", font_size=16).move_to(cat_box)
        
        self.play(Create(dog_box), Write(dog_label))
        self.play(Create(cat_box), Write(cat_label))
        
        # Inheritance arrows
        arrow_dog = Arrow(base_box.get_bottom(), dog_box.get_top(), color=WHITE)
        arrow_cat = Arrow(base_box.get_bottom(), cat_box.get_top(), color=WHITE)
        
        self.play(Create(arrow_dog), Create(arrow_cat))
        self.wait(2)
