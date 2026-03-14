# Explorion Migration Guide

## Converting the Backend from Local Models (Ollama) → NVIDIA NIM + Groq APIs

---

# 1. Purpose

This document explains how to **convert Explorion from a fully local LLM pipeline to a hybrid cloud pipeline using NVIDIA NIM and Groq APIs**.

The objective is to:

* remove slow local inference
* use large cloud models for better code generation
* maintain the existing **LangGraph pipeline**
* keep the architecture modular

After migration, the system will run:

```
Extraction (local)
↓
Groq API (summarization + scene planning)
↓
NVIDIA NIM API (code generation)
↓
Local rendering (Manim / Remotion)
↓
Video scenes
```

This hybrid approach ensures:

* fast inference
* strong coding capability
* minimal API usage
* stable animation generation

---

# 2. New Architecture

## Previous Architecture (Local)

```
Input
↓
Extraction
↓
Ollama (phi3)
↓
Scene planning
↓
Ollama (qwen coder)
↓
Manim / Remotion
↓
Video output
```

Problems:

* slow inference
* weaker code generation
* limited by local GPU

---

## New Architecture (Cloud Hybrid)

```
Input
↓
Extraction (Python)
↓
Groq API
(summary + scene planning)
↓
NVIDIA NIM API
(animation code generation)
↓
Local Rendering
Manim / Remotion
↓
Video scenes
```

Benefits:

* large models
* fast responses
* improved code accuracy

---

# 3. Models Used

## Summarization + Planning

Model:

```
phi-3.5-mini-instruct
```

Provider:

```
Groq API
```

Purpose:

* summarize papers
* extract concepts
* plan animation scenes
* classify visualization engine

Advantages:

* extremely fast
* structured output
* low token usage

---

## Code Generation

Model:

```
llama-3.3-70b-instruct
```

Provider:

```
NVIDIA NIM API
```

Purpose:

* generate Manim animation code
* generate Remotion React components

Advantages:

* strong reasoning
* high-quality Python code
* fewer syntax errors

---

# 4. Backend Structure

The backend folder should be organized as follows:

```
backend/

agents/
    summarizer.py
    planner.py
    coder.py

providers/
    groq_client.py
    nim_client.py

extractors/
    arxiv_extractor.py

renderers/
    manim_renderer.py
    remotion_renderer.py

pipeline/
    graph.py
    state.py

utils/
    config.py
```

---

# 5. Environment Variables

Create `.env` file.

```
GROQ_API_KEY=your_groq_key
NIM_API_KEY=your_nim_key
```

Optional configuration:

```
SUMMARY_MODEL=phi-3.5-mini-instruct
CODE_MODEL=meta/llama-3.3-70b-instruct
```

---

# 6. Groq API Integration

Create:

```
backend/providers/groq_client.py
```

Example implementation:

```python
import requests
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def groq_chat(prompt):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "phi-3.5-mini-instruct",
        "messages": [
            {"role":"user","content":prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()["choices"][0]["message"]["content"]
```

---

# 7. NVIDIA NIM API Integration

Create:

```
backend/providers/nim_client.py
```

Example:

```python
import requests
import os

NIM_API_KEY = os.getenv("NIM_API_KEY")

def nim_generate(prompt):

    url = "https://integrate.api.nvidia.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages":[
            {"role":"user","content":prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    return response.json()["choices"][0]["message"]["content"]
```

---

# 8. Summarization Agent

File:

```
agents/summarizer.py
```

```python
from providers.groq_client import groq_chat

def summarize(text):

    prompt = f"""
Summarize the following research content.

Return JSON:

{{
"title":"",
"concepts":[
{{
"name":"",
"explanation":"",
"visualization_opportunity":""
}}
]
}}

{text}
"""

    return groq_chat(prompt)
```

---

# 9. Scene Planner

File:

```
agents/planner.py
```

Example prompt:

```python
from providers.groq_client import groq_chat

def plan_scenes(summary):

    prompt = f"""
Convert this summary into animation scenes.

Return JSON:

{{
"scenes":[
{{
"title":"",
"engine":"manim or remotion",
"description":""
}}
]
}}

{summary}
"""

    return groq_chat(prompt)
```

---

# 10. Code Generation Agent

File:

```
agents/coder.py
```

```python
from providers.nim_client import nim_generate

def generate_animation(scene):

    engine = scene["engine"]
    description = scene["description"]

    prompt = f"""
You are an expert animation developer.

Framework: {engine}

Scene description:
{description}

Rules:

If Manim:
- write Python code
- create a Scene class
- ensure code renders

If Remotion:
- write React component
- export a video composition

Return ONLY code.
"""

    return nim_generate(prompt)
```

---

# 11. Rendering

## Manim

```
renderers/manim_renderer.py
```

```python
import subprocess

def render_manim(file):

    subprocess.run([
        "manim",
        "-ql",
        file,
        "Scene"
    ])
```

---

## Remotion

```
renderers/remotion_renderer.py
```

```python
import subprocess

def render_remotion():

    subprocess.run([
        "npx",
        "remotion",
        "render"
    ])
```

---

# 12. LangGraph Pipeline

Install:

```
pip install langgraph
```

Example graph:

```
extract
↓
summarize
↓
plan_scenes
↓
generate_code
↓
render
```

Graph logic:

```python
START
↓
extract_content
↓
summarize
↓
plan_scenes
↓
scene_loop
   ↓
 generate_code
   ↓
 render
↓
END
```

---

# 13. Scene Loop

Each scene is processed individually.

Example logic:

```
for scene in scenes:

    code = generate_animation(scene)

    save code file

    render animation

    store video path
```

Output example:

```
scene1.mp4
scene2.mp4
scene3.mp4
```

---

# 14. Rate Limit Management

NIM limit:

```
40 requests per minute
```

Typical request usage per paper:

```
1 summarization
1 planning
3 code generations
```

Total:

```
~5 requests per paper
```

Safe throughput:

```
8 papers per minute
```

---

# 15. Error Handling

Add retry mechanism.

Example:

```
try render
if error:
    regenerate code
    retry
```

Maximum retries:

```
3
```

---

# 16. Frontend Integration

Backend should return:

```
{
 "title":"Paper Title",
 "scenes":[
  "video1.mp4",
  "video2.mp4",
  "video3.mp4"
 ]
}
```

Frontend will display videos in scrollytelling sections.

---

# 17. Expected Performance

Approximate pipeline runtime:

| Step            | Time      |
| --------------- | --------- |
| Extraction      | 1–2 sec   |
| Summarization   | 1–2 sec   |
| Scene planning  | 2 sec     |
| Code generation | 5–10 sec  |
| Rendering       | 20–60 sec |

Total:

```
~30–70 seconds per paper
```

Rendering becomes the main bottleneck.

---

# 18. Final Stack

Frontend

```
Next.js
Tailwind
shadcn/ui
```

Backend

```
FastAPI
LangGraph
Python
```

Models

```
Groq → phi-3.5-mini
NVIDIA NIM → llama-3.3-70b
```

Rendering

```
Manim
Remotion
```

---

# 19. Goal

This migration converts Explorion into a **fast hybrid AI visual explanation engine** capable of:

* analyzing research papers
* generating animation code
* rendering educational visualizations

using powerful cloud models while keeping rendering fully local.

---
