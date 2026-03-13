"""Section Analyzer Agent - Identifies concepts that need visualization.

Supports all content types: research papers, GitHub repos, technical content.
"""

import sys
from pathlib import Path
from typing import Any, Union

# Handle both package and direct imports
try:
    from .base import BaseAgent
    from ..models.paper import Section
    from ..models.generation import AnalyzerOutput, VisualizationCandidate, VisualizationType
except ImportError:
    # Add parent to path for direct execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base import BaseAgent
    from models.paper import Section
    from models.generation import AnalyzerOutput, VisualizationCandidate, VisualizationType


class SectionAnalyzer(BaseAgent):
    """
    Analyzes content sections to identify concepts that would benefit from visualization.
    
    This agent reads each section and determines:
    1. Whether visualization would help understanding
    2. What specific concepts should be visualized
    3. What type of visualization (architecture, equation, algorithm, data_flow, 
       code_structure, execution_flow, system_overview)
    4. Priority ranking for each concept
    
    Works with any content type — research papers, GitHub repos, or technical content.
    """
    
    def __init__(self, model: str | None = None):
        super().__init__("section_analyzer.md", model=model)
    
    def _format_equations(self, section: Section) -> str:
        """Format equations for the prompt."""
        if not section.equations:
            return "No equations in this section."
        
        equations_text = []
        for eq in section.equations:
            eq_str = f"- LaTeX: {eq.latex}"
            if eq.context:
                eq_str += f"\n  Context: {eq.context}"
            equations_text.append(eq_str)
        
        return "\n".join(equations_text)
    
    def _format_code_blocks(self, section: Section) -> str:
        """Format code blocks for the prompt (relevant for repos and technical content)."""
        # Section from paper.py doesn't have code_blocks, but StructuredContent sections might
        code_blocks = getattr(section, "code_blocks", None)
        if not code_blocks:
            return "No code blocks in this section."
        
        formatted = []
        for i, block in enumerate(code_blocks[:5], 1):  # Limit to 5 to avoid prompt overflow
            snippet = block[:500] if isinstance(block, str) else str(block)[:500]
            formatted.append(f"```\n{snippet}\n```")
        
        return "\n\n".join(formatted)
    
    async def run(
        self,
        content_title: str,
        content_description: str,
        section: Section,
        content_type: str = "research_paper",
        # Backward-compatible aliases
        paper_title: str = "",
        paper_abstract: str = "",
    ) -> AnalyzerOutput:
        """
        Analyze a section to identify visualization candidates.
        
        Args:
            content_title: Title of the content (paper, repo, article)
            content_description: Description/abstract for context
            section: The section to analyze
            content_type: Type of content (research_paper, github_repo, technical_content)
            paper_title: Deprecated alias for content_title (backward compat)
            paper_abstract: Deprecated alias for content_description (backward compat)
            
        Returns:
            AnalyzerOutput with visualization candidates
        """
        # Backward compatibility: use paper_* params if content_* not provided
        title = content_title or paper_title
        description = content_description or paper_abstract
        
        prompt = self._format_prompt(
            content_title=title,
            content_description=description,
            content_type=content_type,
            section_id=section.id,
            section_title=section.title,
            section_content=section.content,
            equations=self._format_equations(section),
            code_blocks=self._format_code_blocks(section),
        )
        
        text = await self._call_llm(prompt)

        result = self._parse_json_response(text)
        return self._parse_result(result, section.id)

    def _parse_result(self, result: dict, section_id: str) -> AnalyzerOutput:
        """Parse the LLM response into an AnalyzerOutput."""
        candidates = []
        
        for candidate_data in result.get("candidates", []):
            # Map string visualization type to enum
            viz_type_str = candidate_data.get("visualization_type", "equation")
            try:
                viz_type = VisualizationType(viz_type_str)
            except ValueError:
                viz_type = VisualizationType.EQUATION
            
            candidate = VisualizationCandidate(
                section_id=section_id,  # Always use the actual section ID, not LLM-generated one
                concept_name=candidate_data.get("concept_name", "Unknown Concept"),
                concept_description=candidate_data.get("concept_description", ""),
                visualization_type=viz_type,
                priority=min(5, max(1, candidate_data.get("priority", 3))),
                context=candidate_data.get("context", ""),
            )
            candidates.append(candidate)
        
        return AnalyzerOutput(
            section_id=section_id,
            needs_visualization=result.get("needs_visualization", False),
            candidates=candidates,
            reasoning=result.get("reasoning", ""),
        )
    
    def run_sync(
        self,
        content_title: str = "",
        content_description: str = "",
        section: Section = None,
        content_type: str = "research_paper",
        paper_title: str = "",
        paper_abstract: str = "",
    ) -> AnalyzerOutput:
        """Synchronous version for testing."""
        title = content_title or paper_title
        description = content_description or paper_abstract
        
        prompt = self._format_prompt(
            content_title=title,
            content_description=description,
            content_type=content_type,
            section_id=section.id,
            section_title=section.title,
            section_content=section.content,
            equations=self._format_equations(section),
            code_blocks=self._format_code_blocks(section),
        )
        
        text = self._call_llm_sync(prompt)

        result = self._parse_json_response(text)
        return self._parse_result(result, section.id)
