"""
FastAPI routes for the ArXiviz API.

Endpoints:
- POST /api/process           — legacy arXiv paper processing
- POST /api/process/universal  — any content type (auto-detect)
- POST /api/process/github     — GitHub repo explainer
- POST /api/process/content    — blog/docs/text explainer
- GET  /api/status/{job_id}    — job progress polling
- GET  /api/paper/{content_id} — processed content details
- GET  /api/papers             — list all processed content
- GET  /api/video/{video_id}   — video file serving
- POST /api/render             — test Manim rendering
- GET  /api/health             — service health check
"""

import os
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .schemas import (
    ProcessRequest,
    UniversalProcessRequest,
    GitHubProcessRequest,
    ContentProcessRequest,
    ProcessResponse,
    StatusResponse,
    StepInfo,
    PaperResponse,
    PaperListResponse,
    PaperSummary,
    SectionResponse,
    VisualizationResponse,
    VideoResponse,
    HealthResponse,
    JobStatus,
    VisualizationStatus,
    ContentTypeEnum,
    VideoModeEnum,
    RenderRequest,
    RenderResponse,
)
from db.connection import get_db
from db import queries
from rendering import process_visualization, get_video_path, get_video_url, extract_scene_name
from jobs import process_paper_job
from jobs.worker import process_universal_job

router = APIRouter(prefix="/api")


# ═══════════════════════════════════════════════════════════
# Processing Endpoints
# ═══════════════════════════════════════════════════════════

@router.post("/process", response_model=ProcessResponse)
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start processing an arXiv paper (legacy endpoint).

    Returns immediately with a job_id. Poll /api/status/{job_id} for progress.
    """
    # Create job in database
    job_id = await queries.create_job(db, request.arxiv_id)

    # Start background processing
    background_tasks.add_task(process_paper_job, job_id, request.arxiv_id)

    return ProcessResponse(
        job_id=job_id,
        content_id=request.arxiv_id,
        content_type=ContentTypeEnum.research_paper,
        status=JobStatus.queued,
        message="Processing started. Poll /api/status/{job_id} for updates."
    )


@router.post("/process/universal", response_model=ProcessResponse)
async def start_universal_processing(
    request: UniversalProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start processing any content type.

    Auto-detects content type from input (arXiv URL, GitHub URL, blog URL, or raw text).
    You can also explicitly specify content_type.
    
    Returns immediately with a job_id. Poll /api/status/{job_id} for progress.
    """
    from ingestion import _detect_content_type
    from models.content import ContentType
    
    # Validate input
    if not request.url and not request.arxiv_id and not request.text:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: url, arxiv_id, or text"
        )
    
    # Detect content type
    if request.content_type:
        detected_type = request.content_type.value
    else:
        try:
            ct = _detect_content_type(request.url, request.arxiv_id, request.text)
            detected_type = ct.value
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Determine content_id
    if request.arxiv_id:
        content_id = request.arxiv_id
    elif request.url:
        if detected_type == "github_repo":
            # Extract owner/repo from URL
            from ingestion.github_fetcher import parse_github_url
            try:
                parsed = parse_github_url(request.url)
                content_id = f"gh:{parsed['owner']}/{parsed['repo']}"
            except ValueError:
                content_id = f"url:{request.url[:60]}"
        elif detected_type == "research_paper":
            from ingestion import _extract_arxiv_id_from_url
            try:
                content_id = _extract_arxiv_id_from_url(request.url)
            except ValueError:
                content_id = f"url:{request.url[:60]}"
        else:
            import hashlib
            content_id = f"content:{hashlib.sha256(request.url.encode()).hexdigest()[:12]}"
    else:
        import hashlib
        content_id = f"content:{hashlib.sha256(request.text[:200].encode()).hexdigest()[:12]}"
    
    # Create job with processing config
    job_id = await queries.create_job(
        db,
        paper_id=content_id,
        content_type=detected_type,
        video_mode=request.config.video_mode.value,
        narration_style=request.config.narration_style.value,
        tts_provider=request.config.tts_provider.value,
        language=request.config.language,
    )
    
    # Start background processing
    background_tasks.add_task(
        _process_universal_job,
        job_id=job_id,
        content_id=content_id,
        content_type=detected_type,
        url=request.url,
        arxiv_id=request.arxiv_id,
        text=request.text,
        config=request.config.model_dump(),
    )
    
    return ProcessResponse(
        job_id=job_id,
        content_id=content_id,
        content_type=ContentTypeEnum(detected_type),
        status=JobStatus.queued,
        message=f"Processing {detected_type.replace('_', ' ')} started. Poll /api/status/{job_id} for updates."
    )


