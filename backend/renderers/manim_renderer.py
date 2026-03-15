"""
Manim renderer for the local pipeline.

Writes generated Manim Python code to a temp file, invokes the Manim CLI, and
returns the path of the rendered MP4.
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# Output directory for rendered videos (served by /api/video via LocalStorageBackend)
OUTPUT_DIR = Path(__file__).parent.parent / "media" / "videos"
MANIM_QUALITY_FLAG = os.getenv("MANIM_QUALITY_FLAG", "-ql")  # default low quality for fast rendering


def _get_manim_exe() -> str:
    """Prefer the manim binary inside the active venv."""
    env_val = os.getenv("MANIM_EXECUTABLE")
    if env_val and Path(env_val).exists():
        return env_val

    scripts = Path(sys.executable).parent  # Scripts/ on Windows, bin/ on Unix
    for candidate in (scripts / "manim.exe", scripts / "manim"):
        if candidate.exists():
            return str(candidate)
    return "manim"


def _extract_scene_class(code: str) -> str:
    """Return the Scene class name from Manim code (defaults to MainScene)."""
    m = re.search(r"class\s+(\w+)\s*\(\s*\w*Scene\s*\)", code)
    return m.group(1) if m else "MainScene"


def _fallback_scene_code(
    scene_id: str,
    scene_title: str = "",
    scene_description: str = "",
) -> str:
    """Safe Text-only scene used if generated code fails to render. Uses actual scene title/description when provided."""
    def _safe(s: str, max_len: int = 80) -> str:
        return s.strip()[:max_len].replace("\\", "\\\\").replace('"', "'").replace("\n", " ")

    safe_id = _safe(scene_id, 40) or "Scene"
    title_text = _safe(scene_title or "Visualization", 60)
    desc_text = _safe(scene_description or "Rendering failed; this is a fallback placeholder.", 120)
    return f'''\
from manim import *

class MainScene(Scene):
    def construct(self):
        bg = Rectangle(width=16, height=9, fill_color="#0f0f23", fill_opacity=1, stroke_width=0)
        self.add(bg)

        title = Text("{title_text}", font_size=40, color="#E0E0FF", weight=BOLD)
        self.play(Write(title), run_time=1.5)
        self.wait(2)

        subtitle = Text("Visualizing: {safe_id}", font_size=22, color="#B0BEC5")
        subtitle.next_to(title, DOWN, buff=0.3)
        self.play(FadeIn(subtitle))
        self.wait(2)

        card = RoundedRectangle(
            width=12, height=2.2, corner_radius=0.2,
            fill_color="#1a1a3e", fill_opacity=0.9,
            stroke_color="#6C63FF", stroke_width=2,
        )
        desc = Text("{desc_text}", font_size=20, color="#B0BEC5")
        content = VGroup(card, desc)
        content.to_edge(DOWN, buff=0.8)
        self.play(FadeIn(content, shift=UP * 0.3))
        self.wait(4)
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        self.wait(1)
'''


def _find_output_mp4(media_dir: Path, stem: str, scene_name: str) -> Path | None:
    candidates = list(media_dir.glob(f"videos/{stem}/**/{scene_name}.mp4"))
    if not candidates:
        candidates = list(media_dir.rglob("*.mp4"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def render_manim(
    code: str,
    scene_id: str | None = None,
    scene_title: str = "",
    scene_description: str = "",
) -> str:
    """
    Render a Manim Python script and return the path to the output MP4.

    Args:
        code:             Complete Manim Python source code.
        scene_id:         Optional identifier used for the output filename.
        scene_title:      Used in fallback scene if primary render fails.
        scene_description: Used in fallback scene if primary render fails.

    Returns:
        Absolute path string to the rendered MP4 file.

    Raises:
        RuntimeError: if Manim exits with a non-zero code.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scene_id = scene_id or str(uuid.uuid4())[:8]
    scene_name = _extract_scene_class(code)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix=f"scene_{scene_id}_", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        script_path = f.name

    try:
        manim = _get_manim_exe()
        cmd = [manim, MANIM_QUALITY_FLAG, "--media_dir", str(OUTPUT_DIR), script_path, scene_name]
        logger.info("Rendering Manim: %s", " ".join(cmd))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=600,
        )

        if result.returncode != 0:
            logger.warning(
                "Primary render failed; retrying with safe fallback scene (title=%r)",
                (scene_title or scene_id)[:50],
            )
            logger.error("Manim stderr:\n%s", result.stderr[-2000:])

            fallback_code = _fallback_scene_code(scene_id, scene_title, scene_description)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", prefix=f"fallback_{scene_id}_", delete=False, encoding="utf-8"
            ) as ff:
                ff.write(fallback_code)
                fallback_script = ff.name

            try:
                fb_cmd = [manim, MANIM_QUALITY_FLAG, "--media_dir", str(OUTPUT_DIR), fallback_script, "MainScene"]
                fb_result = subprocess.run(
                    fb_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=300,
                )
                if fb_result.returncode != 0:
                    raise RuntimeError(
                        "Manim rendering failed and fallback also failed:\n"
                        f"Primary: {result.stderr[-400:]}\n"
                        f"Fallback: {fb_result.stderr[-400:]}"
                    )
                script_path = fallback_script
                scene_name = "MainScene"
            finally:
                try:
                    os.unlink(fallback_script)
                except OSError:
                    pass

        # Manim writes to <media_dir>/videos/<stem>/480p15/<SceneName>.mp4
        stem = Path(script_path).stem
        latest = _find_output_mp4(OUTPUT_DIR, stem, scene_name)
        if latest is None:
            raise RuntimeError("Manim ran successfully but no MP4 output was found.")

        # Copy to a flat, API-friendly path: media/videos/<scene_id>.mp4
        flat_out = OUTPUT_DIR / f"{scene_id}.mp4"
        shutil.copy2(latest, flat_out)
        logger.info("Manim output: %s", flat_out)
        return str(flat_out)

    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
