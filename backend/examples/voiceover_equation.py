"""
Example: Voiceover Equation Animation

Demonstrates how to add narration to equation visualizations.
Uses manim-voiceover for synchronized narration.
"""

from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class VoiceoverEquationExample(VoiceoverScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_speech_service(GTTSService(transcription_model=None))
    
    def construct(self):
        # Title with narration
        with self.voiceover(text="Today we will learn about linear equations"):
            title = Text("Linear Equations", font_size=48)
            self.play(Write(title))
        self.wait()
        
        # Clear the title
        self.play(FadeOut(title))
        
        # First equation with narration
        with self.voiceover(text="The equation y equals mx plus b represents a straight line") as tracker:
            eq = MathTex(r"y = mx + b")
            self.play(Write(eq), run_time=tracker.duration)
        self.wait()
        
        # Explain the slope
        with self.voiceover(text="Here, m is the slope of the line") as tracker:
            slope_label = Text("m = slope", font_size=24).next_to(eq, DOWN)
            self.play(Write(slope_label), run_time=tracker.duration)
        self.wait()
        
        # Cleanup
        self.play(FadeOut(eq, slope_label))
