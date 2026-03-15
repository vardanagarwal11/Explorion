"""
Rendering package for Explorion.

Uses local subprocess rendering only.
"""

import logging
from .local_runner import render_manim_local, extract_scene_name
from .storage import save_video, get_video_path, get_video_url, list_videos, get_backend

logger = logging.getLogger(__name__)

__all__ = [
    "render_manim_local",
    "extract_scene_name",
    "save_video",
    "get_video_path",
    "get_video_url",
    "list_videos",
    "process_visualization",
    "render_manim",
    "get_backend",
]


async def render_manim(code: str, scene_name: str, quality: str = "low_quality") -> bytes:
    """
    Render Manim code locally via subprocess.

    Args:
        code: Complete Manim Python code
        scene_name: Name of the Scene class to render
        quality: Rendering quality ("low_quality", "medium_quality", "high_quality")

    Returns:
        MP4 video file as bytes
    """
    return await render_manim_local(code, scene_name, quality)


async def process_visualization(viz_id: str, manim_code: str, quality: str = "low_quality") -> str:
    """
    Process a visualization: render Manim code and save the video.

    Args:
        viz_id: Unique identifier for this visualization
        manim_code: Complete Manim Python code
        quality: Rendering quality

    Returns:
        URL path to the rendered video (e.g., "/api/video/viz_001")
    """
    logger.info(f"[Processing Visualization] {viz_id}")

    scene_name = extract_scene_name(manim_code)
    logger.info(f"[Processing Visualization] Scene name: {scene_name}")

    video_bytes = await render_manim(manim_code, scene_name, quality)
    logger.info(f"[Processing Visualization] Rendering complete ({len(video_bytes):,} bytes)")

    video_url = await save_video(video_bytes, f"{viz_id}.mp4")
    logger.info(f"[Processing Visualization] Video saved: {video_url}")

    return video_url
