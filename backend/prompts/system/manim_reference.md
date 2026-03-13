# Manim Quick Reference for AI Code Generation

You are an expert at generating Manim Community Edition code for mathematical animations.
Use this reference to create clean, working Manim visualizations.

## Basic Structure

```python
from manim import *

class MyScene(Scene):
    def construct(self):
        # All animation code goes here
        pass
```

## Core Mobjects (Visual Objects)

### Text and Math
- `Text("Hello", font_size=36, color=WHITE)` - Regular text
- `MathTex(r"\int_0^1 x^2 dx", font_size=36)` - LaTeX math equations
- `Tex(r"Some \textbf{text}")` - LaTeX text with formatting

### Shapes
- `Circle(radius=1, color=BLUE, fill_opacity=0.5)`
- `Square(side_length=2, color=RED)`
- `Rectangle(width=3, height=2, color=GREEN)`
- `RoundedRectangle(width=3, height=1, corner_radius=0.2)`
- `Dot(point=ORIGIN, color=RED, radius=0.08)`
- `Ellipse(width=4, height=2)`

### Lines and Arrows
- `Line(start=LEFT, end=RIGHT, color=WHITE)`
- `Arrow(start=LEFT, end=RIGHT, color=YELLOW, buff=0.1)`
- `DoubleArrow(start=LEFT, end=RIGHT)`
- `DashedLine(start=LEFT, end=RIGHT)`
- `CurvedArrow(start_point, end_point)`

### Groups
- `VGroup(*mobjects)` - Group multiple objects
- `group.arrange(DOWN, buff=0.5)` - Arrange vertically
- `group.arrange(RIGHT, buff=0.3)` - Arrange horizontally

### Matrices and Tables
- `Matrix([[1, 2], [3, 4]])` - Display a matrix
- `matrix.get_rows()` - Get row groups
- `matrix.get_columns()` - Get column groups

## Screen Dimensions and Safe Areas

### Screen Bounds
- **Full frame**: x in [-7.1, 7.1], y in [-4.0, 4.0]
- **Safe area**: x in [-6.0, 6.0], y in [-3.5, 3.5] (recommended)
- **Aspect ratio**: 16:9 (1920x1080 at 1080p)

### Positioning Guidelines
```python
# SAFE: Within safe area
element.move_to(RIGHT * 5 + UP * 2)  # OK: 5 < 6, 2 < 3.5

# RISKY: Near edge
element.move_to(RIGHT * 7)  # May clip at edge

# DANGEROUS: Off screen
element.move_to(RIGHT * 8)  # WILL be off screen!
```

## Positioning (CRITICAL for avoiding overlaps)

### Absolute Positioning (Use Sparingly)
- `obj.move_to(ORIGIN)` - Center of screen
- `obj.move_to(UP * 2 + RIGHT * 3)` - Specific coordinates

### Edge Positioning (ALWAYS use buff)
- `obj.to_edge(UP, buff=0.5)` - Top edge with margin
- `obj.to_edge(DOWN, buff=0.5)` - Bottom edge with margin
- `obj.to_edge(LEFT, buff=0.5)` / `obj.to_edge(RIGHT, buff=0.5)`
- `obj.to_corner(UL, buff=0.5)` - Upper-left corner (UL, UR, DL, DR)

### Relative Positioning (PREFERRED - prevents overlaps)
- `obj.next_to(other, RIGHT, buff=0.5)` - Next to another object with spacing
- `obj.next_to(other, DOWN, buff=0.3)` - Below another object
- `obj.shift(RIGHT * 2 + UP)` - Move relative to current position

### Group Layout (BEST for multiple elements)
```python
# GOOD: Use arrange() with buff for consistent spacing
elements = VGroup(elem1, elem2, elem3)
elements.arrange(DOWN, buff=0.5)  # Stack vertically
elements.arrange(RIGHT, buff=0.3)  # Arrange horizontally

# Position the group
elements.to_edge(UP, buff=0.5)  # Near top with margin
elements.move_to(ORIGIN)  # Center the group
```

