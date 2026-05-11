"""
Example: Voiceover Data Flow Animation

Shows narrated data flow visualization.
"""

from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class VoiceoverDataFlowExample(VoiceoverScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_speech_service(GTTSService(transcription_model=None))
    
    def construct(self):
        with self.voiceover(text="Data processing pipeline") as tracker:
            title = Text("Data Pipeline", font_size=40)
            self.play(Write(title), run_time=tracker.duration)
        
        self.play(FadeOut(title))
        
        # Create input stage
        with self.voiceover(text="Data enters through the input stage") as tracker:
            input_circle = Circle(radius=0.5, color=BLUE).shift(LEFT * 4)
            input_label = Text("Input", font_size=18).move_to(input_circle)
            self.play(Create(input_circle), Write(input_label), run_time=tracker.duration)
        
        # Create process stage
        with self.voiceover(text="Then it gets processed") as tracker:
            process_circle = Circle(radius=0.5, color=YELLOW).shift(RIGHT * 0)
            process_label = Text("Process", font_size=18).move_to(process_circle)
            self.play(Create(process_circle), Write(process_label), run_time=tracker.duration)
        
        # Create output stage
        with self.voiceover(text="Finally, the output is generated") as tracker:
            output_circle = Circle(radius=0.5, color=GREEN).shift(RIGHT * 4)
            output_label = Text("Output", font_size=18).move_to(output_circle)
            self.play(Create(output_circle), Write(output_label), run_time=tracker.duration)
        
        # Show data flow with narration
        with self.voiceover(text="Data flows through each stage") as tracker:
            arrow1 = Arrow(input_circle.get_right(), process_circle.get_left(), color=WHITE)
            arrow2 = Arrow(process_circle.get_right(), output_circle.get_left(), color=WHITE)
            self.play(Create(arrow1), Create(arrow2), run_time=tracker.duration)
        
        self.wait()
