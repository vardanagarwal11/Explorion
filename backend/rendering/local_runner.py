"""
Local Manim rendering via subprocess.

Windows-safe implementation:
 - Uses subprocess.Popen + communicate() to avoid pipe deadlocks on Python 3.14
 - Falls back to PyAV stream-copy when manim's combine step fails
   (libx264 malloc crash on Python 3.14 / Windows)
 - Stream-copy: packets are muxed without decode/encode so libx264 is never opened
 - Auto-detects manim.exe inside the local venv (Scripts/ on Windows)
"""

import asyncio
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_manim_executable() -> str:
    """Return path to the manim CLI, preferring the local venv."""
    env_val = os.getenv("MANIM_EXECUTABLE")
    if env_val and Path(env_val).exists():
        return env_val

    import sys
    scripts = Path(sys.executable).parent  # Scripts/ on Windows, bin/ on Unix
    for candidate in (scripts / "manim.exe", scripts / "manim"):
        if candidate.exists():
            return str(candidate)
    return "manim"


def extract_scene_name(code: str) -> str:
    """
    Extract the Scene class name from Manim code.

    Looks for patterns like: class MyScene(Scene), class TestScene(ThreeDScene), etc.
    """
    # Match class definitions that inherit from Scene or any *Scene class
    pattern = r'class\s+(\w+)\s*\(\s*\w*Scene\s*\)'
    match = re.search(pattern, code)
    if match:
        return match.group(1)
    return "MainScene"  # Fallback


def _combine_partial_movies_av(partial_files: list, output_path: Path) -> None:
    """Concatenate partial MP4s using PyAV packet-level stream copy.

    Does NOT decode or encode any frames — libx264 is never opened,
    so the libx264 malloc crash on Python 3.14 / Windows is avoided.
    Packets are remuxed directly from each partial into a single output container.
    """
    import av  # local import — only needed in fallback path

    ordered = sorted(partial_files, key=lambda p: p.stat().st_mtime)
    logger.info(
        "  [Combiner] PyAV stream-copy: %d parts -> %s", len(ordered), output_path.name
    )

    with av.open(str(output_path), "w", format="mp4") as out_c:
        out_stream = None
        pts_offset = 0

        for part in ordered:
            with av.open(str(part)) as inp:
                in_vs = inp.streams.video
                if not in_vs:
                    logger.warning("  [Combiner] No video stream in %s, skipping", part.name)
                    continue
                in_s = in_vs[0]

                if out_stream is None:
                    # Create output stream with the input codec.
                    # NOTE: do NOT pass template= kwarg — it is broken in PyAV v16.
                    # Copy relevant parameters manually instead.
                    codec_name = in_s.codec_context.codec.name
                    out_stream = out_c.add_stream(codec_name)
                    out_stream.width = in_s.width
                    out_stream.height = in_s.height
                    out_stream.time_base = in_s.time_base
                    try:
                        if in_s.codec_context.extradata:
                            out_stream.codec_context.extradata = in_s.codec_context.extradata
                    except Exception:
                        pass  # extradata copy failure is non-fatal

                seg_end = 0
                for pkt in inp.demux(in_s):
                    if pkt.dts is None:
                        continue
                    orig_pts = pkt.pts if pkt.pts is not None else pkt.dts
                    orig_dts = pkt.dts
                    pkt.pts = orig_pts + pts_offset
                    pkt.dts = orig_dts + pts_offset
                    pkt.stream = out_stream
                    end = orig_pts + (pkt.duration or 0)
                    if end > seg_end:
                        seg_end = end
                    out_c.mux(pkt)

                pts_offset += seg_end

    sz = output_path.stat().st_size
    logger.info(
        "  [Combiner] Done -> %s (%d bytes)",
        output_path.name,
        sz,
    )
    if sz < 512:
        raise RuntimeError(
            f"Combined video suspiciously small ({sz} bytes) — stream copy may have failed."
        )


