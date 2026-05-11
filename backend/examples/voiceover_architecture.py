"""
Example: Voiceover Architecture Animation

Demonstrates narration for architecture diagrams.
"""

from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class VoiceoverArchitectureExample(VoiceoverScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_speech_service(GTTSService(transcription_model=None))
    
    def construct(self):
        # Title
        with self.voiceover(text="System architecture diagram") as tracker:
            title = Text("System Architecture", font_size=40)
            self.play(Write(title), run_time=tracker.duration)
        
        self.play(FadeOut(title))
        
        # Create API component
        with self.voiceover(text="First, we have the API layer") as tracker:
            api_box = Rectangle(width=2, height=1, color=BLUE).shift(LEFT * 3)
            api_label = Text("API", font_size=20).move_to(api_box)
            self.play(Create(api_box), Write(api_label), run_time=tracker.duration)
        
        # Create Database component
        with self.voiceover(text="And the database layer") as tracker:
            db_box = Rectangle(width=2, height=1, color=GREEN).shift(RIGHT * 3)
            db_label = Text("Database", font_size=20).move_to(db_box)
            self.play(Create(db_box), Write(db_label), run_time=tracker.duration)
        
        # Show connection
        with self.voiceover(text="They communicate through data queries") as tracker:
            arrow = Arrow(api_box.get_right(), db_box.get_left(), color=WHITE)
            self.play(Create(arrow), run_time=tracker.duration)
        
        self.wait()
