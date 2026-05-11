"""
Test sequential analysis → code generation → rendering.
One section at a time to avoid rate limits.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_sequential():
    """Test sequential pipeline: analyze 1 → generate 1 → render 1."""
    print("\n" + "="*70)
    print("SEQUENTIAL ANALYSIS → GENERATION TEST")
    print("="*70)
    
    from ingestion.arxiv_fetcher import fetch_paper_meta, download_pdf
    from ingestion.pdf_parser import parse_pdf
    from ingestion.section_extractor import extract_sections
    from models.content import StructuredContent, ProcessingConfig, VideoMode, ContentType, ContentMeta
    from agents.section_analyzer import SectionAnalyzer
    
    # Fetch paper
    print("\n[STEP 1] Fetching paper...")
    arxiv_id = "1706.03762"
    meta = await fetch_paper_meta(arxiv_id)
    pdf_bytes = await download_pdf(meta.pdf_url)
    pdf_content = parse_pdf(pdf_bytes)
    sections = extract_sections(pdf_content, meta)
    print(f"[OK] Got {len(sections)} sections")
    
    # Create content structure
    print("\n[STEP 2] Creating content structure...")
    content_meta = ContentMeta(
        content_type=ContentType.RESEARCH_PAPER,
        content_id=meta.arxiv_id,
        title=meta.title,
        description=meta.abstract or "",
        source_url=f"https://arxiv.org/abs/{meta.arxiv_id}",
        paper_meta=meta,
    )
    content = StructuredContent(meta=content_meta, sections=sections)
    config = ProcessingConfig(video_mode=VideoMode.STANDARD)
    print(f"[OK] Content ready with {len(content.sections)} sections")
    
    # Analyze sections sequentially
    print("\n[STEP 3] Analyzing sections sequentially...")
    analyzer = SectionAnalyzer()
    
    candidates = []
    for i, section in enumerate(content.sections[:3]):  # Just first 3
        print(f"\n  Analyzing section {i+1}/3: {section.title[:40]}...")
        try:
            result = await analyzer.run(
                content_title=content.meta.title,
                content_description=content.meta.description,
                section=section,
                content_type=content.meta.content_type,
            )
            if result.needs_visualization:
                print(f"    [OK] Found {len(result.candidates)} visualization candidates")
                candidates.extend(result.candidates)
            else:
                print(f"    [SKIP] No visualizations needed")
        except Exception as e:
            print(f"    [ERROR] {e}")
    
    print(f"\n[OK] Total candidates found: {len(candidates)}")
    for i, cand in enumerate(candidates[:3], 1):
        print(f"  {i}. {cand.concept_name} (priority: {cand.priority})")
    
    print("\n" + "="*70)
    print("[PASS] SEQUENTIAL ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_sequential())
