"""
Local Manim rendering via subprocess.

Windows-safe implementation:
 - Uses subprocess.Popen + communicate() to avoid pipe deadlocks on Python 3.14
 - Falls back to PyAV stream-copy when manim's combine step fails
   (libx264 malloc crash on Python 3.14 / Windows)
 - Stream-copy: packets are muxed without decode/encode so libx264 is never opened
 - Auto-detects manim.exe inside the local venv (Scripts/ on Windows)
 - Resolves ffmpeg via imageio_ffmpeg (bundled in venv) as primary,
   backend/bin/ as secondary, then system PATH
 - Stubs out sox with a Python-based ffmpeg wrapper when sox is not installed
"""

import asyncio
import logging
import os
import re
import subprocess
import sys
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


def _get_ffmpeg_path() -> str:
    """Resolve ffmpeg binary path.

    Priority:
    1. imageio_ffmpeg bundled binary (always present in venv if imageio is installed)
    2. Chocolatey-installed ffmpeg (C:\\ProgramData\\chocolatey\\lib\\ffmpeg\\...)
    3. backend/bin/ffmpeg.exe (manually placed)
    4. System PATH ffmpeg (shim or global install)
    """
    # 1. imageio_ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_bin and Path(ffmpeg_bin).exists():
            logger.info("[ffmpeg] Using imageio_ffmpeg bundled binary: %s", ffmpeg_bin)
            return ffmpeg_bin
    except (ImportError, RuntimeError):
        pass

    # 2. Chocolatey ffmpeg install (choco install ffmpeg)
    _choco_ffmpeg_dir = Path(r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin")
    for candidate in (_choco_ffmpeg_dir / "ffmpeg.exe",):
        if candidate.exists():
            logger.info("[ffmpeg] Using chocolatey ffmpeg: %s", candidate)
            return str(candidate)

    # 3. backend/bin/ffmpeg.exe
    _backend_bin = Path(__file__).parent.parent / "bin"
    for candidate in (_backend_bin / "ffmpeg.exe", _backend_bin / "ffmpeg"):
        if candidate.exists():
            logger.info("[ffmpeg] Using backend/bin binary: %s", candidate)
            return str(candidate)

    # 4. System PATH (choco shim or global)
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        logger.info("[ffmpeg] Using system PATH ffmpeg: %s", system_ffmpeg)
        return system_ffmpeg

    logger.warning("[ffmpeg] ffmpeg not found anywhere — Manim may fail")
    return "ffmpeg"


def _ensure_sox_available(proc_env: dict, tmpdir_path: Path) -> dict:
    """Ensure sox is resolvable for manim-voiceover.

    Strategy (in priority order):
    1. System sox is already on PATH — do nothing.
    2. backend/bin/sox.exe exists and is executable — add bin/ to PATH.
    3. No sox anywhere — create a tiny Python wrapper script in tmpdir that
       calls ffmpeg to convert audio. manim-voiceover only uses sox for
       simple format conversion (mp3 → wav) so ffmpeg can substitute.
    """
    import shutil

    # 1. Already available
    if shutil.which("sox", path=proc_env.get("PATH", os.environ.get("PATH", ""))):
        logger.info("[sox] Found sox on PATH — no action needed")
        return proc_env

    # 2. backend/bin/sox.exe
    _bin_dir = Path(__file__).parent.parent / "bin"
    _sox_bin = _bin_dir / "sox.exe"
    if _sox_bin.exists():
        proc_env = proc_env.copy()
        proc_env["PATH"] = str(_bin_dir) + os.pathsep + proc_env.get("PATH", "")
        logger.info("[sox] Using backend/bin/sox.exe")
        return proc_env

    # 3. Fallback: create a sox-shim bat that calls ffmpeg
    # manim-voiceover calls sox like: sox input.mp3 -r 24000 output.wav
    # ffmpeg equivalent: ffmpeg -y -i input.mp3 output.wav
    ffmpeg_exe = _get_ffmpeg_path()
    shim_lines = [
        "@echo off",
        "REM sox-shim: translates simple sox calls to ffmpeg",
        "set INPUT=%~1",
        "set OUTPUT=%~2",
        f'"{ffmpeg_exe}" -y -i %INPUT% %OUTPUT% >nul 2>&1',
    ]
    sox_shim = tmpdir_path / "sox.bat"
    sox_shim.write_text("\r\n".join(shim_lines) + "\r\n", encoding="utf-8")
    proc_env = proc_env.copy()
    proc_env["PATH"] = str(tmpdir_path) + os.pathsep + proc_env.get("PATH", "")
    logger.warning("[sox] sox not found — using ffmpeg-based shim from %s", sox_shim)
    return proc_env


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

        # Fix old flat manim_voiceover imports before rendering.
        # The LLM may generate: from manim_voiceover.services import GTTSService
        # but newer manim-voiceover requires: from manim_voiceover.services.gtts import GTTSService
        _vo_fixes = [
            (r"from manim_voiceover\.services import GTTSService",
             "from manim_voiceover.services.gtts import GTTSService"),
            (r"from manim_voiceover\.services import GoogleTTS\b",
             "from manim_voiceover.services.gtts import GTTSService"),
            (r"from manim_voiceover\.services import AzureService",
             "from manim_voiceover.services.azure import AzureService"),
            (r"from manim_voiceover\.services import ElevenLabsService",
             "from manim_voiceover.services.elevenlabs import ElevenLabsService"),
            (r"from manim_voiceover\.services import RecorderService",
             "from manim_voiceover.services.recorder import RecorderService"),
        ]
        import re as _re2
        for _pat, _rep in _vo_fixes:
            code = _re2.sub(_pat, _rep, code)

        # Also ensure GTTSService is imported if it's used but not imported at all
        if "GTTSService" in code and not _re2.search(r"^\s*(from|import).*GTTSService", code, _re2.MULTILINE):
            code = "from manim_voiceover.services.gtts import GTTSService\n" + code


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

        # Build subprocess environment:
        # - Put imageio_ffmpeg (or backend/bin) ffmpeg at front of PATH
        # - Ensure sox is available (or shimmed with ffmpeg)
        proc_env = os.environ.copy()
        ffmpeg_exe = _get_ffmpeg_path()
        ffmpeg_dir = str(Path(ffmpeg_exe).parent) if ffmpeg_exe != "ffmpeg" else ""
        if ffmpeg_dir:
            proc_env["PATH"] = ffmpeg_dir + os.pathsep + proc_env.get("PATH", "")
            logger.info("%s ffmpeg resolved to: %s", tag, ffmpeg_exe)
        proc_env = _ensure_sox_available(proc_env, tmpdir_path)

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
                    "%d partial files -> PyAV stream-copy fallback.\nManim Log (if any):\n%s",
                    tag, len(partial), manim_log[-1500:]
                )
            else:
                logger.warning(
                    "%s Manim exited %d (combine step crashed). "
                    "%d partial files -> PyAV stream-copy fallback.\nManim Log:\n%s",
                    tag, returncode, len(partial), manim_log[-1500:]
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
