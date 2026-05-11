#!/usr/bin/env python3
"""
Simple pipeline test - skip formatting, go straight to visualization
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def simple_test():
    """Simple test of pipeline without section formatting."""
    
    print("\n" + "="*70)
    print("SIMPLE PIPELINE TEST (NO FORMATTING)")
    print("="*70)
    
    # Test 1: Import check
    print("\n[1/3] Checking imports...")
    try:
        from ingestion.arxiv_fetcher import fetch_paper_meta
        from ingestion.pdf_parser import parse_pdf
        from ingestion.section_extractor import extract_sections
        from agents.pipeline import generate_universal_visualizations
        from models.content import StructuredContent, ProcessingConfig, VideoMode, ContentType, ContentMeta
        print("[OK] All imports successful")
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Fetch and parse paper (WITHOUT formatting)
    print("\n[2/3] Fetching paper from arXiv...")
    try:
        from ingestion.arxiv_fetcher import download_pdf
        
        arxiv_id = "1706.03762"  # Attention is All You Need
        print(f"   Fetching metadata: {arxiv_id}")
        meta = await fetch_paper_meta(arxiv_id)
        print(f"[OK] Fetched: {meta.title[:60]}")
        
        print(f"   Downloading PDF...")
        pdf_bytes = await download_pdf(meta.pdf_url)
        print(f"[OK] Downloaded: {len(pdf_bytes)} bytes")
        
        print(f"   Parsing PDF...")
        pdf_content = parse_pdf(pdf_bytes)
        print(f"[OK] PDF parsed: {len(pdf_content.raw_text)} chars")
        
        print(f"   Extracting sections...")
        sections = extract_sections(pdf_content, meta)
        print(f"[OK] Extracted {len(sections)} sections (NO FORMATTING APPLIED)")
        
    except Exception as e:
        print(f"❌ Paper fetch/parse failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Create content and generate visualizations
    print("\n[3/3] Generating visualizations...")
    try:
        # Create proper ContentMeta wrapper
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
        
        print(f"   Content ready: {len(content.sections)} sections")
        print("   Starting visualization generation...")
        
        visualizations = await generate_universal_visualizations(content, config)
        print(f"✅ Generated {len(visualizations)} visualizations")
        
        if visualizations:
            for i, viz in enumerate(visualizations[:2], 1):  # Show first 2
                print(f"\n   Visualization {i}: {viz.concept[:50]}")
                print(f"   • Code size: {len(viz.manim_code)} chars")
                print(f"   • Has Scene class: {'class ' in viz.manim_code and 'Scene' in viz.manim_code}")
                print(f"   • Has construct method: {'def construct' in viz.manim_code}")
        
        return True
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    print("\n" + "="*70)
    if success:
        print("✅ SIMPLE PIPELINE TEST PASSED!")
    else:
        print("❌ SIMPLE PIPELINE TEST FAILED")
    print("="*70 + "\n")
    sys.exit(0 if success else 1)
