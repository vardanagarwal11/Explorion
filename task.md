# Explorion / arXivisual — AI Video Generation Pipeline Architecture

## Purpose

This document defines the **new architecture and implementation plan** for the Explorion / arXivisual backend pipeline.

The system converts **technical inputs (research papers, GitHub repositories, PDFs, or technical documentation)** into **AI-generated visual explanation videos** using **Manim and Remotion**.

The goal is to produce **structured, coherent, non-overlapping visual explanation videos** with a **streaming UI experience**.

---

# High-Level Pipeline

```
INPUT SOURCE
(arxiv / github / pdf / research docs)
        ↓
CONTENT PARSER
(clean + normalize text)
        ↓
SUMMARIZER
(Groq)
        ↓
SECTION STRUCTURE
(4–8 sections)
        ↓
VIDEO IDEA GENERATOR
(gpt-oss-120b)
        ↓
VIDEO PLAN JSON
(per section)
        ↓
RENDERER SELECTOR
(Manim vs Remotion)
        ↓
CODE GENERATOR
(Kimi K2 Instruct)
        ↓
RENDERING PIPELINE
(Manim or Remotion)
        ↓
VIDEO SEGMENTS
        ↓
UI STREAMING + FINAL VIDEO CONCAT
```

---

# Supported Inputs

The system must support the following input types:

### Research Papers

* arXiv links
* DOI links
* direct PDF upload
* Google Scholar PDFs

### GitHub Repositories

* GitHub repo URL
* README
* source code analysis

### Technical Articles

* blog posts
* documentation pages
* tutorials

---

# Stage 1 — Content Parser

## Purpose

Convert input sources into **clean structured text** for downstream LLM processing.

## Responsibilities

* extract text
* remove formatting noise
* normalize structure
* detect sections

## Output

```
parsed_content.json
```

Example:

```json
{
 "title": "Attention is All You Need",
 "authors": ["Ashish Vaswani"],
 "sections": [
   {
     "title": "Introduction",
     "content": "..."
   },
   {
     "title": "Model Architecture",
     "content": "..."
   }
 ]
}
```

## Implementation Suggestions

Python modules:

```
parser/
    arxiv_parser.py
    pdf_parser.py
    github_parser.py
```

Recommended libraries:

* `PyMuPDF`
* `BeautifulSoup`
* `markdown`
* `pydantic`

---

# Stage 2 — Section Summarizer

## Model

Use:

```
Groq
```

## Goal

Convert parsed content into **4–8 core sections** representing the video structure.

## Prompt Objective

The model must:

* identify core ideas
* merge small sections
* remove redundant details
* produce **logical teaching flow**

## Output

```
sections.json
```

Example:

```json
{
 "sections":[
  {
   "id":1,
   "title":"Introduction",
   "summary":"Overview of the problem and motivation"
  },
  {
   "id":2,
   "title":"Transformer Architecture",
   "summary":"High level explanation of encoder-decoder architecture"
  },
  {
   "id":3,
   "title":"Attention Mechanism",
   "summary":"Explanation of Q, K, V and attention scoring"
  },
  {
   "id":4,
   "title":"Training Process",
   "summary":"Loss functions and optimization"
  }
 ]
}
```

---

# Stage 3 — Video Idea Generator

## Model

```
gpt-oss-120b
```

## Inputs

```
parsed_content
+
sections
```

## Purpose

Generate a **visual explanation plan** for each section.

Each section becomes **one video segment**.

The model should generate:

* scene descriptions
* animation ideas
* visual metaphors
* suggested renderer

## Output

```
video_plan_section_X.json
```

Example:

```json
{
 "section_title":"Attention Mechanism",
 "renderer":"manim",
 "duration":40,
 "scenes":[
  {
   "scene_type":"concept_intro",
   "visual":"query key value vectors",
   "animation":"vectors interacting"
  },
  {
   "scene_type":"math_formula",
   "formula":"softmax(QK^T / sqrt(d_k))V",
   "animation":"matrix multiplication"
  },
  {
   "scene_type":"visual_explanation",
   "description":"attention weights highlighting tokens"
  }
 ]
}
```

---

# Stage 4 — Renderer Selection

Each section must choose a renderer.

## Manim

Use when content includes:

* equations
* mathematical derivations
* algorithms
* graphs
* vector visualizations

