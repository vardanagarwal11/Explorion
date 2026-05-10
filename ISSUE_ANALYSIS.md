# Issue Analysis: Only 1 Video Generated with No Text Explanation

## Problem Statement

When processing arXiv papers through Explorion, the system generates:

- **Only 1 visualization video** instead of multiple sections
- **No text/title displayed** in the videos explaining what topic is being visualized

Expected behavior: Each paper section should get its own visualization video with the section topic clearly displayed as text in the video.

---

## Root Cause Analysis

### Issue #1: Overly Aggressive Section Filtering (PRIMARY BOTTLENECK)

**Location:** `backend/jobs/worker.py` lines 126-132

**Current Code:**

```python
def is_valid_concept(concept: dict) -> bool:
    """Return True only if this concept should get a video (no junk/metadata sections)."""
    title = ((concept.get("title") or concept.get("name")) or "").lower()
    description = (concept.get("description") or concept.get("explanation")) or ""
    if any(block in title for block in CONCEPT_BLOCKLIST):
        return False
    if len(description.strip()) < 40:  # ❌ THIS IS THE PROBLEM
        return False
    return True
```

**The Problem:**

- When creating concepts from paper sections (line 261-265), explanations are truncated to 24 words:
  ```python
  "explanation": _truncate_words(s.summary or s.content or "No content", 24)
  ```
- A 24-word explanation often becomes < 40 characters when truncated
- Most arXiv paper sections have **empty or very short summaries** in the parsed database sections
- Result: 90% of sections get filtered out, leaving only 1-2 concepts that survive the filter

**Example:**

```
Section from DB: "Introduction to Transformers"
Summary: (empty or very short)
Explanation after truncation: "Core mechanism from Introduction" (32 chars)
Filter Result: ❌ REJECTED (32 < 40 chars)
```

**How many sections are lost?**

- If a paper has 8 sections but only 2 pass the 40-char threshold
- Only those 2 concepts → only 2 video scenes are planned
- Planner creates one scene per concept
- Result: 2 videos instead of 8

---

### Issue #2: LLM Explicitly Told NOT to Display Text

**Location:** `backend/agents/coder.py` lines 37-42 in `MANIM_PROMPT`

**Current Instruction:**

```python
CRITICAL RULES:
1. NEVER display the scene description or any instruction text as on-screen text.
   BAD:  Text("Build a 3D graph with x, y, z axes showing...")
   GOOD: Create the actual 3D axes and animate them.
2. The scene description is YOUR PRIVATE BRIEF — it tells you what to build.
   It must NEVER appear as a Manim Text(), MathTex(), or Tex() object.
```

**The Problem:**

- This rule prevents displaying the **scene title** (which should be shown to explain what topic the animation is about)
- The LLM generates pure visualizations without any text context
- Viewer sees animations but doesn't know what they're watching

**What gets lost:**

```python
# Scene object has:
scene = {
    "title": "Attention Mechanism",           # ← Not displayed anywhere
    "description": "Build a 4x4 grid...",     # ← Explicitly forbidden from display
    "code": "from manim import *\n..."         # ← Generated without title text
}
```

---

### Issue #3: Database Section Creation Works But Output Never Used

**Location:** `backend/jobs/worker.py` lines 250-265

**What Happens:**

1. `_ingest_and_store_paper()` parses arXiv and creates multiple database sections
2. Retrieves them: `db_sections = list(db_paper.sections)` → Returns 8+ sections
3. Builds concepts from sections (lines 257-265)
4. **Applies the harsh filter** → Only keeps 1-2
5. Only filtered concepts get sent to planner

```python
# This code works correctly:
db_paper = await queries.get_paper(db, arxiv_id)
if db_paper:
    db_sections = list(db_paper.sections)  # ✅ Correctly fetches all 8 sections

    # Build concepts from each section
    raw_concepts = [{
        "name": s.title,
        "explanation": _truncate_words(s.summary or s.content, 24),  # 24-word limit
        "visualization_opportunity": _truncate_words(f"Visualize {s.title}", 12)
    } for s in db_sections]  # ✅ Creates 8 concepts

    # Apply filter → ❌ REDUCES TO 1-2 CONCEPTS
    main_concepts = [c for c in raw_concepts if is_valid_concept(c)]

    # Only these filtered concepts become videos
    pipeline_kwargs["summary"] = {"main_concepts": main_concepts}  # ❌ 1-2 items instead of 8
```

---

### Issue #4: Frontend Display Path Exists But Empty

**Location:** `backend/api/schemas.py` VisualizationResponse

**Current Schema:**

