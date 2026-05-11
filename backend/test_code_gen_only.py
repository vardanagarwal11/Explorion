"""
Test sequential Manim code generation (GLM) without analysis step.
This validates the core bottleneck: can GLM generate code sequentially?
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_code_generation():
    """Test sequential code generation with GLM."""
    print("\n" + "="*70)
    print("SEQUENTIAL CODE GENERATION TEST (GLM only)")
    print("="*70)
    
    from agents.manim_generator import ManimGenerator
    from models.generation import VisualizationPlan, Scene, VisualizationType
    
    # Create a simple test plan (no NIM involved)
    print("\n[STEP 1] Creating test visualization plans...")
    
    test_concepts = [
        ("Attention Mechanism", "How transformer attention works with multiple heads"),
        ("Encoder Architecture", "Stack of self-attention and feed-forward layers"),
        ("Positional Encoding", "How positions are encoded in sequence"),
    ]
    
    generator = ManimGenerator()
    
    for idx, (concept, description) in enumerate(test_concepts, 1):
        print(f"\n  [{idx}] {concept}")
        print(f"      Generating Manim code...")
        
        try:
            # Create a minimal plan
            plan = VisualizationPlan(
                concept_name=concept,
                visualization_type=VisualizationType.ARCHITECTURE,
                duration_seconds=30,
                scenes=[
                    Scene(
                        order=1,
                        description=f"Show {description.lower()}",
                        duration_seconds=10,
                        transitions="fade_in",
                        elements=[],
                    )
                ],
                narration_points=[description],
            )
            
            # Generate code with LONGER timeout (Modal is slow)
            print(f"      [WAITING] Sending to Modal (this takes 30-60 seconds)...")
            code_result = await asyncio.wait_for(
                generator.run(
                    plan=plan,
                    voiceover_enabled=False,
                    tts_service="gtts",
                    voice_name="",
                    narration_style="friendly_tutor",
                    target_duration_seconds=(30, 45),
                ),
                timeout=90.0  # Modal can take a while
            )
            
            print(f"      [OK] Generated {len(code_result.code)} chars of code")
            print(f"      Sample: {code_result.code[:80]}...")
            
            # WAIT before next request to avoid rate limit
            if idx < len(test_concepts):
                print(f"      [WAIT] Waiting 10 seconds before next request...")
                await asyncio.sleep(10)
            
        except asyncio.TimeoutError:
            print(f"      [TIMEOUT] Code generation took >90 seconds")
        except Exception as e:
            print(f"      [ERROR] {type(e).__name__}: {e}")
    
    print("\n" + "="*70)
    print("[DONE] Code generation test complete")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_code_generation())
