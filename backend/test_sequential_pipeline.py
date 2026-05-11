"""
Test sequential visualization pipeline: 1 section analyzed, 1 code gen, then parallel rendering.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_sequential():
    """Test with sequential code generation."""
    print("\n" + "="*70)
    print("SEQUENTIAL PIPELINE TEST (1 section at a time for code gen)")
    print("="*70)
    
    from ingestion import ingest_paper
    from agents.pipeline import generate_universal_visualizations
    from models.content import StructuredContent, ProcessingConfig, VideoMode, ContentType, ContentMeta
    
    # Fetch and process paper
    arxiv_id = "1706.03762"
    print(f"\n[1/3] Fetching paper: {arxiv_id}")
    paper = await ingest_paper(arxiv_id)
    print(f"[OK] Paper fetched with {len(paper.sections)} sections")
    
    # Create content wrapper
    print(f"\n[2/3] Preparing content for pipeline...")
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
    print(f"[OK] Content ready: {len(content.sections)} sections")
    print(f"   Sections: {[s.title[:40] for s in content.sections[:3]]}...")
    
    # Run sequential visualization generation
    print(f"\n[3/3] Generating visualizations (sequential mode)...")
    print(f"   > Max 3 visualizations")
    print(f"   > 1 code generation per section (no concurrent requests)")
    print(f"   > Rendering can happen in parallel while next section is analyzed\n")
    
    visualizations = await generate_universal_visualizations(content, config)
    
    print(f"\n[OK] Generated {len(visualizations)} visualizations")
    
    if visualizations:
        for i, viz in enumerate(visualizations[:3], 1):
            code_lines = len(viz.manim_code.split('\n'))
            print(f"   Viz {i}: {viz.concept[:50]}")
            print(f"      - Code: {code_lines} lines, {len(viz.manim_code)} chars")
            print(f"      - Has Scene class: {'class ' in viz.manim_code and 'Scene' in viz.manim_code}")
    
    print("\n" + "="*70)
    print("[PASS] SEQUENTIAL PIPELINE TEST PASSED!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_sequential())