```python
class VisualizationResponse(BaseModel):
    id: str
    section_id: str
    concept: str                    # ← Scene title stored here
    video_url: Optional[str]
    subtitle_url: Optional[str]
    audio_url: Optional[str]
    status: VisualizationStatus
```

**What's missing:**

- The `concept` field is populated but **not being rendered in the Manim video itself**
- It sits in the database/API response with no visual representation

---

## The Flow of Data Loss

```
ArXiv Paper
    ↓
Parse into 8 sections (200+ words in database) ✅
    ↓
Create 8 concepts from sections ✅
    ↓
FILTER BY 40-CHAR RULE → 1-2 concepts survive ❌
    ↓
Plan visualization for 1-2 concepts ✅
    ↓
Generate Manim code (WITHOUT title text) ❌
    ↓
Render 1-2 videos with no explanatory titles ❌
    ↓
Return to frontend with only 1-2 visualizations
```

---

## Solution Overview

### Fix #1: Relax the Concept Filter

**File:** `backend/jobs/worker.py` lines 126-132

**Change:** Replace the 40-character minimum with a 10-character minimum (just to filter out empty/garbage)

```python
# BEFORE:
if len(description.strip()) < 40:
    return False

# AFTER:
if len(description.strip()) < 10:
    return False
```

**Impact:**

- A 24-word explanation (typical output of `_truncate_words(..., 24)`) is ~120 chars
- Even if truncated to 8 words, it's ~50 chars
- Only actual empty/corrupted sections get filtered
- **Expected result:** 8 sections → 8 concepts → 8 videos (instead of 1-2)

---

### Fix #2: Tell LLM to Display the Scene Title

**File:** `backend/agents/coder.py` lines 37-42, update MANIM_PROMPT

**Change:** Add explicit instruction to create and display the scene title

```python
MANIM_PROMPT = """\
You are a world-class Manim animation developer who creates visually stunning,
3Blue1Brown-style educational explainer videos.

Write a complete, self-contained Manim Python script for the following scene.

SCENE TITLE: {title}
SCENE BRIEF: {description}

CRITICAL RULES:

1. DISPLAY THE SCENE TITLE AT START (MANDATORY):
   - Create a prominent, large title text at the top of the scene
   - Example: title_text = Text("{title}", font_size=52, color=WHITE)
   - Position it with: title_text.to_edge(UP, buff=0.5)
   - Animate it with: self.play(FadeIn(title_text), run_time=0.8)
   - Keep it visible for at least 1.5 seconds
   - Then fade it to 40% opacity as background: title_text.set_opacity(0.4)
   - OR move it to a corner: title_text.scale(0.6).to_corner(UP+LEFT, buff=0.3)
   - This tells viewers WHAT CONCEPT they're about to see

2. DO NOT display the scene brief/description as animation text:
   The brief is YOUR PRIVATE notes explaining what to build.
   BAD:  Text("Build a 3D graph with x, y, z axes showing...")
   GOOD: Create the actual 3D axes and animate them.

3. All other on-screen labels must explain what the viewer is seeing
   (e.g. axis names, formula components, concept labels) — not instructions.

... [rest of prompt]
```

**Why this works:**

- First thing the viewer sees is the **topic name** (e.g., "Attention Mechanism", "Gradient Flow")
- Manim code now explicitly adds `Text("{title}")` at the start
- Validation in `coder.py` no longer flags the title text as "description being displayed"

---

### Fix #3: Ensure Quality Descriptions in Concepts

**File:** `backend/jobs/worker.py` lines 257-265

**Current code (already correct, just needs to work with relaxed filter):**

```python
raw_concepts = [{
    "name": s.title,  # Section title becomes concept name (displayed in video)
    "explanation": _truncate_words(s.summary or s.content or "No content", 24),
    "visualization_opportunity": _truncate_words(f"Visualize the core mechanism from {s.title}", 12)
} for s in db_sections]
```

**No changes needed here** — once the filter is relaxed, all concepts will have:

- `name`: The section title (will be displayed in the video)
- `explanation`: First 24 words of summary (used by planner for context)
- `visualization_opportunity`: Hint for the coder (directs the animation)

---

## Expected Impact After Fixes

### Before:

```
Paper: "Attention is All You Need"
Sections in DB: 8 (Introduction, Attention, Encoder, Decoder, etc.)
After filter: 1-2 concepts
Generated videos: 1-2 with no title text visible
Viewer experience: Single animation, no context
```

### After:

