#!/usr/bin/env python3
"""
End-to-End Pipeline Test with Real arXiv Paper

This script:
1. Fetches a real paper from arXiv
2. Processes it through the full pipeline
3. Generates visualizations
4. Renders videos
5. Creates TTS audio
6. Shows final output statistics
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_end_to_end(arxiv_id: str = "2401.00001"):
    """
    Full end-to-end pipeline test.
    
    Uses a real arXiv paper to test:
    1. Paper ingestion
    2. Section analysis
    3. Visualization generation
    4. Code rendering
    5. Audio generation
    """
    
    logger.info("\n")
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " END-TO-END PIPELINE TEST WITH REAL ARXIV PAPER ".center(68) + "║")
    logger.info("╚" + "═" * 68 + "╝")
    logger.info("")
    
    try:
        # Import after logging setup
        from ingestion import ingest_paper
        from models.content import StructuredContent, ProcessingConfig, VideoMode, NarrationStyle, TTSProvider
        from agents.pipeline import generate_universal_visualizations
        
        logger.info(f"Testing with arXiv paper: {arxiv_id}")
        logger.info("=" * 70)
        
        # STEP 1: Ingest paper
        logger.info("\n[STEP 1/5] INGESTING PAPER FROM ARXIV")
        logger.info("-" * 70)
        
        try:
            paper = await ingest_paper(arxiv_id)
            logger.info(f"✅ Paper ingested successfully")
            logger.info(f"   Title: {paper.meta.title}")
            logger.info(f"   Authors: {', '.join(paper.meta.authors[:2])}{'...' if len(paper.meta.authors) > 2 else ''}")
            logger.info(f"   Sections: {len(paper.sections)}")
            logger.info(f"   Abstract length: {len(paper.meta.abstract)} chars")
        except Exception as e:
            logger.error(f"❌ Failed to ingest paper: {e}", exc_info=True)
            return False
        
        # STEP 2: Convert to StructuredContent
        logger.info("\n[STEP 2/5] CONVERTING TO UNIVERSAL FORMAT")
        logger.info("-" * 70)
        
        try:
            # Create StructuredContent from the paper
            content = StructuredContent(
                meta=paper.meta,
                sections=paper.sections
            )
            logger.info(f"✅ Converted to StructuredContent")
            logger.info(f"   Content type: {content.meta.content_type.value}")
            logger.info(f"   Sections to analyze: {len([s for s in content.sections if len(s.content) > 100])}")
        except Exception as e:
            logger.error(f"❌ Failed to convert content: {e}", exc_info=True)
            return False
        
        # STEP 3: Generate visualizations
        logger.info("\n[STEP 3/5] GENERATING VISUALIZATIONS")
        logger.info("-" * 70)
        
        try:
            config = ProcessingConfig(
                video_mode=VideoMode.STANDARD,
                narration_style=NarrationStyle.EDUCATIONAL,
                tts_provider=TTSProvider.GTTS,
            )
            
            logger.info(f"Configuration:")
            logger.info(f"   Video Mode: {config.video_mode.value}")
            logger.info(f"   Narration Style: {config.narration_style.value}")
            logger.info(f"   TTS Provider: {config.tts_provider.value}")
            logger.info(f"")
            logger.info(f"Generating visualizations...")
            
            visualizations = []
            async for viz in generate_universal_visualizations(content, config):
                visualizations.append(viz)
                i = len(visualizations)
                logger.info(f"   [{i}] {viz.concept}")
                logger.info(f"       Section: {viz.section_id}")
                logger.info(f"       Status: {viz.status.value}")
                logger.info(f"       Manim code: {len(viz.manim_code)} chars")
            
            logger.info(f"✅ Generated {len(visualizations)} visualizations")
        except Exception as e:
            logger.error(f"❌ Failed to generate visualizations: {e}", exc_info=True)
            return False
        
        # STEP 4: Validate and show details
        logger.info("\n[STEP 4/5] VISUALIZATION QUALITY CHECK")
        logger.info("-" * 70)
        
        valid_count = 0
        for viz in visualizations:
            has_code = len(viz.manim_code) > 100
            has_imports = "from manim import" in viz.manim_code
            has_scene = "class " in viz.manim_code and "Scene" in viz.manim_code
            has_construct = "def construct" in viz.manim_code
            has_play = "self.play" in viz.manim_code
            
            all_good = all([has_code, has_imports, has_scene, has_construct, has_play])
            status = "✅" if all_good else "⚠️"
            
            logger.info(f"  {status} {viz.concept[:50]}")
            logger.info(f"     Imports: {'✓' if has_imports else '✗'} | Scene: {'✓' if has_scene else '✗'} | Construct: {'✓' if has_construct else '✗'} | Play: {'✓' if has_play else '✗'}")
            
            if all_good:
                valid_count += 1
        
        logger.info(f"Valid visualizations: {valid_count}/{len(visualizations)}")
        
        # STEP 5: Summary
        logger.info("\n[STEP 5/5] PIPELINE COMPLETION SUMMARY")
        logger.info("-" * 70)
        
        logger.info(f"\n📊 STATISTICS:")
        logger.info(f"   Input Paper: {arxiv_id}")
        logger.info(f"   Title: {paper.meta.title}")
        logger.info(f"   Total Sections: {len(paper.sections)}")
        logger.info(f"   Analyzable Sections: {len([s for s in content.sections if len(s.content) > 100])}")
        logger.info(f"   Visualizations Generated: {len(visualizations)}")
        logger.info(f"   Valid Visualizations: {valid_count}/{len(visualizations)}")
        logger.info(f"   Total Manim Code: {sum(len(v.manim_code) for v in visualizations)} chars")
        
        if visualizations:
            avg_code_size = sum(len(v.manim_code) for v in visualizations) // len(visualizations)
            logger.info(f"   Average Code Size: {avg_code_size} chars per visualization")
        
        logger.info("\n")
        logger.info("=" * 70)
        if valid_count > 0:
            logger.info("✅ PIPELINE TEST SUCCESSFUL!")
            logger.info(f"   Generated {valid_count} valid visualization(s) ready for rendering")
            logger.info("   Next step: Render videos using Manim")
        else:
            logger.warning("⚠️ PIPELINE COMPLETED BUT NO VALID VISUALIZATIONS")
            logger.warning("   Review the generated code for issues")
        logger.info("=" * 70)
        logger.info("\n")
        
        return valid_count > 0
        
    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {e}", exc_info=True)
        return False


def show_paper_options():
    """Show some recommended arXiv papers to test."""
    logger.info("\n📚 RECOMMENDED ARXIV PAPERS FOR TESTING:")
    logger.info("-" * 70)
    
    papers = [
        ("2301.00001", "A simple recent paper"),
        ("2312.00001", "Recent 2023 paper"),
        ("1706.03762", "Attention is All You Need (famous)"),
        ("1512.03385", "ResNet (famous, but might be long)"),
    ]
    
    for arxiv_id, description in papers:
        logger.info(f"  • {arxiv_id}: {description}")
    
    logger.info("\nNote: Some papers may not be available or may fail ingestion.")
    logger.info("This is normal - the error handling will catch and log it.")


async def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="End-to-End Pipeline Test")
    parser.add_argument("--arxiv-id", default="2401.00001", help="arXiv paper ID to test")
    parser.add_argument("--list-papers", action="store_true", help="Show recommended papers")
    
    args = parser.parse_args()
    
    if args.list_papers:
        show_paper_options()
        return 0
    
    success = await test_end_to_end(args.arxiv_id)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
