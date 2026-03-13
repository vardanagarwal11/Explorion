"""
Pydantic schemas defining the API contract.

Supports three processing modes:
- Legacy: POST /api/process (arXiv papers only, backward-compatible)
- Universal: POST /api/process/universal (any content type)
- Specific: POST /api/process/github, POST /api/process/content
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


# === Enums ===

class JobStatus(str, Enum):
    """Processing job status values."""
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VisualizationStatus(str, Enum):
    """Individual visualization rendering status."""
    pending = "pending"
    rendering = "rendering"
    complete = "complete"
    failed = "failed"


class ContentTypeEnum(str, Enum):
    """Supported content types for processing."""
    research_paper = "research_paper"
    github_repo = "github_repo"
    technical_content = "technical_content"


class VideoModeEnum(str, Enum):
    """Video generation depth modes."""
    quick = "quick"
    standard = "standard"
    deep_dive = "deep_dive"


class NarrationStyleEnum(str, Enum):
    """Voice narration style presets."""
    educational = "educational"
    teacher = "teacher"
    quick_summary = "quick_summary"
    youtube = "youtube"
    podcast = "podcast"


class TTSProviderEnum(str, Enum):
    """TTS engine providers."""
    gtts = "gtts"
    openai = "openai"
    elevenlabs = "elevenlabs"


# === Request Schemas ===

class ProcessRequest(BaseModel):
    """Request body for POST /api/process (legacy arXiv-only endpoint)."""
    arxiv_id: str = Field(
        ...,
        description="arXiv paper ID (e.g., '1706.03762' or '1706.03762v1')",
        examples=["1706.03762", "2301.07041v2"]
    )


class ProcessingConfigSchema(BaseModel):
    """Processing configuration for universal requests."""
    video_mode: VideoModeEnum = Field(
        VideoModeEnum.standard,
        description="Video depth: quick (2-3min), standard (5-8min), deep_dive (10-20min)"
    )
    narration_style: NarrationStyleEnum = Field(
        NarrationStyleEnum.educational,
        description="Voice narration style"
    )
    tts_provider: TTSProviderEnum = Field(
        TTSProviderEnum.gtts,
        description="Text-to-speech provider"
    )
    language: str = Field(
        "en",
        description="Narration language (ISO 639-1 code)"
    )
    voice_name: str = Field(
        "",
        description="Specific voice name (provider-dependent)"
    )
    generate_subtitles: bool = Field(
        True,
        description="Generate SRT/VTT subtitles"
    )


class UniversalProcessRequest(BaseModel):
    """
    Request body for POST /api/process/universal.
    
    Accepts any content type — arXiv papers, GitHub repos, or technical text.
    The system auto-detects the content type from the input.
    """
    url: Optional[str] = Field(
        None,
        description="URL (arXiv paper, GitHub repo, blog post, docs page)",
        examples=["https://arxiv.org/abs/1706.03762", "https://github.com/3b1b/manim"]
    )
    arxiv_id: Optional[str] = Field(
        None,
        description="arXiv paper ID (shorthand for research papers)",
        examples=["1706.03762"]
    )
    text: Optional[str] = Field(
        None,
        description="Raw technical text or markdown to explain"
    )
    content_type: Optional[ContentTypeEnum] = Field(
        None,
        description="Explicit content type. If omitted, auto-detected from input."
    )
    config: ProcessingConfigSchema = Field(
        default_factory=ProcessingConfigSchema,
        description="Processing configuration (video mode, narration, etc.)"
    )


class GitHubProcessRequest(BaseModel):
    """Request body for POST /api/process/github."""
    url: str = Field(
        ...,
        description="GitHub repository URL",
        examples=["https://github.com/3b1b/manim", "https://github.com/fastapi/fastapi"]
    )
    branch: Optional[str] = Field(
        None,
        description="Specific branch to analyze (defaults to repo's default branch)"
    )
    path: Optional[str] = Field(
        None,
        description="Specific folder/module path within the repo to focus on"
    )
    config: ProcessingConfigSchema = Field(
        default_factory=ProcessingConfigSchema,
        description="Processing configuration"
    )


class ContentProcessRequest(BaseModel):
    """Request body for POST /api/process/content."""
    url: Optional[str] = Field(
        None,
        description="URL of blog/documentation/article to explain",
    )
    text: Optional[str] = Field(
        None,
        description="Raw technical text or markdown to explain"
    )
    title: Optional[str] = Field(
        None,
        description="Optional title for the content"
    )
    config: ProcessingConfigSchema = Field(
        default_factory=ProcessingConfigSchema,
        description="Processing configuration"
    )


class RenderRequest(BaseModel):
    """Request body for POST /api/render (test endpoint)."""
    code: str = Field(
        ...,
        description="Complete Manim Python code to render",
        examples=[
            "from manim import *\n\nclass TestScene(Scene):\n    def construct(self):\n        circle = Circle(color=BLUE)\n        self.play(Create(circle))\n        self.wait()"
        ]
    )
    quality: str = Field(
        default="low_quality",
        description="Render quality: low_quality, medium_quality, or high_quality"
    )


class RenderResponse(BaseModel):
    """Response for POST /api/render."""
    video_id: str = Field(..., description="ID of the rendered video")
    video_url: str = Field(..., description="URL to access the rendered video")
    scene_name: str = Field(..., description="Detected scene class name")
    message: str = Field(..., description="Status message")


# === Response Schemas ===

class ProcessResponse(BaseModel):
    """Response for POST /api/process (and all process endpoints)."""
    job_id: str = Field(..., description="Unique job identifier for polling")
    content_id: str = Field(..., description="Content identifier (arXiv ID, repo name, etc.)")
    content_type: ContentTypeEnum = Field(ContentTypeEnum.research_paper, description="Detected content type")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Human-readable status message")


class StepInfo(BaseModel):
    """Individual processing step status."""
    name: str = Field(..., description="Step name (e.g., 'fetch_paper', 'render_videos')")
    status: str = Field(..., description="Step status: pending, in_progress, complete, failed")
    duration_ms: Optional[int] = Field(None, description="Time taken in milliseconds, null if not started")


class StatusResponse(BaseModel):
    """Response for GET /api/status/{job_id}."""
    job_id: str
    content_id: str = Field(..., description="Content identifier")
    content_type: ContentTypeEnum = Field(ContentTypeEnum.research_paper)
    status: JobStatus
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress 0.0 to 1.0")
    current_step: Optional[str] = Field(None, description="Current processing step description")
    sections_completed: int = Field(0, description="Number of sections processed")
    sections_total: int = Field(0, description="Total number of sections")
    video_mode: VideoModeEnum = Field(VideoModeEnum.standard, description="Video generation mode")
    steps_completed: list[StepInfo] = Field(default_factory=list, description="Detailed step-by-step progress")
    error: Optional[str] = Field(None, description="Error message if status is failed")
    created_at: datetime
    estimated_completion: Optional[datetime] = None


class SectionResponse(BaseModel):
    """Section data within a content item."""
    id: str
    title: str
    content: str
    summary: Optional[str] = Field(None, description="LLM-formatted summary of the section content")
    level: int = Field(..., description="Heading level (1=H1, 2=H2, etc.)")
    order_index: int = Field(..., description="Order in which sections appear")
    section_type: Optional[str] = Field(None, description="Section type: code_module, architecture, etc.")
    equations: list[str] = Field(default_factory=list, description="LaTeX equations in this section")
    code_blocks: list[str] = Field(default_factory=list, description="Code snippets in this section")
    video_url: Optional[str] = Field(None, description="URL to visualization video for this section, if available")


class VisualizationResponse(BaseModel):
    """Visualization data for a content section."""
    id: str
    section_id: str = Field(..., description="ID of the section this visualization belongs to")
    concept: str = Field(..., description="Human-readable concept being visualized")
    video_url: Optional[str] = Field(None, description="URL to rendered video, null if not ready")
    subtitle_url: Optional[str] = Field(None, description="URL to subtitle file")
    audio_url: Optional[str] = Field(None, description="URL to separate audio track")
    status: VisualizationStatus


class PaperResponse(BaseModel):
    """Response for GET /api/paper/{content_id} or GET /api/content/{content_id}."""
    paper_id: str = Field(..., description="Content ID")
    title: str
    authors: list[str]
    abstract: str
    pdf_url: str
    html_url: Optional[str] = None
    content_type: ContentTypeEnum = Field(ContentTypeEnum.research_paper)
    source_url: Optional[str] = None
    sections: list[SectionResponse]
    visualizations: list[VisualizationResponse]
    processed_at: datetime


class VideoResponse(BaseModel):
    """Response for GET /api/video/{video_id}."""
    video_id: str
    url: str = Field(..., description="Public URL to the video file")
    content_type: str = Field(default="video/mp4")


class PaperSummary(BaseModel):
    """Summary of a content item for list endpoints."""
    paper_id: str
    title: str
    authors: list[str]
    content_type: ContentTypeEnum = Field(ContentTypeEnum.research_paper)
    visualization_count: int = Field(0, description="Number of visualizations")
    processed_at: datetime


class PaperListResponse(BaseModel):
    """Response for GET /api/papers."""
    papers: list[PaperSummary]
    total: int


class HealthResponse(BaseModel):
    """Response for GET /api/health."""
    status: str = Field(..., description="'healthy' or 'unhealthy'")
    version: str
    services: dict[str, str] = Field(
        ...,
        description="Status of dependent services",
        examples=[{"database": "connected", "redis": "connected", "modal": "configured"}]
    )