### Directions (Constants)
- `UP`, `DOWN`, `LEFT`, `RIGHT`, `ORIGIN`
- `UL` (upper-left), `UR`, `DL`, `DR`
- Combine: `UP * 2 + RIGHT * 3`

## Spatial Best Practices (CRITICAL)

### Avoid Overlaps
```python
# BAD: Hardcoded positions can overlap
title.shift(UP * 2)
equation.shift(UP * 2)  # OVERLAPS with title!

# GOOD: Use relative positioning
title.to_edge(UP, buff=0.5)
equation.next_to(title, DOWN, buff=0.5)  # Always below title
```

### Always Use buff Parameter
```python
# BAD: Elements may touch
label.next_to(box, RIGHT)  # No spacing!

# GOOD: Explicit spacing
label.next_to(box, RIGHT, buff=0.3)  # Clear separation
```

### Clear Scene Between Sections
```python
# Good practice for multi-scene visualizations
self.play(FadeOut(*self.mobjects))  # Clear everything
self.wait(0.5)  # Brief pause
# Now add new content without overlap
```

### Check Element Sizes
```python
# Get dimensions for layout calculations
width = element.get_width()
height = element.get_height()
center = element.get_center()
top = element.get_top()
bottom = element.get_bottom()
left_edge = element.get_left()
right_edge = element.get_right()
```

## Colors (Constants)

Primary: `BLUE`, `RED`, `GREEN`, `YELLOW`, `ORANGE`, `PURPLE`
Neutral: `WHITE`, `GRAY`, `DARK_GRAY`, `BLACK`
Special: `TEAL`, `PINK`, `MAROON`, `GOLD`
Shades: `BLUE_A`, `BLUE_B`, `BLUE_C`, `BLUE_D`, `BLUE_E` (light to dark)

## Animations

### Creating Objects
- `Create(shape)` - Draw a shape
- `Write(text)` - Handwriting effect for text/math
- `FadeIn(obj)` - Fade in
- `FadeIn(obj, shift=UP)` - Fade in from below
- `FadeOut(obj)` - Fade out
- `GrowFromCenter(obj)` - Grow from center point

### Transformations
- `Transform(obj1, obj2)` - Morph obj1 into obj2
- `ReplacementTransform(obj1, obj2)` - Replace obj1 with obj2
- `obj.animate.shift(RIGHT)` - Animate a property change
- `obj.animate.scale(2)` - Animate scaling
- `obj.animate.set_color(RED)` - Animate color change
- `obj.animate.rotate(PI/2)` - Animate rotation

### Highlights and Emphasis
- `Circumscribe(obj, color=YELLOW)` - Draw circle around
- `Indicate(obj)` - Pulse/highlight effect
- `Flash(point, color=YELLOW)` - Flash at a point
- `FocusOn(obj)` - Focus attention on object
- `Wiggle(obj)` - Wiggle effect

### Removing Objects
- `FadeOut(obj)` - Fade out
- `Uncreate(shape)` - Reverse of Create
- `Unwrite(text)` - Reverse of Write

## Animation Control

### Playing Animations
```python
self.play(animation)  # Single animation
self.play(Create(circle), Write(text))  # Multiple simultaneous
self.play(animation, run_time=2)  # Custom duration
self.play(a1, a2, lag_ratio=0.3)  # Staggered start
```

### Waiting
```python
self.wait()  # Default 1 second
self.wait(2)  # Wait 2 seconds
```

### Adding Without Animation
```python
self.add(obj)  # Add instantly
self.remove(obj)  # Remove instantly
```

## Advanced Animations

### Animation Composition
```python
# LaggedStart - Stagger multiple animations
from manim import LaggedStart
items = [Circle() for _ in range(5)]
self.play(LaggedStart(*[Create(c) for c in items], lag_ratio=0.2))

# Succession - Play animations one after another
from manim import Succession
self.play(Succession(
    FadeIn(circle),
    circle.animate.shift(RIGHT),
    FadeOut(circle),
))

# AnimationGroup - Run animations together with control
from manim import AnimationGroup
self.play(AnimationGroup(
    Create(circle),
    Write(label),
    lag_ratio=0.5
))
```