@router.post("/process/github", response_model=ProcessResponse)
async def start_github_processing(
    request: GitHubProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start processing a GitHub repository.

    Fetches repo metadata, analyzes structure, and generates animated explainer.
    """
    from ingestion.github_fetcher import parse_github_url
    
    # Parse and validate URL
    try:
        parsed = parse_github_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    content_id = f"gh:{parsed['owner']}/{parsed['repo']}"
    
    # Create job
    job_id = await queries.create_job(
        db,
        paper_id=content_id,
        content_type="github_repo",
        video_mode=request.config.video_mode.value,
        narration_style=request.config.narration_style.value,
        tts_provider=request.config.tts_provider.value,
        language=request.config.language,
    )
    
    # Start background processing
    background_tasks.add_task(
        _process_universal_job,
        job_id=job_id,
        content_id=content_id,
        content_type="github_repo",
        url=request.url,
        config=request.config.model_dump(),
        branch=request.branch,
        focus_path=request.path,
    )
    
    return ProcessResponse(
        job_id=job_id,
        content_id=content_id,
        content_type=ContentTypeEnum.github_repo,
        status=JobStatus.queued,
        message=f"GitHub repo processing started for {parsed['owner']}/{parsed['repo']}."
    )


@router.post("/process/content", response_model=ProcessResponse)
async def start_content_processing(
    request: ContentProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start processing technical content (blog, docs, or raw text).
    """
    if not request.url and not request.text:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'url' or 'text'"
        )
    
    import hashlib
    source = request.url or request.text[:200]
    content_id = f"content:{hashlib.sha256(source.encode()).hexdigest()[:12]}"
    
    # Create job
    job_id = await queries.create_job(
        db,
        paper_id=content_id,
        content_type="technical_content",
        video_mode=request.config.video_mode.value,
        narration_style=request.config.narration_style.value,
        tts_provider=request.config.tts_provider.value,
        language=request.config.language,
    )
    
    # Start background processing
    background_tasks.add_task(
        _process_universal_job,
        job_id=job_id,
        content_id=content_id,
        content_type="technical_content",
        url=request.url,
        text=request.text,
        config=request.config.model_dump(),
        title=request.title,
    )
    
    return ProcessResponse(
        job_id=job_id,
        content_id=content_id,
        content_type=ContentTypeEnum.technical_content,
        status=JobStatus.queued,
        message="Technical content processing started."
    )


async def _process_universal_job(
    job_id: str,
    content_id: str,
    content_type: str,
    url: str | None = None,
    arxiv_id: str | None = None,
    text: str | None = None,
    config: dict | None = None,
    **kwargs,
):
    """
    Background task adapter for universal content processing.
    
    Routes to the full pipeline in jobs.worker, which handles:
    - Ingestion
    - Visualization generation with ProcessingConfig
    - Rendering
    - TTS audio + subtitle generation
    """
    import logging
    _logger = logging.getLogger(__name__)
    
    config = config or {}
    video_mode = config.get("video_mode", "standard")
    narration_style = config.get("narration_style", "educational")
    tts_provider = config.get("tts_provider", "gtts")
    language = config.get("language", "en")
    
    # For arXiv papers, use the legacy path which already works fully
    if content_type == "research_paper" and arxiv_id:
        from jobs.worker import process_paper_job as _paper_job
        await _paper_job(job_id, arxiv_id)
        return
    
    # For all other types, use the universal worker
    try:
        await process_universal_job(
            job_id=job_id,
            content_id=content_id,
            content_type=content_type,
            video_mode=video_mode,
            narration_style=narration_style,
            tts_provider=tts_provider,
            language=language,
            source_url=url,
            source_text=text,
        )
    except Exception as e:
        _logger.exception(f"Universal job {job_id} failed")


