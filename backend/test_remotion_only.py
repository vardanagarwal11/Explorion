from renderers.remotion_renderer import render_remotion

code = '''
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

export default function MainScene() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 60, 660, 720], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0f172a, #1e293b)",
      color: "white",
      justifyContent: "center",
      alignItems: "center",
      fontFamily: "Segoe UI, sans-serif",
    }}>
      <div style={{opacity, textAlign: "center", width: 900}}>
        <h1 style={{fontSize: 58}}>Remotion Pipeline Check</h1>
        <p style={{fontSize: 28}}>24-second visualization timeline</p>
      </div>
    </AbsoluteFill>
  );
}
'''

out = render_remotion(code, scene_id="remotion_check")
print(out)
