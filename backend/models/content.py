"""
Universal content models for Explorion.

Supports three input types:
- Research papers (arXiv, DOI, PDF upload)
- GitHub repositories
- Technical content (blogs, docs, pasted text)

All content types are normalized into a common StructuredContent
interface that the visualization pipeline can consume uniformly.
"""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

from .paper import Section, ArxivPaperMeta


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class ContentType(str, Enum):
    """Supported input content types."""
    RESEARCH_PAPER = "research_paper"
    GITHUB_REPO = "github_repo"
    TECHNICAL_CONTENT = "technical_content"


class VideoMode(str, Enum):
    """Video generation depth modes."""
    QUICK = "quick"           # 2-3 min overview
    STANDARD = "standard"     # 5-8 min explanation
    DEEP_DIVE = "deep_dive"   # 10-20 min comprehensive walkthrough


class NarrationStyle(str, Enum):
    """Voice narration style presets."""
    EDUCATIONAL = "educational"       # Default, clear and structured
    TEACHER = "teacher"               # Slow, clear, beginner-friendly
    QUICK_SUMMARY = "quick_summary"   # Fast-paced overview
    YOUTUBE = "youtube"               # YouTube explainer style, engaging
    PODCAST = "podcast"               # Conversational, deep discussion


class TTSProvider(str, Enum):
    """Text-to-speech engine providers."""
    GTTS = "gtts"               # Google TTS (free, decent quality)
    OPENAI = "openai"           # OpenAI TTS (high quality)
    ELEVENLABS = "elevenlabs"   # ElevenLabs (premium, emotional)


# ═══════════════════════════════════════════════════════════
# Video Mode Configuration
# ═══════════════════════════════════════════════════════════

VIDEO_MODE_CONFIG = {
    VideoMode.QUICK: {
        "max_visualizations": 3,
        "duration_range": (15, 30),   # seconds per visualization
        "max_scenes_per_viz": 4,
        "description": "2-3 minute quick overview",
    },
    VideoMode.STANDARD: {
        "max_visualizations": 5,
        "duration_range": (30, 45),
        "max_scenes_per_viz": 6,
        "description": "5-8 minute standard explanation",
    },
    VideoMode.DEEP_DIVE: {
        "max_visualizations": 10,
        "duration_range": (45, 90),
        "max_scenes_per_viz": 10,
        "description": "10-20 minute comprehensive walkthrough",
    },
}


# ═══════════════════════════════════════════════════════════
# GitHub Repository Models
# ═══════════════════════════════════════════════════════════

class GitHubFileMeta(BaseModel):
    """Metadata for a file in a GitHub repository."""
    path: str = Field(..., description="File path relative to repo root")
    name: str = Field(..., description="File name")
    size: int = Field(0, description="File size in bytes")
    language: str | None = Field(None, description="Detected programming language")
    content: str | None = Field(None, description="File content (loaded for key files)")


class GitHubRepoMeta(BaseModel):
    """Metadata about a GitHub repository."""
    owner: str = Field(..., description="Repository owner/organization")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full name: owner/name")
    url: str = Field(..., description="GitHub URL")
    description: str = Field("", description="Repository description")
    default_branch: str = Field("main", description="Default branch name")
    branch: str | None = Field(None, description="Specific branch to analyze")
    languages: dict[str, int] = Field(default_factory=dict, description="Languages and byte counts")
    primary_language: str | None = Field(None, description="Primary programming language")
    stars: int = Field(0, description="Star count")
    forks: int = Field(0, description="Fork count")
    topics: list[str] = Field(default_factory=list, description="Repository topics/tags")
    license: str | None = Field(None, description="License type")
    created_at: datetime | None = Field(None, description="Repository creation date")
    updated_at: datetime | None = Field(None, description="Last update date")
    readme_content: str = Field("", description="README.md content")
    tree: list[GitHubFileMeta] = Field(default_factory=list, description="File tree (filtered)")
    key_files: list[GitHubFileMeta] = Field(
        default_factory=list,
        description="Key files with content loaded (configs, entry points, etc.)"
    )
    dependencies: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Dependencies by package manager (e.g., {'npm': ['react', 'next'], 'pip': ['fastapi']})"
    )


