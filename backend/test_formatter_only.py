"""
Test just the formatter pipeline without analysis/generation.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_formatter():
    """Test formatter in isolation."""
    print("\n" + "="*70)
    print("FORMATTER-ONLY TEST")
    print("="*70)
    
    from ingestion.arxiv_fetcher import fetch_paper_meta, download_pdf
    from ingestion.pdf_parser import parse_pdf
    from ingestion.section_extractor import extract_sections
    from ingestion.section_formatter import format_sections
    
    # Fetch paper
    arxiv_id = "1706.03762"
    print(f"\n[1/4] Fetching paper: {arxiv_id}")
    meta = await fetch_paper_meta(arxiv_id)
    print(f"[OK] Fetched: {meta.title}")
    
    # Download and parse
    print(f"\n[2/4] Downloading PDF...")
    pdf_bytes = await download_pdf(meta.pdf_url)
    print(f"[OK] Downloaded: {len(pdf_bytes)} bytes")
    
    print(f"\n[3/4] Parsing PDF...")
    pdf_content = parse_pdf(pdf_bytes)
    print(f"[OK] Parsed: {len(pdf_content.raw_text)} chars")
    
    # Extract sections
    print(f"\n[4/4] Extracting sections...")
    sections = extract_sections(pdf_content, meta)
    print(f"[OK] Extracted: {len(sections)} sections")
    
    # Format sections
    print(f"\n[5/5] Running formatter (summarize + organize)...")
    formatted = await format_sections(sections, meta)
    print(f"[OK] Formatted: {len(formatted)} sections")
    
    for section in formatted[:3]:
        print(f"  - {section.title}: {len(section.content)} chars")
    
    print("\n" + "="*70)
    print("[PASS] FORMATTER TEST PASSED!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_formatter())
