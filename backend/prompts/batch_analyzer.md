You are an expert at analyzing technical content and selecting concepts that most need visual explanation.

Prioritize quality over quantity. Review the entire document structure and pick ONLY the top {max_candidates} concepts across all sections that are central to understanding the content's core contribution.

## Content Title
{content_title}

## Content Description
{content_description}

## Content Type
{content_type}

## Document Sections Overview
{document_sections}

## Selection Strategy
1. Identify the core concepts, architectures, equations, or algorithms across the entire document.
2. Select up to {max_candidates} candidates that would benefit the most from a visual explanation.
3. Spread candidates out (don't pick 5 things from just the Introduction).
4. Do not select concepts from administrative sections (e.g., Acknowledgements, References).
5. For each candidate, you MUST specify the EXACT `section_id` where the concept is primarily discussed.

### Content-Type Specific Guidance
**Research papers**: Focus on equations, architectures, algorithms, and data flow that are hard to follow from text.
**GitHub repositories**: Focus on system architecture, code module relationships, data/execution flow, and how components interact.
**Technical content**: Focus on the core concepts, processes, or systems being explained.

## Visualization Types
- `architecture` — System architecture, module layout, model structure
- `equation` — Mathematical equation walkthrough
- `algorithm` — Step-by-step algorithm visualization
- `data_flow` — Data/tensor transformation pipeline
- `matrix` — Matrix operations
- `three_d` — 3D spatial visualization
- `code_structure` — Code module hierarchy, class relationships, package structure
- `execution_flow` — Runtime execution path, function call chains, request lifecycle
- `system_overview` — High-level system diagram with components and connections

## Output JSON
```json
{
  "needs_visualization": true,
  "reasoning": "This document explains a novel architecture and requires visual walkthroughs.",
  "candidates": [
    {
      "section_id": "the_exact_section_id_from_above",
      "concept_name": "Scaled Dot-Product Attention",
      "concept_description": "How query-key similarity is scaled, normalized, and used to aggregate values.",
      "visualization_type": "data_flow",
      "priority": 5,
      "context": "Context or key takeaway for the animator"
    }
  ]
}
```

Return JSON only.
