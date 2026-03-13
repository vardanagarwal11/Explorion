"""
Jobs package for ArXiviz.

Provides background job processing for paper processing pipeline.
"""

from .worker import process_paper_job
from .sample_manim import get_sample_visualizations, get_visualizations_for_sections

__all__ = ["process_paper_job", "get_sample_visualizations", "get_visualizations_for_sections"]
