"""
Remotion renderer for the local pipeline.

Uses a persistent runtime project to avoid reinstalling dependencies per scene.
Renders longer scenes suitable for educational explainers.
"""

import json
import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "media" / "videos"
RUNTIME_DIR = Path(__file__).parent.parent / ".remotion_runtime"
SRC_DIR = RUNTIME_DIR / "src"

FPS = 30
DURATION_FRAMES = 900  # 30 seconds
WIDTH = 1280
HEIGHT = 720

_PACKAGE_JSON = {
    "name": "explorion-remotion-runtime",
    "version": "1.0.0",
    "private": True,
    "dependencies": {
        "remotion": "^4.0.0",
        "react": "^18.0.0",
        "react-dom": "^18.0.0",
    },
    "devDependencies": {
        "@remotion/cli": "^4.0.0",
        "@types/react": "^18.0.0",
        "typescript": "^5.0.0",
    },
}

_TS_CONFIG = {
    "compilerOptions": {
        "target": "ES2020",
        "lib": ["dom", "ES2020"],
        "jsx": "react-jsx",
        "strict": False,
        "module": "ESNext",
        "moduleResolution": "Node",
        "esModuleInterop": True,
        "skipLibCheck": True,
    },
    "include": ["src"],
}

_INDEX_TSX = f"""\
import React from \"react\";
import {{ registerRoot, Composition }} from \"remotion\";
import MainScene from \"./MainScene\";

const RemotionRoot: React.FC = () => {{
  return (
    <>
      <Composition
        id=\"MainScene\"
        component={{MainScene}}
        durationInFrames={{{DURATION_FRAMES}}}
        fps={{{FPS}}}
        width={{{WIDTH}}}
        height={{{HEIGHT}}}
      />
    </>
  );
}};

registerRoot(RemotionRoot);
"""


def _ensure_runtime_project() -> None:
    """Create/refresh runtime project and install deps once."""
    if not shutil.which("node"):
        raise RuntimeError("Node.js is not on PATH. Install Node >= 18 to render Remotion scenes.")

    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    if not shutil.which(npm_cmd):
        raise RuntimeError("npm is not on PATH. Install Node.js with npm included.")

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    SRC_DIR.mkdir(parents=True, exist_ok=True)

    (RUNTIME_DIR / "package.json").write_text(json.dumps(_PACKAGE_JSON, indent=2), encoding="utf-8")
    (RUNTIME_DIR / "tsconfig.json").write_text(json.dumps(_TS_CONFIG, indent=2), encoding="utf-8")
    (SRC_DIR / "index.tsx").write_text(_INDEX_TSX, encoding="utf-8")

    node_modules = RUNTIME_DIR / "node_modules"
    if not node_modules.exists():
        logger.info("Installing Remotion runtime dependencies (first run)...")
        install = subprocess.run(
            [npm_cmd, "install", "--no-audit", "--no-fund"],
            cwd=RUNTIME_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=600,
        )
        if install.returncode != 0:
            raise RuntimeError(f"Remotion npm install failed: {install.stderr[-800:]}")


def _fallback_component(scene_id: str) -> str:
    """Safe fallback component when generated code fails to render."""
    safe = scene_id.replace("`", "'")
    return """\
import React from \"react\";
import { AbsoluteFill, useCurrentFrame, interpolate } from \"remotion\";

export default function MainScene() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 40, 860, 900], [0, 1, 1, 0], {
    extrapolateLeft: \"clamp\",
    extrapolateRight: \"clamp\",
  });

  return (
    <AbsoluteFill
      style={{
        background: \"linear-gradient(135deg, #0d1b2a, #1b263b)\",
        color: \"white\",
        justifyContent: \"center\",
        alignItems: \"center\",
        fontFamily: \"Segoe UI, sans-serif\",
      }}
    >
      <div style={{ opacity, width: 920, textAlign: \"center\" }}>
        <h1 style={{ fontSize: 58, marginBottom: 20 }}>Explorion Visualization</h1>
        <p style={{ fontSize: 28, lineHeight: 1.4 }}>Fallback scene for """ + safe + """</p>
        <p style={{ fontSize: 22, opacity: 0.8, marginTop: 18 }}>30 second render | Remotion</p>
      </div>
    </AbsoluteFill>
  );
}
"""


def render_remotion(code: str, scene_id: str | None = None) -> str:
    """
    Render a Remotion component and return absolute output MP4 path.
    """
    _ensure_runtime_project()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scene_id = scene_id or str(uuid.uuid4())[:8]
    output_file = OUTPUT_DIR / f"{scene_id}.mp4"
    scene_file = SRC_DIR / "MainScene.tsx"

    # Try generated component first.
    scene_file.write_text(code, encoding="utf-8")

    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    render_cmd = [
        npx_cmd,
        "remotion",
        "render",
        "src/index.tsx",
        "MainScene",
        str(output_file),
      "--timeout",
      "120000",
        "--overwrite",
    ]

    logger.info("Rendering Remotion scene %s", scene_id)
    render = subprocess.run(
        render_cmd,
        cwd=RUNTIME_DIR,
        capture_output=True,
        text=True,
      encoding="utf-8",
      errors="ignore",
        timeout=900,
    )

    if render.returncode != 0:
        logger.warning("Primary Remotion render failed; trying fallback component")
        logger.error("Remotion stderr:\n%s", render.stderr[-2000:])

        scene_file.write_text(_fallback_component(scene_id), encoding="utf-8")
        fallback = subprocess.run(
            render_cmd,
            cwd=RUNTIME_DIR,
            capture_output=True,
            text=True,
          encoding="utf-8",
          errors="ignore",
            timeout=900,
        )
        if fallback.returncode != 0:
            raise RuntimeError(
                "Remotion rendering failed and fallback failed:\n"
                f"Primary: {render.stderr[-500:]}\n"
                f"Fallback: {fallback.stderr[-500:]}"
            )

    return str(output_file)
