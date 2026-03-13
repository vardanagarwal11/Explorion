"""
Universal Content Ingestion Pipeline for ArXiviz.

Supports three content types:
- Research papers: ingest_paper(arxiv_id) → StructuredContent
- GitHub repos:    ingest_github_repo(url) → StructuredContent
- Technical text:  ingest_technical_content(url/text) → StructuredContent

Universal router: ingest_content(input) → StructuredContent
  Auto-detects content type from the input.

Pipeline outputs StructuredContent which the visualization agents consume.
"""

import logging
import re
from typing import Optional

from models.paper import (
    ArxivPaperMeta,
    ParsedContent,
    Section,
    StructuredPaper,
)
from models.content import (
    ContentType,
    ContentMeta,
    StructuredContent,
    UniversalProcessRequest,
)
from .arxiv_fetcher import (
    fetch_paper_meta,
    download_pdf,
    fetch_html_content,
    normalize_arxiv_id,
    validate_arxiv_id,
)
# pdf_parser imported lazily inside _parse_pdf_content() to avoid requiring PyMuPDF at import time
from .html_parser import parse_html, fetch_and_parse_html
from .section_extractor import extract_sections
from .section_formatter import format_sections

# Configure logging
logger = logging.getLogger(__name__)

# Simple in-memory cache for development
# In production, use Redis or database
_paper_cache: dict[str, StructuredPaper] = {}
_content_cache: dict[str, StructuredContent] = {}


# ═══════════════════════════════════════════════════════════
# Universal Router (auto-detect & dispatch)
# ═══════════════════════════════════════════════════════════

def _detect_content_type(
    url: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    text: Optional[str] = None,
) -> ContentType:
    """
    Auto-detect content type from the input.
    
    Detection logic:
    1. If arxiv_id is provided → research_paper
    2. If URL contains github.com → github_repo  
    3. If URL contains arxiv.org → research_paper
    4. If URL provided → technical_content (blog/docs)
    5. If text provided → technical_content
    """
    if arxiv_id:
        return ContentType.RESEARCH_PAPER
    
    if url:
        url_lower = url.lower()
        if "github.com" in url_lower:
            return ContentType.GITHUB_REPO
        if "arxiv.org" in url_lower:
            return ContentType.RESEARCH_PAPER
        return ContentType.TECHNICAL_CONTENT
    
    if text:
        return ContentType.TECHNICAL_CONTENT
    
    raise ValueError("No input provided. Supply a URL, arXiv ID, or text.")


