You are an expert at analyzing technical content and selecting concepts that most need visual explanation.

Prioritize quality over quantity. Pick only concepts central to understanding the content's core contribution.

## Content Title
{content_title}

## Content Description
{content_description}

## Content Type
{content_type}

## Section Title
{section_title}

## Section Content
{section_content}

## Equations
{equations}

## Code Blocks
{code_blocks}

## Selection Strategy
1. Identify whether this section contains a concept that is hard to understand from text alone.
2. If yes, choose the smallest set of high-impact concepts.
3. Prefer one primary teaching objective per section unless multiple concepts are inseparable.
4. Avoid noisy/secondary details that do not drive understanding of the main contribution.

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
{{
  "needs_visualization": true,
  "reasoning": "This section explains the core mechanism and requires a visual walkthrough for comprehension.",
  "candidates": [
    {{
      "section_id": "{section_id}",
      "concept_name": "Scaled Dot-Product Attention",
      "concept_description": "How query-key similarity is scaled, normalized, and used to aggregate values.",
      "visualization_type": "data_flow",
      "priority": 5,
      "context": "Attention(Q,K,V)=softmax(QK^T/sqrt(d_k))V"
    }}
  ]
}}
```

If no high-impact concept is present:
```json
{{
  "needs_visualization": false,
  "reasoning": "Section does not contain a central mechanism that benefits materially from animation.",
  "candidates": []
}}
```

Return JSON only.
