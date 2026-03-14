import json
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
print("Setting up logging...", flush=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

print("Importing run_pipeline...", flush=True)
try:
    from pipeline.graph import run_pipeline
    print("Import successful.", flush=True)
except Exception as e:
    print(f"Error during import: {e}", flush=True)

URL = "https://arxiv.org/abs/2508.12111"

print(f"Starting pipeline for {URL}...", flush=True)

URL = "https://arxiv.org/abs/2508.12111"

result = run_pipeline(URL)
print(json.dumps({
    "paper_id": result.get("paper_id"),
    "title": result.get("title"),
    "scene_count": len(result.get("scenes", [])),
    "errors": result.get("errors", []),
}, indent=2))

# Duration probe using PyAV (available with Manim deps)
try:
    import av
except Exception:
    av = None

engine_count = {"manim": 0, "remotion": 0}
for i, s in enumerate(result.get("scenes", [])):
    engine = s.get("engine", "")
    if engine in engine_count:
        engine_count[engine] += 1

    vp = s.get("video_path")
    dur = None
    if vp and av and Path(vp).exists():
        try:
            with av.open(vp) as c:
                dur = float(c.duration / av.time_base) if c.duration else None
        except Exception:
            dur = None

    print(json.dumps({
        "idx": i,
        "title": s.get("title"),
        "engine": engine,
        "video_path": vp,
        "duration_seconds": dur,
    }, indent=2))

print(json.dumps({"engine_count": engine_count}, indent=2))