class TechnicalContentMeta(BaseModel):
    """Metadata about technical content (blog, docs, paste)."""
    source_url: str | None = Field(None, description="Source URL if fetched from web")
    title: str = Field("", description="Content title")
    author: str | None = Field(None, description="Content author")
    source_type: str = Field("text", description="Source type: url, text, markdown")
    word_count: int = Field(0, description="Total word count")
    has_code_blocks: bool = Field(False, description="Whether content contains code blocks")
    has_equations: bool = Field(False, description="Whether content contains LaTeX equations")
    fetched_at: datetime | None = Field(None, description="When the content was fetched")


# ═══════════════════════════════════════════════════════════
# Universal Content Interface
# ═══════════════════════════════════════════════════════════

class ContentMeta(BaseModel):
    """
    Unified metadata wrapper that holds any content type's metadata.
    
    The visualization pipeline uses this as its input interface,
    regardless of whether the source is a paper, repo, or blog post.
    """
    content_type: ContentType = Field(..., description="Type of content")
    content_id: str = Field(..., description="Unique identifier (arxiv_id, owner/repo, or generated)")
    title: str = Field(..., description="Content title")
    description: str = Field("", description="Short description or abstract")
    source_url: str | None = Field(None, description="Source URL")
    
    # Type-specific metadata (only one is populated)
    paper_meta: ArxivPaperMeta | None = Field(None, description="Paper metadata if research_paper")
    repo_meta: GitHubRepoMeta | None = Field(None, description="Repo metadata if github_repo")
    content_meta: TechnicalContentMeta | None = Field(None, description="Content metadata if technical_content")


class StructuredContent(BaseModel):
    """
    Universal structured content — the output of any ingestion pipeline.
    
    This is the single input format the visualization pipeline accepts.
    It generalizes StructuredPaper to work with any content type.
    """
    meta: ContentMeta = Field(..., description="Content metadata")
    sections: list[Section] = Field(default_factory=list, description="Structured sections")
    
    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return self.model_dump()
    
    def get_section_by_id(self, section_id: str) -> Section | None:
        """Find a section by its ID."""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def get_context(self) -> str:
        """Get content context (title + description) for prompts."""
        return f"{self.meta.title}\n\n{self.meta.description}"
    
    def get_all_equations(self) -> list:
        """Get all equations from all sections."""
        equations = []
        for section in self.sections:
            equations.extend(section.equations)
        return equations


class ProcessingConfig(BaseModel):
    """Configuration for how content should be processed."""
    video_mode: VideoMode = Field(VideoMode.STANDARD, description="Video generation depth")
    narration_style: NarrationStyle = Field(NarrationStyle.EDUCATIONAL, description="Voice narration style")
    tts_provider: TTSProvider = Field(TTSProvider.GTTS, description="TTS engine to use")
    language: str = Field("en", description="Narration language code (ISO 639-1)")
    voice_name: str = Field("", description="Specific voice name (provider-dependent)")
    generate_subtitles: bool = Field(True, description="Whether to generate SRT/VTT subtitles")
    background_music: bool = Field(False, description="Whether to add background music")


class UniversalProcessRequest(BaseModel):
    """
    Universal input request — accepts any content type.
    
    The system auto-detects content type from the input, or you can
    specify it explicitly via content_type.
    """
    # Input (at least one required)
    url: str | None = Field(None, description="URL (arXiv, GitHub, blog, DOI)")
    arxiv_id: str | None = Field(None, description="arXiv paper ID (e.g., '1706.03762')")
    text: str | None = Field(None, description="Raw technical text to explain")
    
    # Processing config
    content_type: ContentType | None = Field(
        None, 
        description="Explicit content type. If omitted, auto-detected from input."
    )
    config: ProcessingConfig = Field(
        default_factory=ProcessingConfig,
        description="Processing configuration (video mode, narration, etc.)"
    )