# ═══════════════════════════════════════════════════════════
# Status & Data Endpoints
# ═══════════════════════════════════════════════════════════

@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get the processing status of a job.

    Poll this endpoint to track progress.
    """
    job = await queries.get_job(db, job_id)

    if job:
        # Build steps_completed from job progress
        progress = job.progress or 0.0
        steps = [
            StepInfo(
                name="ingest_content",
                status="complete" if progress > 0.2 else ("in_progress" if progress > 0.0 else "pending"),
            ),
            StepInfo(
                name="analyze_sections",
                status="complete" if progress > 0.3 else ("in_progress" if progress > 0.2 else "pending"),
            ),
            StepInfo(
                name="generate_visualizations",
                status="complete" if progress > 0.6 else ("in_progress" if progress > 0.3 else "pending"),
            ),
            StepInfo(
                name="render_videos",
                status="complete" if progress >= 1.0 else ("in_progress" if progress > 0.6 else "pending"),
            ),
        ]

        return StatusResponse(
            job_id=job.id,
            content_id=job.paper_id or "unknown",
            content_type=ContentTypeEnum(getattr(job, 'content_type', 'research_paper') or 'research_paper'),
            status=JobStatus(job.status),
            progress=progress,
            current_step=job.current_step,
            sections_completed=job.sections_completed or 0,
            sections_total=job.sections_total or 0,
            video_mode=VideoModeEnum(getattr(job, 'video_mode', 'standard') or 'standard'),
            steps_completed=steps,
            error=job.error,
            created_at=job.created_at,
            estimated_completion=job.created_at + timedelta(minutes=5) if job.status != "completed" else None
        )

    # Job not found - return 404
    raise HTTPException(
        status_code=404,
        detail=f"Job '{job_id}' not found"
    )


@router.get("/paper/{content_id:path}", response_model=PaperResponse)
async def get_paper(content_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get processed content with all sections and visualizations.

    Works for any content type (papers, repos, technical content).
    Returns 404 if the content hasn't been processed yet.
    """
    # Handle version suffix for arXiv IDs
    if "v" in content_id and not content_id.startswith("gh:") and not content_id.startswith("content:"):
        base_id = content_id.split("v")[0]
    else:
        base_id = content_id

    paper = await queries.get_paper(db, base_id)

    if paper:
        # Convert database models to response schemas
        sections = sorted(paper.sections, key=lambda s: s.order_index)

        # Build section_id -> video_url lookup from visualizations
        section_video_map = {}
        section_status_map = {}
        for v in paper.visualizations:
            if v.video_url and v.section_id:
                existing_status = section_status_map.get(v.section_id)
                if v.section_id not in section_video_map:
                    section_video_map[v.section_id] = v.video_url
                    section_status_map[v.section_id] = v.status
                elif v.status == "complete" and existing_status != "complete":
                    section_video_map[v.section_id] = v.video_url
                    section_status_map[v.section_id] = v.status

        return PaperResponse(
            paper_id=paper.id,
            title=paper.title,
            authors=paper.authors or [],
            abstract=paper.abstract or "",
            pdf_url=paper.pdf_url or "",
            html_url=paper.html_url,
            content_type=ContentTypeEnum(getattr(paper, 'content_type', 'research_paper') or 'research_paper'),
            source_url=getattr(paper, 'source_url', None),
            sections=[
                SectionResponse(
                    id=s.id,
                    title=s.title,
                    content=s.content or "",
                    summary=s.summary or None,
                    level=s.level,
                    order_index=s.order_index,
                    section_type=getattr(s, 'section_type', None),
                    equations=s.equations or [],
                    code_blocks=getattr(s, 'code_blocks', []) or [],
                    video_url=section_video_map.get(s.id),
                )
                for s in sections
            ],
            visualizations=[
                VisualizationResponse(
                    id=v.id,
                    section_id=v.section_id,
                    concept=v.concept,
                    video_url=v.video_url,
                    subtitle_url=getattr(v, 'subtitle_url', None),
                    audio_url=getattr(v, 'audio_url', None),
                    status=VisualizationStatus(v.status),
                )
                for v in paper.visualizations
            ],
            processed_at=paper.updated_at or paper.created_at or datetime.utcnow(),
        )

    raise HTTPException(
        status_code=404,
        detail=f"Content '{content_id}' not found. Process it first with POST /api/process/universal"
    )


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    content_type: ContentTypeEnum | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all processed content items.

    Optionally filter by content_type (research_paper, github_repo, technical_content).
    """
    papers = await queries.list_papers(db)
    
    # Filter by content_type if specified
    if content_type:
        papers = [p for p in papers if getattr(p, 'content_type', 'research_paper') == content_type.value]

    return PaperListResponse(
        papers=[
            PaperSummary(
                paper_id=p.id,
                title=p.title,
                authors=p.authors or [],
                content_type=ContentTypeEnum(getattr(p, 'content_type', 'research_paper') or 'research_paper'),
                visualization_count=len(p.visualizations) if p.visualizations else 0,
                processed_at=p.updated_at or p.created_at or datetime.utcnow(),
            )
            for p in papers
        ],
        total=len(papers),
    )


# ═══════════════════════════════════════════════════════════
# Video & Rendering Endpoints
# ═══════════════════════════════════════════════════════════

@router.get("/video/{video_id}")
async def get_video(video_id: str):
    """
    Get a rendered visualization video.

    Returns the actual video file if it exists locally,
    or redirects to the cloud URL (R2) if available.
    """
    # Try local file first
    video_path = get_video_path(video_id)
    if video_path and video_path.exists():
        return FileResponse(
            path=str(video_path),
            media_type="video/mp4",
            filename=f"{video_id}.mp4"
        )

    # Try cloud URL (R2 mode)
    cloud_url = get_video_url(video_id)
    if cloud_url and cloud_url.startswith("http"):
        return RedirectResponse(url=cloud_url, status_code=302)

    raise HTTPException(
        status_code=404,
        detail=f"Video '{video_id}' not found"
    )


@router.post("/render", response_model=RenderResponse)
async def render_manim(request: RenderRequest):
    """
    Test endpoint to render Manim code directly.

    This is for testing/development purposes.
    """
    try:
        video_id = f"test_{uuid.uuid4().hex[:8]}"
        scene_name = extract_scene_name(request.code)

        video_url = await process_visualization(
            viz_id=video_id,
            manim_code=request.code,
            quality=request.quality
        )

        return RenderResponse(
            video_id=video_id,
            video_url=video_url,
            scene_name=scene_name,
            message=f"Successfully rendered {scene_name}"
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rendering failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════

@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.

    Returns status of the API and dependent services.
    """
    import subprocess

    # Test database connection
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Test Manim availability
    manim_status = "not found"
    try:
        manim_exe = os.getenv("MANIM_EXECUTABLE", "manim")
        result = subprocess.run(
            [manim_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            manim_status = f"available ({version})"
        else:
            manim_status = "error: command failed"
    except FileNotFoundError:
        manim_status = "not installed"
    except Exception as e:
        manim_status = f"error: {str(e)}"

    # Test storage connectivity
    from rendering.storage import STORAGE_MODE, get_backend
    storage_status = "local"
    if STORAGE_MODE == "r2":
        backend = get_backend()
        if hasattr(backend, "check_connectivity"):
            try:
                storage_status = "r2: connected" if backend.check_connectivity() else "r2: unreachable"
            except Exception as e:
                storage_status = f"r2: error ({e})"
        else:
            storage_status = "r2: configured"

    # Check Modal configuration
    from rendering import RENDER_MODE
    modal_status = "not configured"
    if RENDER_MODE == "modal":
        modal_token = os.getenv("MODAL_TOKEN_ID")
        modal_status = "configured" if modal_token else "missing MODAL_TOKEN_ID"

    # Check GitHub token
    github_status = "configured" if os.getenv("GITHUB_TOKEN") else "unauthenticated (60 req/hr limit)"

    # Overall health
    if RENDER_MODE == "modal":
        all_healthy = db_status == "connected"
    else:
        all_healthy = db_status == "connected" and "available" in manim_status

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version="0.2.0",
        services={
            "database": db_status,
            "manim": manim_status if RENDER_MODE != "modal" else f"offloaded to modal ({manim_status})",
            "storage": storage_status,
            "github": github_status,
            "modal": modal_status,
        }
    )