### Updaters (Dynamic Animations)
```python
# Value tracker for animation control
t = ValueTracker(0)

# Always redraw based on tracker
dot = always_redraw(lambda: Dot().move_to(RIGHT * t.get_value()))
self.add(dot)
self.play(t.animate.set_value(3), run_time=2)

# Custom updater function
def update_func(mob, dt):
    mob.rotate(dt * PI)  # Rotate based on time
    
circle.add_updater(update_func)
self.wait(2)
circle.remove_updater(update_func)
```

### Path Animations
```python
# Move along a path
path = Circle(radius=2)
dot = Dot()
self.play(MoveAlongPath(dot, path), run_time=3)

# Traced path (draw trail)
from manim import TracedPath
trace = TracedPath(dot.get_center, stroke_color=YELLOW)
self.add(trace)
self.play(dot.animate.shift(RIGHT * 3), run_time=2)
```

### Transform Animations
```python
# TransformMatchingShapes - Smart morphing
self.play(TransformMatchingShapes(old_text, new_text))

# TransformMatchingTex - Math-aware transform
eq1 = MathTex(r"a + b")
eq2 = MathTex(r"b + a")
self.play(TransformMatchingTex(eq1, eq2))

# Morph between different shapes
self.play(Transform(circle, square))
self.play(ReplacementTransform(square, triangle))
```

### Rate Functions (Easing)
```python
# Different timing curves
self.play(animation, rate_func=linear)  # Constant speed
self.play(animation, rate_func=smooth)  # Default, ease in/out
self.play(animation, rate_func=rush_into)  # Fast start, slow end
self.play(animation, rate_func=rush_from)  # Slow start, fast end
self.play(animation, rate_func=there_and_back)  # Return to start
```

## Common Patterns

### Title at Top
```python
title = Text("My Title", font_size=40)
self.play(Write(title))
self.play(title.animate.to_edge(UP))
```

### Sequential Element Creation
```python
items = VGroup(*[Circle() for _ in range(3)])
items.arrange(RIGHT, buff=0.5)
for item in items:
    self.play(Create(item), run_time=0.3)
```

### Highlighting Parts of Equation (CRITICAL - Safe Splitting)
When splitting MathTex into parts for highlighting, EACH PART must be valid LaTeX on its own!

```python
# CORRECT - each part is complete LaTeX
eq = MathTex("a", "+", "b", "=", "c")
self.play(Write(eq))
self.play(eq[0].animate.set_color(RED))  # Highlight 'a'

# CORRECT - complete fractions
eq = MathTex(r"\frac{a}{b}", "+", r"\frac{c}{d}")

# WRONG - DO NOT split inside \frac{}, \sqrt{}, \left(, etc.
# eq = MathTex(r"\frac{", "a", "}{b}")  # WILL FAIL!
# eq = MathTex(r"\text{softmax}\left(\frac{", "x", "}")  # WILL FAIL!
```

For complex formulas, write as ONE string and use set_color_by_tex:
```python
eq = MathTex(r"\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V")
eq.set_color_by_tex("Q", BLUE)
eq.set_color_by_tex("K", ORANGE)
eq.set_color_by_tex("V", GREEN)
```

### Building Block Diagrams
```python
def create_block(text, color):
    rect = RoundedRectangle(width=3, height=0.8, color=color, fill_opacity=0.3)
    label = Text(text, font_size=20)
    label.move_to(rect)
    return VGroup(rect, label)
```

### Connecting Elements with Arrows
```python
box1 = Square().shift(LEFT * 2)
box2 = Square().shift(RIGHT * 2)
arrow = Arrow(box1.get_right(), box2.get_left(), buff=0.1)
self.play(Create(box1), Create(box2))
self.play(Create(arrow))
```

## Quality Guidelines

1. **Keep it short**: 15-45 seconds total
2. **One concept per video**: Focus on a single idea
3. **Use color meaningfully**: Consistent colors for related concepts
4. **Pace appropriately**: Use `self.wait()` to let viewers absorb
5. **Build incrementally**: Show pieces, then combine
6. **Always include**: Title, clear labels, visual hierarchy

## 3D Visualizations (ThreeDScene)

For 3D content (neural networks, data cubes, 3D transformations), use ThreeDScene:

