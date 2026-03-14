"""
Background job processing for arXivisual.

Processes all content types asynchronously with progress tracking.
Supports legacy paper-only mode and universal content processing.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from db.connection import async_session_maker
from db import queries
from db.models import Section
from rendering import process_visualization, get_video_path
# NOTE: agents.pipeline is imported lazily inside functions that use it
# to avoid pulling in heavy/optional dependencies at startup.
from models.paper import (
    ArxivPaperMeta,
    Equation,
    Figure,
    Section as PaperSection,
    StructuredPaper,
    Table,
)
from models.content import (
    StructuredContent,
    ContentMeta,
    ContentType,
    ProcessingConfig,
    VideoMode,
    NarrationStyle,
    TTSProvider,
)

logger = logging.getLogger(__name__)


class ProgressBar:
    """Simple progress bar for logging output."""

    def __init__(self, total: int, name: str = "Progress"):
        self.total = total
        self.current = 0
        self.name = name
        self.start_time = datetime.now()

    def update(self, increment: int = 1):
        self.current += increment
        self._display()

    def _display(self):
        """Display progress bar in logs."""
        if self.total == 0:
            return

        percent = self.current / self.total
        bar_length = 30
        filled = int(bar_length * percent)
        bar = "█" * filled + "░" * (bar_length - filled)

        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.current > 0 and percent > 0:
            avg_time = elapsed / self.current
            eta_seconds = avg_time * (self.total - self.current)
            eta_str = f" ETA: {int(eta_seconds)}s"
        else:
            eta_str = ""

        percent_str = f"{percent*100:5.1f}%"
        logger.info(f"  [{self.name}] {bar} {percent_str} ({self.current}/{self.total}){eta_str}")


# ═══════════════════════════════════════════════════════════
# Legacy Paper Processing (backward compatible)
# ═══════════════════════════════════════════════════════════

async def process_paper_job(job_id: str, arxiv_id: str):
    """
    Legacy job processing function for arXiv papers.
    
    Pipeline:
    1. Ingest paper from arXiv (real fetch + parse)
    2. Store paper and sections in database
    3. Pick visualizations for sections
    4. Render all visualizations
    5. Update job status to completed
    """
    logger.info("=" * 60)
    logger.info(f"STARTING JOB: {job_id}")
    logger.info(f"ArXiv ID: {arxiv_id}")
    logger.info("=" * 60)

    async with async_session_maker() as db:
        try:
            # Step 1: Ingest paper from arXiv
            logger.info("STEP 1: Ingesting paper from arXiv")
            logger.info("-" * 60)

            await queries.update_job_status(
                db, job_id,
                status="processing",
                current_step="Fetching paper from arXiv",
                progress=0.10
            )

            paper_exists = await queries.paper_exists(db, arxiv_id)
            if paper_exists:
                logger.info(f"Paper {arxiv_id} already exists in database, skipping ingestion")
            else:
                logger.info(f"Paper {arxiv_id} not found, fetching from arXiv...")

            if not paper_exists:
                await _ingest_and_store_paper(db, job_id, arxiv_id)
            else:
                # Paper already exists, just link the job to it
                logger.info("Linking job to existing paper...")
                job = await queries.get_job(db, job_id)
                if job:
                    job.paper_id = arxiv_id
                    await db.commit()
                logger.info("Job linked successfully")

                # Update progress to match what would happen after ingestion
                await queries.update_job_status(
                    db, job_id,
                    current_step="Paper already processed",
                    progress=0.30
                )

            # Step 2: Use the unified graph pipeline for end-to-end processing
            logger.info("=" * 60)
            logger.info("STEP 2: Generating and Rendering with pipeline.graph")
            logger.info("=" * 60)

            await queries.update_job_status(
                db, job_id,
                current_step="Running unified pipeline (summarization, planning, coding, rendering)...",
                progress=0.40
            )

            from pipeline.graph import run_pipeline
            logger.info("Invoking visualization generation pipeline...")
            
            import functools
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                functools.partial(run_pipeline, input_url=arxiv_id),
            )
            
            scenes = result.get("scenes", [])
            logger.info(f"Generated {len(scenes)} visualization(s)")

            if not scenes:
                raise RuntimeError("Pipeline finished but generated 0 scenes.")

            # Record completed videos in database so the UI can stream them
            content_id = result.get("content_id") or arxiv_id
            
            for i, scene in enumerate(scenes):
                viz_id = f"{content_id}_{i}"
                
                await queries.upsert_visualization(
                    db,
                    viz_id=viz_id,
                    paper_id=content_id,
                    section_id=str(i+1),
                    concept=scene.get("title", ""),
                    storyboard={"description": scene.get("description", "")},
                    manim_code=scene.get("code", ""),
                    status="complete",
                    video_url=f"/api/video/{viz_id}"
                )

            # Mark job complete
            await queries.update_job_status(
                db, job_id, 
                status="completed", 
                current_step="Pipeline completed successfully", 
                progress=1.0,
                sections_completed=len(scenes),
                sections_total=len(scenes)
            )

        except Exception as e:
            logger.exception(f"✗ JOB FAILED: {job_id} for paper {arxiv_id}")
            logger.error(f"Error: {str(e)}")
            try:
                await db.rollback()
                await queries.update_job_status(
                    db, job_id,
                    status="failed",
                    error=str(e)
                )
            except Exception:
                logger.exception("Failed to update job status after error")
            raise


# ═══════════════════════════════════════════════════════════
# Universal Content Processing
# ═══════════════════════════════════════════════════════════

async def process_universal_job(
    job_id: str,
    content_id: str,
    content_type: str = "research_paper",
    video_mode: str = "standard",
    narration_style: str = "educational",
    tts_provider: str = "gtts",
    language: str = "en",
    source_url: str | None = None,
    source_text: str | None = None,
):
    """
    Universal job processing function — handles any content type.
    
    Pipeline:
    1. Ingest content (auto-dispatched to correct pipeline)
    2. Store content and sections in database
    3. Generate visualizations with ProcessingConfig
    4. Render all visualizations
    5. Generate TTS audio and subtitles
    6. Update job status to completed
    """
    logger.info("=" * 60)
    logger.info(f"STARTING UNIVERSAL JOB: {job_id}")
    logger.info(f"Content ID: {content_id}")
    logger.info(f"Type: {content_type}, Mode: {video_mode}, Narration: {narration_style}")
    logger.info("=" * 60)

    async with async_session_maker() as db:
        try:
            # Step 1: Ingest content
            logger.info("STEP 1: Ingesting content")
            logger.info("-" * 60)

            await queries.update_job_status(
                db, job_id,
                status="processing",
                current_step="Fetching and parsing content",
                progress=0.10,
            )

            # Check if already exists
            existing = await queries.paper_exists(db, content_id)
            if existing:
                logger.info(f"Content {content_id} already exists, skipping ingestion")
                await queries.update_job_paper_id(db, job_id, content_id)
                await queries.update_job_status(
                    db, job_id,
                    current_step="Content already processed",
                    progress=0.30,
                )
            else:
                logger.info(f"Content {content_id} not found, ingesting...")
                await _ingest_and_store_universal(db, job_id, content_id, content_type, source_url, source_text)

            # Step 2: Build StructuredContent and generate visualizations
            logger.info("=" * 60)
            logger.info("STEP 2: Generating visualizations")
            logger.info("=" * 60)

            # Generate using universal pipeline
            logger.info("Invoking unified visualization pipeline...")
            from pipeline.graph import run_pipeline
            
            import functools
            loop = asyncio.get_event_loop()
            
            # Build the pipeline call based on content type
            pipeline_kwargs = {}
            if source_url:
                pipeline_kwargs["input_url"] = source_url
            elif source_text:
                pipeline_kwargs["content"] = source_text
                pipeline_kwargs["content_id"] = content_id
                pipeline_kwargs["content_title"] = "Text Content"
                pipeline_kwargs["input_type"] = "text"
            else:
                pipeline_kwargs["input_url"] = content_id
            
            result = await loop.run_in_executor(
                None,
                functools.partial(run_pipeline, **pipeline_kwargs),
            )
            
            scenes = result.get("scenes", [])
            logger.info(f"Generated {len(scenes)} visualization(s)")

            if not scenes:
                raise RuntimeError("Unified pipeline finished but generated 0 scenes.")

            # Step 3: Store and map the locally rendered videos
            for i, scene in enumerate(scenes):
                viz_id = f"{content_id}_{i}"
                await queries.upsert_visualization(
                    db,
                    viz_id=viz_id,
                    paper_id=content_id,
                    section_id=str(i+1),
                    concept=scene.get("title", ""),
                    storyboard={"description": scene.get("description", "")},
                    manim_code=scene.get("code", ""),
                    status="complete",
                    video_url=f"/api/video/{viz_id}"
                )

            # Mark job complete
            await queries.update_job_status(
                db, job_id, 
                status="completed",
                current_step="Pipeline completed successfully", 
                progress=1.0,
                sections_completed=len(scenes),
                sections_total=len(scenes)
            )

            # Step 4: Generate TTS audio and subtitles (non-blocking, non-fatal)
            if narration_style != "none":
                try:
                    processing_config = ProcessingConfig(
                        video_mode=VideoMode(video_mode),
                        narration_style=NarrationStyle(narration_style),
                        tts_provider=TTSProvider(tts_provider),
                        language=language,
                    )
                    await _generate_tts_for_visualizations(
                        db, content_id, processing_config
                    )
                except Exception as tts_err:
                    logger.warning(f"TTS generation failed (non-fatal): {tts_err}")
            
        except Exception as e:
            logger.exception(f"✗ UNIVERSAL JOB FAILED: {job_id}")
            logger.error(f"Error: {str(e)}")
            try:
                await db.rollback()
                await queries.update_job_status(
                    db, job_id,
                    status="failed",
                    error=str(e)
                )
            except Exception:
                logger.exception("Failed to update job status after error")
            raise




# ═══════════════════════════════════════════════════════════
# TTS Audio Generation
# ═══════════════════════════════════════════════════════════

async def _generate_tts_for_visualizations(db, content_id: str, config: ProcessingConfig):
    """
    Generate TTS audio and subtitles for all visualizations of a content item.
    
    This runs after rendering and produces:
    - MP3 audio files for narration
    - SRT/VTT subtitle files
    """
    import re
    from tts import get_tts_engine, get_narration_style, estimate_narration_timing, generate_srt, generate_vtt
    
    logger.info("Generating TTS audio and subtitles...")
    
    engine = get_tts_engine(config.tts_provider.value)
    style = get_narration_style(config.narration_style.value)
    
    # Get all visualizations for this content
    db_paper = await queries.get_paper(db, content_id)
    if not db_paper or not db_paper.visualizations:
        logger.info("No visualizations found for TTS generation")
        return
    
    for viz in db_paper.visualizations:
        if not viz.manim_code:
            continue
        
        # Extract narration lines from the manim code
        narrations = re.findall(
            r'with\s+self\.voiceover\s*\(\s*text\s*=\s*"([^"]+)"\s*\)\s+as\s+tracker\s*:',
            viz.manim_code,
        )
        if not narrations:
            narrations = re.findall(
                r'with\s+self\.voiceover\s*\(\s*"([^"]+)"\s*\)\s+as\s+tracker\s*:',
                viz.manim_code,
            )
        
        if not narrations:
            logger.info(f"No narration found in {viz.id}, skipping TTS")
            continue
        
        narration_text = " ".join(narrations)
        logger.info(f"Generating TTS for {viz.id}: {len(narrations)} segments, {len(narration_text)} chars")
        
        try:
            # Synthesize audio
            audio_bytes = await engine.synthesize(
                text=narration_text,
                voice=config.voice_name,
                language=config.language,
                speed=style["speed"],
            )
            
            # Save audio file
            from pathlib import Path
            audio_dir = Path("output") / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = audio_dir / f"{viz.id}.mp3"
            audio_path.write_bytes(audio_bytes)
            audio_url = f"/output/audio/{viz.id}.mp3"
            
            # Generate subtitles
            if config.generate_subtitles:
                segments = estimate_narration_timing(
                    narrations,
                    words_per_minute=150 / style["speed"],
                    pause_between=style["pause_between_scenes"],
                )
                
                srt_content = generate_srt(segments)
                vtt_content = generate_vtt(segments)
                
                subtitle_dir = Path("output") / "subtitles"
                subtitle_dir.mkdir(parents=True, exist_ok=True)
                
                srt_path = subtitle_dir / f"{viz.id}.srt"
                vtt_path = subtitle_dir / f"{viz.id}.vtt"
                srt_path.write_text(srt_content, encoding="utf-8")
                vtt_path.write_text(vtt_content, encoding="utf-8")
                subtitle_url = f"/output/subtitles/{viz.id}.vtt"
            else:
                subtitle_url = None
            
            # Update visualization record with audio and subtitle URLs
            viz.audio_url = audio_url
            viz.subtitle_url = subtitle_url
            viz.narration_script = narrations  # Store as list of segments (JSON column)
            await db.commit()
            
            logger.info(f"✓ TTS generated for {viz.id}: audio={audio_url}")
            
        except Exception as e:
            logger.error(f"✗ TTS failed for {viz.id}: {e}")
            # Non-fatal — video still works without audio


# ═══════════════════════════════════════════════════════════
# Ingestion Helpers
# ═══════════════════════════════════════════════════════════

def _sanitize_for_json(obj):
    """Recursively convert datetime/date/enum objects to JSON-safe types."""
    import enum
    from datetime import date, datetime as dt

    if isinstance(obj, dt):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    return obj


async def _ingest_and_store_paper(db, job_id: str, arxiv_id: str):
    """
    Ingest a real paper from arXiv and store it in the database.
    """
    from ingestion import ingest_paper

    await queries.update_job_status(
        db, job_id,
        current_step="Fetching paper metadata from arXiv",
        progress=0.15
    )

    structured_paper = await ingest_paper(arxiv_id)
    meta = structured_paper.meta

    await queries.update_job_status(
        db, job_id,
        current_step="Parsing sections and content",
        progress=0.30
    )

    # Store paper record
    await queries.create_paper(
        db,
        arxiv_id=meta.arxiv_id,
        title=meta.title,
        authors=meta.authors,
        abstract=meta.abstract,
        pdf_url=meta.pdf_url,
        html_url=meta.html_url,
    )

    # Now that the paper exists, link the job to it
    await queries.update_job_paper_id(db, job_id, meta.arxiv_id)

    # Store sections using savepoints so one failure doesn't roll back the paper
    stored_count = 0
    seen_ids = set()
    for i, section in enumerate(structured_paper.sections):
        # Ensure unique section IDs
        sid = section.id
        if sid in seen_ids:
            sid = f"{sid}-{i}"
        seen_ids.add(sid)

        try:
            async with db.begin_nested():
                equations_json = [eq.latex for eq in section.equations]
                figures_json = [fig.model_dump() for fig in section.figures]
                tables_json = [tbl.model_dump() for tbl in section.tables]

                section_obj = Section(
                    id=sid,
                    paper_id=meta.arxiv_id,
                    title=section.title,
                    content=section.content,
                    summary=section.summary or None,
                    level=section.level,
                    order_index=i,
                    equations=equations_json,
                    figures=figures_json,
                    tables=tables_json,
                )
                db.add(section_obj)
            stored_count += 1
        except Exception as e:
            logger.warning(f"Failed to store section '{section.title}': {e}")

    await db.commit()

    logger.info(f"Stored paper '{meta.title}' with {stored_count}/{len(structured_paper.sections)} sections")


async def _ingest_and_store_universal(db, job_id: str, content_id: str, content_type: str, source_url: str | None = None, source_text: str | None = None):
    """
    Ingest any content type and store it in the database.
    """
    from ingestion import ingest_github_repo
    from ingestion.content_fetcher import ingest_technical_content

    await queries.update_job_status(
        db, job_id,
        current_step=f"Ingesting {content_type} content",
        progress=0.15,
    )

    if content_type == "github_repo":
        # content_id is "gh:owner/repo" — strip prefix for URL
        repo_path = content_id.replace("gh:", "", 1) if content_id.startswith("gh:") else content_id
        url = f"https://github.com/{repo_path}"
        structured = await ingest_github_repo(url)
    elif content_type == "technical_content":
        # Use original URL or text (content_id is a hash, not the actual URL)
        structured = await ingest_technical_content(url=source_url, text=source_text)
    else:
        # Fallback: treat as arXiv paper through the universal router
        from ingestion import ingest_content
        structured = await ingest_content(url=content_id, arxiv_id=content_id)

    await queries.update_job_status(
        db, job_id,
        current_step="Storing content and sections",
        progress=0.30,
    )

    # Store content record
    raw_meta = structured.meta.model_dump() if hasattr(structured.meta, "model_dump") else {}
    await queries.create_paper(
        db,
        paper_id=content_id,
        title=structured.meta.title,
        authors=[],
        abstract=structured.meta.description,
        content_type=content_type,
        source_url=structured.meta.source_url,
        extra_meta=_sanitize_for_json(raw_meta),
    )

    # Link job to content
    await queries.update_job_paper_id(db, job_id, content_id)

    # Store sections
    stored_count = 0
    seen_ids = set()
    for i, section in enumerate(structured.sections):
        sid = section.id
        if sid in seen_ids:
            sid = f"{sid}-{i}"
        seen_ids.add(sid)

        try:
            async with db.begin_nested():
                equations_json = [eq.latex for eq in section.equations] if section.equations else []
                
                section_obj = Section(
                    id=sid,
                    paper_id=content_id,
                    title=section.title,
                    content=section.content,
                    summary=section.summary or None,
                    level=section.level,
                    order_index=i,
                    equations=equations_json,
                    figures=[],
                    tables=[],
                )
                db.add(section_obj)
            stored_count += 1
        except Exception as e:
            logger.warning(f"Failed to store section '{section.title}': {e}")

    await db.commit()
    logger.info(f"Stored content '{structured.meta.title}' with {stored_count}/{len(structured.sections)} sections")


# ═══════════════════════════════════════════════════════════
# DB → Model Converters
# ═══════════════════════════════════════════════════════════

def _build_structured_paper_from_db(db_paper, db_sections: list[Section]) -> StructuredPaper:
    """Reconstruct StructuredPaper from database rows for legacy pipeline input."""
    meta = ArxivPaperMeta(
        arxiv_id=db_paper.id,
        title=db_paper.title,
        authors=db_paper.authors or [],
        abstract=db_paper.abstract or "",
        pdf_url=db_paper.pdf_url or f"https://arxiv.org/pdf/{db_paper.id}",
        html_url=db_paper.html_url,
    )

    sections: list[PaperSection] = []
    for db_section in db_sections:
        equations = [
            Equation(latex=eq if isinstance(eq, str) else str(eq), context="")
            for eq in (db_section.equations or [])
        ]
        figures = [
            Figure(
                id=fig.get("id", f"{db_section.id}-figure-{idx+1}"),
                caption=fig.get("caption", ""),
                page=fig.get("page"),
            )
            for idx, fig in enumerate(db_section.figures or [])
            if isinstance(fig, dict)
        ]
        tables = [
            Table(
                id=tbl.get("id", f"{db_section.id}-table-{idx+1}"),
                caption=tbl.get("caption", ""),
                headers=tbl.get("headers", []),
                rows=tbl.get("rows", []),
            )
            for idx, tbl in enumerate(db_section.tables or [])
            if isinstance(tbl, dict)
        ]

        sections.append(
            PaperSection(
                id=db_section.id,
                title=db_section.title,
                level=db_section.level,
                content=db_section.content or "",
                equations=equations,
                figures=figures,
                tables=tables,
            )
        )

    return StructuredPaper(meta=meta, sections=sections)


def _build_structured_content_from_db(
    db_paper, db_sections: list[Section], content_type: str
) -> StructuredContent:
    """Build StructuredContent from database rows for universal pipeline input."""
    meta = ContentMeta(
        content_type=ContentType(content_type),
        content_id=db_paper.id,
        title=db_paper.title,
        description=db_paper.abstract or "",
        source_url=getattr(db_paper, "source_url", None),
    )

    sections: list[PaperSection] = []
    for db_section in db_sections:
        equations = [
            Equation(latex=eq if isinstance(eq, str) else str(eq), context="")
            for eq in (db_section.equations or [])
        ]

        sections.append(
            PaperSection(
                id=db_section.id,
                title=db_section.title,
                level=db_section.level,
                content=db_section.content or "",
                summary=db_section.summary or "",
                equations=equations,
                figures=[],
                tables=[],
            )
        )

    return StructuredContent(meta=meta, sections=sections)
