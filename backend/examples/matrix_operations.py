"""
Example: Matrix Operations Animation

Visualizes matrix transformations, multiplications, and decompositions.
"""

from manim import *

class MatrixExample(Scene):
    def construct(self):
        title = Text("Matrix Multiplication", font_size=40)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))
        
        # Create matrices
        matrix1 = Matrix([[1, 2], [3, 4]], h_buff=1.5)
        matrix1.shift(LEFT * 3)
        
        times = Text("×", font_size=40)
        
        matrix2 = Matrix([[5, 6], [7, 8]], h_buff=1.5)
        matrix2.shift(RIGHT * 3)
        
        self.play(Write(matrix1), Write(times), Write(matrix2))
        self.wait(1)
        
        # Show result
        result = Matrix([[19, 22], [43, 50]], h_buff=1.5)
        result.to_edge(DOWN)
        equals = Text("=", font_size=40).next_to(result, LEFT)
        
        self.play(Write(equals), Write(result))
        self.wait(2)
