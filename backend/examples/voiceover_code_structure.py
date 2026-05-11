"""
Example: Voiceover Code Structure Animation

Demonstrates narrated code hierarchy visualization.
"""

from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class VoiceoverCodeStructureExample(VoiceoverScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_speech_service(GTTSService(transcription_model=None))
    
    def construct(self):
        with self.voiceover(text="Object oriented programming with class hierarchy") as tracker:
            title = Text("Class Hierarchy", font_size=40)
            self.play(Write(title), run_time=tracker.duration)
        
        self.play(FadeOut(title))
        
        # Base class
        with self.voiceover(text="We start with a base class called Animal") as tracker:
            base_box = Rectangle(width=2, height=0.6, color=PURPLE)
            base_label = Text("Animal", font_size=18).move_to(base_box)
            self.play(Create(base_box), Write(base_label), run_time=tracker.duration)
        
        # Derived class 1
        with self.voiceover(text="Dog is derived from Animal") as tracker:
            dog_box = Rectangle(width=1.5, height=0.6, color=BLUE).shift(DOWN * 2 + LEFT * 2)
            dog_label = Text("Dog", font_size=16).move_to(dog_box)
            self.play(Create(dog_box), Write(dog_label), run_time=tracker.duration)
        
        # Derived class 2
        with self.voiceover(text="And Cat is also derived from Animal") as tracker:
            cat_box = Rectangle(width=1.5, height=0.6, color=GREEN).shift(DOWN * 2 + RIGHT * 2)
            cat_label = Text("Cat", font_size=16).move_to(cat_box)
            self.play(Create(cat_box), Write(cat_label), run_time=tracker.duration)
        
        # Arrows
        with self.voiceover(text="Both inherit properties from the base class") as tracker:
            arrow_dog = Arrow(base_box.get_bottom(), dog_box.get_top(), color=WHITE)
            arrow_cat = Arrow(base_box.get_bottom(), cat_box.get_top(), color=WHITE)
            self.play(Create(arrow_dog), Create(arrow_cat), run_time=tracker.duration)
        
        self.wait()