def _extract_arxiv_id_from_url(url: str) -> str:
    """Extract arXiv ID from an arXiv URL."""
    # Match patterns like:
    #   https://arxiv.org/abs/1706.03762
    #   https://arxiv.org/pdf/1706.03762.pdf
    #   https://ar5iv.labs.arxiv.org/html/1706.03762
    match = re.search(r'(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)', url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract arXiv ID from URL: {url}")


async def ingest_content(
    url: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    text: Optional[str] = None,
    content_type: Optional[ContentType] = None,
    force_refresh: bool = False,
    **kwargs,
) -> StructuredContent:
    """
    Universal content ingestion entry point.
    
    Auto-detects content type from input and dispatches to the
    appropriate pipeline. This is the primary function the API
    and worker should call.
    
    Args:
        url: URL (arXiv, GitHub, blog, docs)
        arxiv_id: arXiv paper ID (shortcut for papers)
        text: Raw technical text or markdown
        content_type: Explicit type override (auto-detected if None)
        force_refresh: Bypass cache
        **kwargs: Passed to specific ingestion functions
        
    Returns:
        StructuredContent ready for the visualization pipeline
    """
    # Detect type
    detected_type = content_type or _detect_content_type(url, arxiv_id, text)
    logger.info(f"Ingesting content (type={detected_type.value})")
    
    if detected_type == ContentType.RESEARCH_PAPER:
        # Extract arXiv ID from URL if needed
        if not arxiv_id and url:
            arxiv_id = _extract_arxiv_id_from_url(url)
        if not arxiv_id:
            raise ValueError("arXiv ID required for research paper ingestion")
        
        paper = await ingest_paper(arxiv_id, force_refresh=force_refresh)
        return paper_to_structured_content(paper)
    
    elif detected_type == ContentType.GITHUB_REPO:
        if not url:
            raise ValueError("GitHub URL required for repository ingestion")
        return await ingest_github_repo(
            url, 
            branch=kwargs.get("branch"),
            focus_path=kwargs.get("focus_path"),
        )
    
    elif detected_type == ContentType.TECHNICAL_CONTENT:
        return await ingest_technical_content_wrapper(
            url=url, 
            text=text,
            title=kwargs.get("title"),
        )
    
    else:
        raise ValueError(f"Unsupported content type: {detected_type}")


# ═══════════════════════════════════════════════════════════
# Paper Ingestion (original, unchanged)
# ═══════════════════════════════════════════════════════════

async def ingest_paper(
    arxiv_id: str,
    force_refresh: bool = False,
    prefer_pdf: bool = False
) -> StructuredPaper:
    """
    Legacy entry point for paper ingestion.

    Takes an arXiv ID and returns a fully structured paper ready for
    the AI visualization pipeline.

    Args:
        arxiv_id: arXiv paper ID (e.g., "1706.03762" or "1706.03762v1")
        force_refresh: If True, bypass cache and re-fetch
        prefer_pdf: If True, use PDF even if HTML is available

    Returns:
        StructuredPaper with metadata and extracted sections

    Raises:
        ValueError: If paper not found or parsing fails
    """
    # Normalize ID
    arxiv_id = normalize_arxiv_id(arxiv_id)
    logger.info(f"Starting ingestion for paper: {arxiv_id}")

    # Check cache
    if not force_refresh:
        cached = await get_cached_paper(arxiv_id)
        if cached:
            logger.info(f"Returning cached paper: {arxiv_id}")
            return cached

    # Step 1: Fetch metadata from arXiv
    logger.info(f"Fetching metadata for: {arxiv_id}")
    meta = await fetch_paper_meta(arxiv_id)
    logger.info(f"Got paper: {meta.title}")

    # Step 2: Parse content (HTML preferred, PDF fallback)
    content: ParsedContent

    if meta.html_url and not prefer_pdf:
        # Try HTML first (cleaner structure)
        logger.info(f"Parsing ar5iv HTML: {meta.html_url}")
        try:
            content = await fetch_and_parse_html(meta.html_url)
            logger.info("Successfully parsed HTML content")
        except Exception as e:
            logger.warning(f"HTML parsing failed, falling back to PDF: {e}")
            content = await _parse_pdf_content(meta.pdf_url)
    else:
        # Use PDF
        content = await _parse_pdf_content(meta.pdf_url)

    # Step 3: Extract sections
    logger.info("Extracting sections from parsed content")
    sections = extract_sections(content, meta)
    raw_count = len(sections)
    total_chars = sum(len(s.content) for s in sections)
    logger.info(f"Extracted {raw_count} raw sections ({total_chars:,} chars total)")

    # Step 4: Summarize + organize (two-phase LLM pipeline)
    try:
        sections = await format_sections(sections, meta)
        logger.info(
            f"Section formatting succeeded: {raw_count} raw → {len(sections)} summarized sections"
        )
    except Exception as e:
        logger.error(
            f"Section formatting FAILED ({type(e).__name__}: {e}). "
            f"Falling back to {raw_count} raw sections. "
            f"This usually means the LLM call timed out or the API key is invalid."
        )

    # Step 5: Build final structure
    paper = StructuredPaper(
        meta=meta,
        sections=sections
    )

    # Step 6: Cache result
    await cache_paper(paper)

    logger.info(f"Ingestion complete for: {arxiv_id}")
    return paper


def paper_to_structured_content(paper: StructuredPaper) -> StructuredContent:
    """Convert a StructuredPaper to the universal StructuredContent format."""
    content_meta = ContentMeta(
        content_type=ContentType.RESEARCH_PAPER,
        content_id=paper.meta.arxiv_id,
        title=paper.meta.title,
        description=paper.meta.abstract,
        source_url=paper.meta.pdf_url,
        paper_meta=paper.meta,
    )
    return StructuredContent(
        meta=content_meta,
        sections=paper.sections,
    )


# ═══════════════════════════════════════════════════════════
# GitHub Repo Ingestion
# ═══════════════════════════════════════════════════════════

async def ingest_github_repo(
    url: str,
    branch: Optional[str] = None,
    focus_path: Optional[str] = None,
) -> StructuredContent:
    """
    Fetch and analyze a GitHub repository.
    
    Pipeline:
    1. Parse URL → owner/repo
    2. Fetch metadata, file tree, key file contents
    3. Analyze structure into explainer sections
    4. Return as StructuredContent
    """
    from .github_fetcher import fetch_github_repo
    from .github_analyzer import build_structured_content_from_repo
    
    logger.info(f"Starting GitHub repo ingestion: {url}")
    
    # Check cache
    cache_key = f"gh:{url}:{branch or ''}"
    if cache_key in _content_cache:
        logger.info(f"Returning cached GitHub content: {url}")
        return _content_cache[cache_key]
    
    # Fetch repo data
    repo_meta = await fetch_github_repo(url, branch=branch, focus_path=focus_path)
    
    # Analyze into sections
    structured = build_structured_content_from_repo(repo_meta)
    
    # Cache
    _content_cache[cache_key] = structured
    
    logger.info(f"GitHub ingestion complete: {url} → {len(structured.sections)} sections")
    return structured


# ═══════════════════════════════════════════════════════════
# Technical Content Ingestion
# ═══════════════════════════════════════════════════════════

async def ingest_technical_content_wrapper(
    url: Optional[str] = None,
    text: Optional[str] = None,
    title: Optional[str] = None,
) -> StructuredContent:
    """
    Fetch and parse technical content (blog, docs, or raw text).
    """
    from .content_fetcher import ingest_technical_content
    
    logger.info(f"Starting technical content ingestion (url={url is not None}, text={text is not None})")
    
    content = await ingest_technical_content(url=url, text=text, title=title)
    
    # Cache if URL-based
    if url:
        _content_cache[f"content:{url}"] = content
    
    logger.info(f"Technical content ingestion complete → {len(content.sections)} sections")
    return content


# ═══════════════════════════════════════════════════════════
# Helpers & Cache
# ═══════════════════════════════════════════════════════════

async def _parse_pdf_content(pdf_url: str) -> ParsedContent:
    """Helper to download and parse PDF."""
    logger.info(f"Downloading PDF: {pdf_url}")
    pdf_bytes = await download_pdf(pdf_url)
    logger.info(f"Downloaded {len(pdf_bytes)} bytes, parsing...")

    from .pdf_parser import parse_pdf  # lazy import — PyMuPDF is heavy
    content = parse_pdf(pdf_bytes)
    logger.info(
        f"Parsed PDF: {len(content.raw_text)} chars, "
        f"{len(content.equations)} equations, "
        f"{len(content.figures)} figures, "
        f"{len(content.tables)} tables"
    )
    return content


async def get_cached_paper(arxiv_id: str) -> Optional[StructuredPaper]:
    """Check cache for previously processed paper."""
    return _paper_cache.get(arxiv_id)


async def cache_paper(paper: StructuredPaper) -> None:
    """Cache processed paper for future requests."""
    _paper_cache[paper.meta.arxiv_id] = paper
    logger.debug(f"Cached paper: {paper.meta.arxiv_id}")


def clear_cache() -> None:
    """Clear all caches (useful for testing)."""
    _paper_cache.clear()
    _content_cache.clear()
    logger.info("All caches cleared")


# Export public API
__all__ = [
    # Universal router (preferred entry point)
    "ingest_content",
    
    # Type-specific entry points
    "ingest_paper",
    "ingest_github_repo",
    "ingest_technical_content_wrapper",
    
    # Conversion
    "paper_to_structured_content",

    # Cache functions
    "get_cached_paper",
    "cache_paper",
    "clear_cache",

    # Lower-level functions for flexibility
    "fetch_paper_meta",
    "download_pdf",
    "fetch_html_content",
    "parse_pdf",
    "parse_html",
    "fetch_and_parse_html",
    "extract_sections",
    "format_sections",
    "normalize_arxiv_id",
    "validate_arxiv_id",

    # Models (re-exported for convenience)
    "ArxivPaperMeta",
    "ParsedContent",
    "Section",
    "StructuredPaper",
    "StructuredContent",
]