### Basic 3D Structure
```python
from manim import *

class My3DScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
        # 3D content here
```

### 3D Objects
- `Sphere(radius=0.3, color=BLUE)` - 3D sphere
- `Cube(side_length=1.5, fill_color=BLUE, fill_opacity=0.7)` - 3D cube
- `Cylinder(radius=0.5, height=2, color=GREEN)` - Cylinder
- `Cone(base_radius=0.5, height=1, color=RED)` - Cone
- `Arrow3D(start, end, color=WHITE)` - 3D arrow
- `Line3D(start, end, color=GRAY, thickness=0.01)` - 3D line
- `ThreeDAxes(x_range=[-3,3], y_range=[-3,3], z_range=[-3,3])` - 3D coordinate system

### Camera Control
```python
# Set camera angle (phi=vertical angle, theta=horizontal rotation)
self.set_camera_orientation(phi=60 * DEGREES, theta=-60 * DEGREES)

# Animate camera rotation
self.begin_ambient_camera_rotation(rate=0.3)
self.wait(3)
self.stop_ambient_camera_rotation()

# Move camera
self.move_camera(phi=70 * DEGREES, theta=30 * DEGREES, run_time=2)
```

### 2D Text in 3D Scenes
```python
# Add 2D text that stays fixed (doesn't rotate with camera)
title = Text("3D Visualization", font_size=36)
title.to_corner(UL)
self.add_fixed_in_frame_mobjects(title)
self.play(Write(title))
```

## LaTeX Usage (BasicTeX Compatible)

**IMPORTANT**: Use only BasicTeX-compatible LaTeX. Avoid packages not in the minimal distribution.

### Safe LaTeX Patterns
```python
# Basic math - ALWAYS works
MathTex(r"x^2 + y^2 = z^2")
MathTex(r"\frac{a}{b}")
MathTex(r"\int_0^1 f(x) dx")
MathTex(r"\sum_{i=1}^n x_i")
MathTex(r"\sqrt{x}")

# Greek letters - ALWAYS works
MathTex(r"\alpha, \beta, \gamma, \theta, \pi, \sigma")

# Matrices - ALWAYS works
MathTex(r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}")
MathTex(r"\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix}")

# Multiple equations aligned - ALWAYS works
MathTex(r"a &= b + c \\ d &= e + f")
```

### Avoid These (Not in BasicTeX)
- Fancy fonts: `\mathcal`, `\mathbb` may fail - use plain letters instead
- Custom packages: Don't use `\usepackage{}` commands
- Tikz/PGF: Not available - use Manim shapes instead
- Complex symbols: Test unusual symbols before using

### Fallback to Plain Text
```python
# If LaTeX is problematic, use Text() instead
Text("Attention = softmax(QK^T / sqrt(d_k)) V", font_size=24)

# Or simpler MathTex
MathTex(r"E = mc^2")  # Simple is better
```

## Common Pitfalls to Avoid

1. **Don't reuse animation targets**: After `FadeIn(obj)`, can't `FadeIn(obj)` again
2. **Always wait after important content**: `self.wait(1)` after key reveals
3. **Don't overcrowd**: Keep screen clean, remove old elements
4. **Check positioning**: Test that elements don't overlap
5. **Use descriptive class names**: `class AttentionVisualization(Scene)` not `class Test(Scene)`
6. **3D text overlay**: Use `self.add_fixed_in_frame_mobjects(text)` for 2D text in 3D scenes
7. **Keep LaTeX simple**: Stick to basic math, avoid fancy packages (BasicTeX compatible)
8. **NEVER split MathTex inside braces**: Each MathTex part must be valid LaTeX alone. Don't split inside `\frac{}`, `\sqrt{}`, `\left(`, `\begin{}`. Use single string + `set_color_by_tex()` for complex formulas.

## AI/ML Visualization Patterns

