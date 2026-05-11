"""
Example: 3D Network Visualization

Shows how to create 3D network graphs and visualizations.
"""

from manim import *

class ThreeDNetworkExample(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=45 * DEGREES)
        
        title = Text("3D Network Topology", font_size=40)
        title.to_edge(UP)
        self.add_fixed_in_frame_mobjects(title)
        
        # Create 3D points (nodes)
        nodes = []
        positions = [
            np.array([1, 1, 0]),
            np.array([-1, 1, 0]),
            np.array([1, -1, 0]),
            np.array([-1, -1, 0]),
        ]
        
        for pos in positions:
            dot = Dot3D(point=pos, color=BLUE, radius=0.2)
            nodes.append(dot)
            self.add(dot)
        
        # Add connections
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                line = Line3D(positions[i], positions[j], color=GREEN)
                self.add(line)
        
        self.wait(2)
