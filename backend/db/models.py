"""
SQLAlchemy database models for ArXiviz.

Models:
- Paper: Content item (arXiv paper, GitHub repo, or technical content)
- Section: Content sections/chapters
- Visualization: Manim visualizations for sections
- ProcessingJob: Background processing job status
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Paper(Base):
    """
    Content item — originally arXiv papers, now supports any content type.
    
    Table name kept as 'papers' for backward compatibility with existing DBs.
    The content_type column distinguishes between paper/repo/content.
    """
    __tablename__ = "papers"

    id = Column(String, primary_key=True)  # arxiv_id, "gh:owner/repo", or generated UUID
    title = Column(String, nullable=False)
    authors = Column(JSON)  # List of author names (or contributors for repos)
    abstract = Column(Text)  # Abstract or description
    pdf_url = Column(String)
    html_url = Column(String, nullable=True)
    
    # === Universal content fields ===
    content_type = Column(String, default="research_paper")  # research_paper, github_repo, technical_content
    source_url = Column(String, nullable=True)  # GitHub URL, blog URL, etc.
    extra_meta = Column(JSON, nullable=True)  # Type-specific metadata (repo stats, blog author, etc.)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sections = relationship("Section", back_populates="paper", cascade="all, delete-orphan")
    visualizations = relationship("Visualization", back_populates="paper", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="paper", cascade="all, delete-orphan")


class Section(Base):
    """Paper section/chapter — works for all content types."""
    __tablename__ = "sections"

    id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("papers.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)
    summary = Column(Text, nullable=True)  # LLM-formatted summary
    level = Column(Integer, default=1)  # Heading level (1=H1, 2=H2, etc.)
    order_index = Column(Integer, default=0)  # Order in content
    equations = Column(JSON, default=list)  # List of LaTeX equation strings
    figures = Column(JSON, default=list)  # List of figure dicts from ingestion
    tables = Column(JSON, default=list)  # List of table dicts from ingestion
    
    # === New fields for code/repo sections ===
    section_type = Column(String, nullable=True)  # code_module, architecture, data_flow, readme, etc.
    code_blocks = Column(JSON, default=list)  # Code snippets in this section

    # Relationships
    paper = relationship("Paper", back_populates="sections")


class Visualization(Base):
    """Manim visualization for a content section."""
    __tablename__ = "visualizations"

    id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("papers.id"), nullable=False)
    section_id = Column(String, ForeignKey("sections.id"), nullable=True)
    concept = Column(String, nullable=False)  # Human-readable concept name
    storyboard = Column(JSON, nullable=True)  # Animation storyboard data
    manim_code = Column(Text, nullable=True)  # Generated Manim Python code
    video_url = Column(String, nullable=True)  # URL to rendered video
    status = Column(String, default="pending")  # pending, rendering, complete, failed
    error = Column(Text, nullable=True)  # Error message if failed
    
    # === Narration fields ===
    narration_script = Column(JSON, nullable=True)  # Scene-by-scene narration text
    subtitle_url = Column(String, nullable=True)  # URL to SRT/VTT subtitle file
    audio_url = Column(String, nullable=True)  # URL to separate audio track
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    paper = relationship("Paper", back_populates="visualizations")


class ProcessingJob(Base):
    """Background processing job for content pipeline."""
    __tablename__ = "processing_jobs"

    id = Column(String, primary_key=True)
    paper_id = Column(String, ForeignKey("papers.id"), nullable=True)
    status = Column(String, default="queued")  # queued, processing, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 to 1.0
    sections_completed = Column(Integer, default=0)
    sections_total = Column(Integer, default=0)
    current_step = Column(String, nullable=True)  # Human-readable current step
    error = Column(Text, nullable=True)  # Error message if failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # === Processing configuration ===
    content_type = Column(String, default="research_paper")  # research_paper, github_repo, technical_content
    video_mode = Column(String, default="standard")  # quick, standard, deep_dive
    narration_style = Column(String, default="educational")
    tts_provider = Column(String, default="gtts")
    language = Column(String, default="en")  # ISO 639-1 language code

    # Relationships
    paper = relationship("Paper", back_populates="jobs")