def _run_manim_subprocess(
    code: str,
    scene_name: str,
    quality: str,
    label: str = "",
) -> bytes:
    """Run a single Manim render subprocess and return video bytes.

    Handles two failure modes unique to manim + Python 3.14 on Windows:

    1. manim exits with code != 0 but partial_movie_files were written:
       Manim's PyAV-based combine step fails due to a libx264 malloc bug.
       We fall back to ``_combine_partial_movies_av`` (stream-copy, no x264).

    2. manim .exe not on PATH:
       ``get_manim_executable`` now also checks for ``manim.exe`` (Windows).
    """
    manim_executable = get_manim_executable()
    tag = f"  [Renderer{label}]"

    # Locate backend/bin where we placed ffmpeg.exe, and build a PATH that
    # includes it so manim's subprocess calls to 'ffmpeg' succeed.
    _backend_bin = Path(__file__).parent.parent / "bin"
    _ffmpeg_path = _backend_bin / "ffmpeg.exe"
    _ffmpeg_dir = str(_backend_bin) if _ffmpeg_path.exists() else ""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        code_path = tmpdir_path / "scene.py"
        logger.info(f"{tag} Writing Manim code to {code_path.name}")
        code_path.write_text(code, encoding="utf-8")

        # Override codec to mpeg4 so manim doesn't try libx264 (which hangs on
        # Python 3.14 / Windows with the LGPL ffmpeg build we ship).
        # Manim checks manim.cfg in cwd first, so writing it to tmpdir works.
        manim_cfg = tmpdir_path / "manim.cfg"
        manim_cfg.write_text(
            "[CLI]\nvideo_codec = mpeg4\n",
            encoding="utf-8",
        )

        output_dir = tmpdir_path / "media"
        quality_flags = {
            "low_quality": "-ql",
            "medium_quality": "-qm",
            "high_quality": "-qh",
        }
        quality_flag = quality_flags.get(quality, "-ql")
        logger.info(f"{tag} Rendering quality: {quality} ({quality_flag})")

        cmd = [
            manim_executable,
            "render",
            str(code_path),
            scene_name,
            quality_flag,
            "--format=mp4",
            f"--media_dir={output_dir}",
        ]

        # Build subprocess environment: inject backend/bin at front of PATH
        # so 'ffmpeg' resolves to our bundled binary.
        proc_env = os.environ.copy()
        if _ffmpeg_dir:
            proc_env["PATH"] = _ffmpeg_dir + os.pathsep + proc_env.get("PATH", "")
            logger.info("%s Using ffmpeg from %s", tag, _ffmpeg_dir)
        else:
            logger.warning("%s backend/bin/ffmpeg.exe not found; using PATH ffmpeg", tag)

        logger.info("%s Starting Manim render: %s (%s)", tag, scene_name, quality)

        # Use Popen + communicate() — NOT capture_output=True.
        # On Windows / Python 3.14 using both stdout=PIPE and stderr=PIPE
        # deadlocks when the combined output exceeds the OS pipe buffer.
        # Merging stderr into stdout (stderr=STDOUT) gives a single pipe
        # that communicate() reads without blocking.
        timed_out = False
        stdout_bytes = b""
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=tmpdir,
                env=proc_env,
            )
            # Timeout of 120s is generous for frame rendering.
            # Manim typically finishes quickly and only hangs at the
            # ffmpeg/PyAV combine step — we catch that below.
            stdout_bytes, _ = proc.communicate(timeout=120)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_bytes, _ = proc.communicate()
            timed_out = True
            returncode = -1  # sentinel

        manim_log = (
            stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        )
        if manim_log:
            logger.debug("%s manim output:\n%s", tag, manim_log[-3000:])

        # Collect output files
        all_mp4 = list(output_dir.rglob("*.mp4"))
        partial = [f for f in all_mp4 if "partial_movie_files" in str(f)]
        final   = [f for f in all_mp4 if "partial_movie_files" not in str(f)]

        if returncode == 0 and not timed_out:
            logger.info("%s Manim completed OK", tag)
            if not all_mp4:
                raise RuntimeError(f"No mp4 produced.\n{manim_log[-1000:]}")
            candidates = final if final else all_mp4
            video_file = max(candidates, key=lambda f: f.stat().st_size)

        elif partial:
            # Two cases land here:
            # (a) Manim's combine step crashed (libx264 malloc on Python 3.14/Windows)
            #     causing a non-zero exit code.
            # (b) Manim timed out while waiting for its ffmpeg/PyAV combine step.
            # Either way, partial_movie_files were written and we can combine them
            # ourselves using PyAV stream-copy which never opens libx264.
            if timed_out:
                logger.warning(
                    "%s Manim timed out (combine step hung). "
                    "%d partial files -> PyAV stream-copy fallback.",
                    tag, len(partial),
                )
            else:
                logger.warning(
                    "%s Manim exited %d (combine step crashed). "
                    "%d partial files -> PyAV stream-copy fallback.",
                    tag, returncode, len(partial),
                )
            combined = tmpdir_path / "combined.mp4"
            _combine_partial_movies_av(partial, combined)
            video_file = combined

        else:
            reason = "timed out" if timed_out else f"exit {returncode}"
            logger.error("%s Manim failed (%s), no partial files.\n%s", tag, reason, manim_log[-2000:])
            raise RuntimeError(
                f"Manim render failed ({reason}):\n{manim_log[-1500:]}"
            )

        logger.info(
            "%s Video ready: %s (%d bytes)",
            tag, video_file.name, video_file.stat().st_size,
        )
        return video_file.read_bytes()


