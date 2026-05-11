"""
ArXiviz Agent Pipeline

Multi-agent AI pipeline for generating Manim visualizations
from structured academic papers / repos / technical content.

LLM routing (first key in .env wins):
    NIM_API_KEY      → NVIDIA NIM  (meta/llama-3.1-70b-instruct)
    GROQ_API_KEY     → Groq Cloud  (llama-3.3-70b-versatile)
    GEMINI_API_KEY   → Google Gemini (gemini-1.5-pro)

Usage:
    from agents import generate_visualizations
    from models import StructuredPaper

    paper = StructuredPaper(...)
    visualizations = await generate_visualizations(paper)
"""

try:
    from .base import BaseAgent, get_provider, get_model_name, call_llm
    from .section_analyzer import SectionAnalyzer
    from .visualization_planner import VisualizationPlanner
    from .manim_generator import ManimGenerator
    from .code_validator import CodeValidator
    from .voiceover_script_validator import VoiceoverScriptValidator
    from .pipeline import (
        generate_visualizations,
        generate_universal_visualizations,
        generate_single_visualization,
    )
except ImportError:
    from agents.base import BaseAgent, get_provider, get_model_name, call_llm
    from agents.section_analyzer import SectionAnalyzer
    from agents.visualization_planner import VisualizationPlanner
    from agents.manim_generator import ManimGenerator
    from agents.code_validator import CodeValidator
    from agents.voiceover_script_validator import VoiceoverScriptValidator
    from agents.pipeline import (
        generate_visualizations,
        generate_universal_visualizations,
        generate_single_visualization,
    )

__all__ = [
    "BaseAgent",
    "get_provider",
    "get_model_name",
    "call_llm",
    "SectionAnalyzer",
    "VisualizationPlanner",
    "ManimGenerator",
    "CodeValidator",
    "VoiceoverScriptValidator",
    "generate_visualizations",
    "generate_universal_visualizations",
    "generate_single_visualization",
]
