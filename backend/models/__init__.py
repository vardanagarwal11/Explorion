"""Data models for ingestion + generation pipeline."""

from .paper import (
    ArxivPaperMeta,
    Equation,
    Figure,
    Table,
    ParsedContent,
    Section,
    StructuredPaper,
)
from .generation import (
    VisualizationCandidate,
    AnalyzerOutput,
    Scene,
    VisualizationPlan,
    GeneratedCode,
    ValidatorOutput,
    Visualization,
)
from .voiceover import VoiceoverValidationOutput
from .content import (
    ContentType,
    VideoMode,
    NarrationStyle,
    TTSProvider,
    VIDEO_MODE_CONFIG,
    GitHubFileMeta,
    GitHubRepoMeta,
    TechnicalContentMeta,
    ContentMeta,
    StructuredContent,
    ProcessingConfig,
    UniversalProcessRequest,
)

__all__ = [
    # Paper models
    "ArxivPaperMeta",
    "Equation",
    "Figure",
    "Table",
    "ParsedContent",
    "Section",
    "StructuredPaper",
    # Generation models
    "VisualizationCandidate",
    "AnalyzerOutput",
    "Scene",
    "VisualizationPlan",
    "GeneratedCode",
    "ValidatorOutput",
    "Visualization",
    "VoiceoverValidationOutput",
    # Universal content models
    "ContentType",
    "VideoMode",
    "NarrationStyle",
    "TTSProvider",
    "VIDEO_MODE_CONFIG",
    "GitHubFileMeta",
    "GitHubRepoMeta",
    "TechnicalContentMeta",
    "ContentMeta",
    "StructuredContent",
    "ProcessingConfig",
    "UniversalProcessRequest",
]
