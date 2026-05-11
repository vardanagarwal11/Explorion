#!/usr/bin/env python3
"""
Quick pipeline verification test with real paper
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def quick_test():
    """Quick test of pipeline stages."""
    
    print("\n" + "="*70)
    print("QUICK PIPELINE VERIFICATION TEST")
    print("="*70)
    
    # Test 1: Import check
    print("\n[1/4] Checking imports...")
    try:
        from ingestion import ingest_paper
        from agents.pipeline import generate_universal_visualizations
        from models.content import StructuredContent, ProcessingConfig, VideoMode
        print("[OK] All imports successful")
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False
    
    # Test 2: Fetch and parse paper (SKIP FORMATTER - it's too slow)
    print("\n[2/4] Fetching paper from arXiv (skipping formatter)...")
    try:
        from ingestion.arxiv_fetcher import fetch_paper_meta, download_pdf
        from ingestion.pdf_parser import parse_pdf
        from ingestion.section_extractor import extract_sections
        
        arxiv_id = "1706.03762"  # Attention is All You Need
        print(f"   Fetching: {arxiv_id}")
        meta = await fetch_paper_meta(arxiv_id)
        pdf_bytes = await download_pdf(meta.pdf_url)
        pdf_content = parse_pdf(pdf_bytes)
        sections = extract_sections(pdf_content, meta)
        
        # Create paper structure
        paper = type('Paper', (), {
            'meta': meta,
            'sections': sections
        })()
        
        print(f"[OK] Paper fetched: {meta.title[:60]}...")
        print(f"   Sections (raw, no formatting): {len(sections)}")
    except Exception as e:
        print(f"[ERROR] Paper fetch failed: {e}")
        return False
    
    # Test 3: Convert and analyze
    print("\n[3/4] Processing through pipeline...")
    try:
        from models.content import ContentType, ContentMeta
        
        # Create proper ContentMeta wrapper
        meta = ContentMeta(
            content_type=ContentType.RESEARCH_PAPER,
            content_id=paper.meta.arxiv_id,
            title=paper.meta.title,
            description=paper.meta.abstract or "",
            source_url=f"https://arxiv.org/abs/{paper.meta.arxiv_id}",
            paper_meta=paper.meta,
        )
        
        content = StructuredContent(meta=meta, sections=paper.sections)
        config = ProcessingConfig(video_mode=VideoMode.STANDARD)
        print(f"   Content type: {content.meta.content_type.value}")
        print(f"   Sections ready: {len(content.sections)}")
        print("[OK] Content prepared")
    except Exception as e:
        print(f"[ERROR] Content preparation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Generate visualizations
    print("\n[4/4] Generating visualizations...")
    try:
        print("   Starting generation...")
        visualizations = []
        async for viz in generate_universal_visualizations(content, config):
            visualizations.append(viz)
        print(f"[OK] Generated {len(visualizations)} visualizations")
        
        if visualizations:
            for i, viz in enumerate(visualizations[:3], 1):  # Show first 3
                print(f"\n   Visualization {i}: {viz.concept[:50]}")
                print(f"   • Code size: {len(viz.manim_code)} chars")
                print(f"   • Has Scene class: {'class ' in viz.manim_code and 'Scene' in viz.manim_code}")
                print(f"   • Has construct method: {'def construct' in viz.manim_code}")
                print(f"   • Has animations: {'self.play' in viz.manim_code}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    print("\n" + "="*70)
    if success:
        print("[PASS] PIPELINE TEST PASSED!")
    else:
        print("[FAIL] PIPELINE TEST FAILED")
    print("="*70 + "\n")
    sys.exit(0 if success else 1)
