# Model Assignment Strategy

## Overview
The ArXiviz pipeline uses different LLM models for different tasks:

| Task | Model | Provider | Purpose |
|------|-------|----------|---------|
| **Text Analysis & Summarization** | Llama 3.1 70B | NIM | Understand and summarize research papers |
| **Section Organization** | Llama 3.1 70B | NIM | Organize summarized content into logical sections |
| **Section Analysis** | Llama 3.1 70B | NIM | Analyze sections and identify visualization candidates |
| **Voiceover Generation** | Llama 3.1 70B | NIM | Generate narration scripts |
| **Manim Code Generation** | GLM-5.1-FP8 | Modal | Generate visual animation code |

## Implementation Details

### NIM Llama 3.1 (Text Processing)
**Files:** 
- `backend/ingestion/section_formatter.py` - Summarizes and organizes sections
- `backend/agents/section_analyzer.py` - Identifies visualization candidates
- `backend/agents/voiceover_generator.py` - Generates narration scripts

Uses explicit NIM provider via model parameter:
- Summarizes entire paper to 30-40% of original length
- Organizes content into ≤5 logical sections
- Analyzes sections to identify what to visualize
- Generates natural language narration
- Designed for natural language understanding and synthesis

```python
# NIM calls (section_formatter.py)
result = await call_llm_nim(prompt, system_prompt, max_tokens=16000)

# Agents using NIM (section_analyzer.py, voiceover_generator.py)
def __init__(self, model: str | None = None):
    nim_model = "meta/llama-3.1-70b-instruct"
    super().__init__("prompt.md", model=model or nim_model)
```

### GLM-5.1-FP8 (Code Generation)
**File:** `backend/agents/manim_generator.py` - Generates Manim animation code

Uses BaseAgent which resolves to Modal GLM-5.1 (via provider priority in `.env`):
```python
# Provider resolution order (from agents/base.py):
1. MODAL_API_KEY     → Modal GLM-5.1-FP8 (primary for code generation)
2. NIM_API_KEY       → NVIDIA NIM Llama 3.1 (default if MODAL not set)
3. GROQ_API_KEY      → Groq Cloud Llama 3.3
4. GEMINI_API_KEY    → Google Gemini
```

ManimGenerator uses BaseAgent which will default to Modal GLM-5.1 when MODAL_API_KEY is set.

## Why This Split?

**NIM Llama 3.1 for Text & Analysis:**
- Excellent at semantic understanding and summarization
- Good at organizing and restructuring content
- Strong at analyzing concepts and identifying key ideas
- Natural narration generation
- Cost-effective for large text processing

**GLM-5.1-FP8 for Code Generation Only:**
- Optimized specifically for code generation and syntax
- Better at following Manim API documentation
- Produces cleaner, working animation code
- Has access to manim examples for few-shot learning
- Reserved for the most critical code generation task

## Configuration

**.env file:**
```
MODAL_API_KEY=...              # GLM-5.1 (primary for code)
NIM_API_KEY=...                # Llama 3.1 (for text analysis)
```

The order in `.env` determines provider priority. Since MODAL comes first, it's the default for generic LLM calls (via `call_llm()`), while specific NIM calls go directly to NIM provider.

## Pipeline Flow

```
arXiv Paper
    ↓
[NIM Llama 3.1] Fetch & Parse PDF
    ↓
[NIM Llama 3.1] Summarize & Organize Sections
    ↓
[NIM Llama 3.1] Section Analysis (identify what to visualize)
    ↓
[GLM-5.1] Generate Manim Code
    ↓
[NIM Llama 3.1] Generate Voiceover Script
    ↓
Render with Manim + TTS
```

**Summary:**
- **NIM Llama 3.1**: All text understanding, analysis, and narration
- **GLM-5.1**: Only Manim code generation (where code quality matters most)

## Testing

Run `test_simple_pipeline.py` to validate:
```bash
cd backend
.venv\Scripts\python.exe test_simple_pipeline.py
```

Expected: Paper fetches → sections extract → visualizations generate with Manim code