### Neural Network Layer Visualization
```python
def create_neural_layer(n_neurons, color=BLUE, label=None):
    """Create a vertical stack of neurons."""
    neurons = VGroup(*[
        Circle(radius=0.15, color=color, fill_opacity=0.3, stroke_width=2)
        for _ in range(n_neurons)
    ])
    neurons.arrange(DOWN, buff=0.25)
    if label:
        lbl = Text(label, font_size=18).next_to(neurons, UP, buff=0.3)
        return VGroup(neurons, lbl)
    return neurons

# Usage: Create a simple network
layer1 = create_neural_layer(4, BLUE, "Input")
layer2 = create_neural_layer(6, ORANGE, "Hidden")
layer3 = create_neural_layer(2, GREEN, "Output")
network = VGroup(layer1, layer2, layer3).arrange(RIGHT, buff=1.5)
```

### Transformer/Attention Block
```python
def create_attention_block(label="Attention", color=BLUE):
    """Create a rounded rectangle block for architecture diagrams."""
    rect = RoundedRectangle(
        width=2.0, height=0.7, corner_radius=0.15,
        color=color, fill_opacity=0.2, stroke_width=2
    )
    text = Text(label, font_size=20).move_to(rect)
    return VGroup(rect, text)

# Build transformer encoder
multi_head = create_attention_block("Multi-Head\\nAttention", BLUE)
add_norm1 = create_attention_block("Add & Norm", GRAY)
ffn = create_attention_block("Feed Forward", GREEN)
add_norm2 = create_attention_block("Add & Norm", GRAY)

encoder = VGroup(multi_head, add_norm1, ffn, add_norm2)
encoder.arrange(DOWN, buff=0.3)
```

### Attention Score Heatmap
```python
def create_attention_heatmap(rows, cols, title=None):
    """Create an attention score grid (heatmap style)."""
    import random
    cells = VGroup()
    for i in range(rows):
        for j in range(cols):
            # Random opacity to simulate attention weights
            opacity = random.random()
            cell = Square(
                side_length=0.5, 
                fill_opacity=opacity * 0.8 + 0.1,
                fill_color=BLUE, 
                stroke_width=1
            )
            cell.move_to(RIGHT * j * 0.5 + DOWN * i * 0.5)
            cells.add(cell)
    cells.center()
    if title:
        lbl = Text(title, font_size=18).next_to(cells, UP, buff=0.3)
        return VGroup(cells, lbl)
    return cells

# Usage
attention_weights = create_attention_heatmap(4, 4, "Attention Scores")
```

### Embedding/Feature Vector
```python
def create_embedding(size=8, color=BLUE, label=None):
    """Create a horizontal embedding vector visualization."""
    cells = VGroup(*[
        Square(side_length=0.3, color=color, fill_opacity=0.3 + 0.1 * i, stroke_width=1)
        for i in range(size)
    ])
    cells.arrange(RIGHT, buff=0.02)
    if label:
        lbl = Text(label, font_size=16).next_to(cells, LEFT, buff=0.3)
        return VGroup(lbl, cells)
    return cells

# Create token embeddings
token1 = create_embedding(8, BLUE, "word₁")
token2 = create_embedding(8, BLUE, "word₂")
token3 = create_embedding(8, BLUE, "word₃")
embeddings = VGroup(token1, token2, token3).arrange(DOWN, buff=0.2)
```

### ML Color Coding Convention
Use these colors consistently throughout visualizations:
- **BLUE** - Query vectors, input embeddings, encoder
- **ORANGE/YELLOW** - Key vectors, intermediate states, attention weights
- **GREEN** - Value vectors, output, decoder
- **RED** - Loss, errors, gradients, attention highlights
- **PURPLE** - Weights, parameters, learned values
- **GRAY** - Normalization layers, add & norm, auxiliary components
- **WHITE** - Text labels, titles

### Common ML Equations (Safe LaTeX)
```python
# Softmax
MathTex(r"\text{softmax}(x_i) = \frac{e^{x_i}}{\sum_j e^{x_j}}")

# Attention
MathTex(r"\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V")

# Cross-entropy loss
MathTex(r"L = -\sum_i y_i \log(\hat{y}_i)")

# Layer normalization
MathTex(r"\text{LayerNorm}(x) = \frac{x - \mu}{\sigma} \cdot \gamma + \beta")

# ReLU activation
MathTex(r"\text{ReLU}(x) = \max(0, x)")
```