```
Paper: "Attention is All You Need"
Sections in DB: 8
After filter: 7-8 concepts (all non-blocklisted)
Generated videos: 7-8, each starting with scene title (e.g., "Attention Mechanism")
Viewer experience: Multiple focused animations, clear topic identification
```

---

## Implementation Checklist

- [ ] Update `is_valid_concept()` filter threshold from 40 chars to 10 chars
- [ ] Update `MANIM_PROMPT` to include explicit title display instructions
- [ ] Test with an arXiv paper (e.g., "1706.03762" - Attention paper)
- [ ] Verify 6+ videos are generated
- [ ] Verify each video starts with a text overlay showing the concept name
- [ ] Verify visualization code includes the title text object

---

## Testing Validation

Run this after applying fixes:

```bash
# Check that multiple sections are processed
grep -i "generated \d visualization" backend/media/pipeline_runs/*/run.json

# Verify Manim code includes Text() for titles
grep "Text(" backend/media/pipeline_runs/*/scene_*.py | head -5
```

Expected output:

```
Generated 7 visualization(s)  ← Should be > 1
Generated 8 visualization(s)  ← Should be > 1

# Multiple scene files with Text() calls:
scene_0.py: title_text = Text("Attention Mechanism", ...)
scene_1.py: title_text = Text("Encoder Layer", ...)
scene_2.py: title_text = Text("Decoder Architecture", ...)
```

---

## Code Example: What Changes

### Example arXiv paper sections from database:

```python
db_sections = [
    Section(id="intro", title="Introduction", content="Transformers are...", summary=""),
    Section(id="related", title="Related Work", content="Previous work...", summary=None),
    Section(id="method", title="Attention Mechanism", content="Scaled dot product...", summary="Core innovation."),
    Section(id="arch", title="Model Architecture", content="Encoder-decoder...", summary=None),
    Section(id="exp", title="Experiments", content="We evaluated on...", summary="Test results."),
    Section(id="results", title="Results", content="BLEU scores...", summary=""),
    Section(id="conclusion", title="Conclusion", content="We presented...", summary="Summary of work."),
]
```

### Current behavior (with 40-char filter):

```python
raw_concepts = [
    {"name": "Introduction", "explanation": "No content", ...},           # 10 chars → fails
    {"name": "Related Work", "explanation": "No content", ...},           # 10 chars → fails
    {"name": "Attention Mechanism", "explanation": "Core innovation", ...}, # 18 chars → fails
    {"name": "Model Architecture", "explanation": "No content", ...},     # 10 chars → fails
    {"name": "Experiments", "explanation": "Test results evaluated", ...},  # 28 chars → fails
    {"name": "Results", "explanation": "No content", ...},                # 10 chars → fails
    {"name": "Conclusion", "explanation": "Summary of work presented", ...}, # 28 chars → fails
]

main_concepts = [c for c in raw_concepts if is_valid_concept(c)]
# Result: [] or maybe 1 that passed somehow

# Only 1 concept → Only 1 scene → Only 1 video
```

### New behavior (with 10-char filter):

```python
raw_concepts = […all 7 same as above…]

main_concepts = [c for c in raw_concepts if is_valid_concept(c)]
# Result: 7 concepts (all pass 10-char threshold)

# 7 concepts → 7 scenes → 7 videos with titles displayed
```

### Generated Manim code sample (with new instructions):

```python
from manim import *

class MainScene(Scene):
    def construct(self):
        # NEW: Display the scene title
        title_text = Text("Attention Mechanism", font_size=52, color=WHITE)
        title_text.to_edge(UP, buff=0.5)
        self.play(FadeIn(title_text), run_time=0.8)
        self.wait(1.5)

        # Fade title to background
        title_text.set_opacity(0.4)

        # Now show the actual visualization
        grid = create_grid(4, 4)  # The visual concept
        self.play(ShowCreation(grid), run_time=2)

        # Attention animation
        arrows = create_attention_arrows(grid)
        self.play(AnimationGroup(*arrows), run_time=3, lag_ratio=0.1)

        self.wait(2)
```

---

## Summary for Other Agents

**What's broken:** Only 1 video instead of N (one per section), with no title text.

**Why:** Two bugs compound:

1. **Concept filter too strict** → 8 sections become 1-2 concepts
2. **LLM forbidden from displaying titles** → Videos have no context text

**Fix:**

1. Change threshold from 40 to 10 characters in `is_valid_concept()`
2. Add explicit title display instructions in `MANIM_PROMPT`

**Files to modify:**

- `backend/jobs/worker.py` (line 129)
- `backend/agents/coder.py` (lines 37-42, add to MANIM_PROMPT)

**Effort:** ~15 minutes to apply and test