def _render_manim_sync(
    code: str,
    scene_name: str,
    quality: str = "low_quality"
) -> bytes:
    """
    Synchronous Manim rendering.

    Args:
        code: Complete Manim Python code
        scene_name: Name of the Scene class to render
        quality: "low_quality", "medium_quality", or "high_quality"

    Returns:
        MP4 video file as bytes

    Raises:
        RuntimeError: If rendering fails
    """
    return _run_manim_subprocess(code, scene_name, quality)


async def render_manim_local(
    code: str,
    scene_name: Optional[str] = None,
    quality: str = "low_quality"
) -> bytes:
    """
    Async wrapper for local Manim rendering.

    Runs the synchronous subprocess in a thread pool to avoid blocking.

    Args:
        code: Complete Manim Python code
        scene_name: Name of the Scene class to render (auto-detected if None)
        quality: "low_quality", "medium_quality", or "high_quality"

    Returns:
        MP4 video file as bytes
    """
    if scene_name is None:
        logger.info("  [Renderer] Extracting scene name from code")
        scene_name = extract_scene_name(code)
        logger.info(f"  [Renderer] Detected scene name: {scene_name}")

    logger.info(f"[Rendering] Starting async render for {scene_name}")

    # Run in thread pool to not block async event loop
    return await asyncio.to_thread(
        _render_manim_sync,
        code,
        scene_name,
        quality
    )


# Test code for manual verification
TEST_MANIM_CODE = '''
from manim import *

class TestScene(Scene):
    def construct(self):
        circle = Circle(color=BLUE)
        square = Square(color=RED).shift(RIGHT * 2)
        self.play(Create(circle))
        self.play(Transform(circle, square))
        self.wait()
'''

if __name__ == "__main__":
    # Quick test
    import sys

    print(f"Using Manim executable: {get_manim_executable()}")
    print(f"Extracted scene name: {extract_scene_name(TEST_MANIM_CODE)}")

    try:
        print("Rendering test scene...")
        video_bytes = _render_manim_sync(TEST_MANIM_CODE, "TestScene", "low_quality")

        # Save to file
        output_path = Path("test_output.mp4")
        output_path.write_bytes(video_bytes)
        print(f"Success! Video saved to {output_path} ({len(video_bytes)} bytes)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