## Remotion

Use when content includes:

* system architecture diagrams
* UI flows
* code walkthrough
* conceptual explanations
* token flow / pipelines

## Renderer Decision Rule

```
if contains math:
    renderer = "manim"
else:
    renderer = "remotion"
```

The LLM suggestion can be overridden by this rule.

---

# Stage 5 — Code Generation

## Model

```
Kimi K2 Instruct
```

## Input

```
video_plan_section.json
```

## Output

Depending on renderer:

### Manim

```
manim_scene_section_1.py
```

### Remotion

```
remotion_scene_section_1.tsx
```

## Requirements

Generated code must:

* be deterministic
* avoid overlapping animations
* follow scene ordering
* respect duration limits

---

# Stage 6 — Rendering

## Manim Rendering

Command example:

```
manim -pqh scene.py SceneName
```

Output:

```
scene_1.mp4
```

---

## Remotion Rendering

Remotion should render React components into video.

Example command:

```
npx remotion render src/index.tsx Video out/scene_2.mp4
```

---

# Stage 7 — Video Segments

Each section becomes one video segment.

Example:

```
scene_1.mp4
scene_2.mp4
scene_3.mp4
scene_4.mp4
```

---

# Stage 8 — Streaming UI

The UI should display progress as segments render.

Example UI state:

```
Video Structure

✓ Introduction
Rendering Architecture
Queued Attention
Queued Training
```

Once a segment finishes rendering:

```
scene_1.mp4 → playable
```

Users can begin watching immediately.

---

# Stage 9 — Final Video Concatenation

After all segments render:

```
ffmpeg concat
```

Example command:

```
ffmpeg -f concat -safe 0 -i list.txt -c copy final_video.mp4
```

---

# Backend Architecture

Suggested backend stack:

```
FastAPI
Redis Queue
Celery Workers
Docker
```

## Worker Types

### Scene Planning Worker

Handles:

```
video idea generation
```

### Code Generation Worker

Handles:

```
Kimi K2 Instruct code generation
```

### Rendering Worker

Handles:

```
Manim / Remotion rendering
```

Rendering workers should be **separate processes**.

---

# File Structure

Suggested backend layout:

```
backend/
│
├── parser/
│   ├── arxiv_parser.py
│   ├── pdf_parser.py
│   └── github_parser.py
│
├── summarizer/
│   └── section_summarizer.py
│
├── video_planner/
│   └── video_idea_generator.py
│
├── renderer_selector/
│   └── renderer_router.py
│
├── code_generation/
│   └── kimi_codegen.py
│
├── renderers/
│   ├── manim_renderer.py
│   └── remotion_renderer.py
│
├── pipeline/
│   └── pipeline_controller.py
│
└── utils/
```

---

# Pipeline Controller Logic

Pseudo code:

```
input → parse

parse → summarizer

summarizer → sections

for each section:
    generate video_plan

for each video_plan:
    choose renderer
    generate code
    render scene

collect scenes

concat video
```

---

# Key Design Rules

### 1. Maximum Sections

```
min = 4
max = 8
```

---

### 2. Per-Section Rendering

Never generate the entire video at once.

Always:

```
section → segment
```

---

### 3. Structured JSON Contracts

Every stage communicates via **JSON contracts**.

Example flow:

```
parsed_content.json
sections.json
video_plan_section.json
```

---

### 4. Deterministic Rendering

Animations must avoid:

* overlapping objects
* undefined positions
* infinite loops

---

# Future Improvements

Potential upgrades:

### Scene Templates

Predefined animation templates:

```
formula_explanation
algorithm_flow
architecture_diagram
token_flow
timeline_visualization
```

---

### Style Generator

Create consistent visual style across segments.

Example:

```
video_style.json
```

Example:

```
color_theme: dark
font: inter
transition: fade
```

---

### Parallel Rendering

Segments can render in parallel using workers.

---

# Summary

The new architecture improves:

* pipeline modularity
* rendering stability
* UI responsiveness
* animation quality
* scalability

The pipeline converts **technical content into visual explanations** through the following steps:

```
Input → Parse → Summarize → Video Plan → Code Generation → Rendering → Streaming UI → Final Video
```

This architecture ensures **consistent, non-overlapping, and structured educational video generation**.

---
