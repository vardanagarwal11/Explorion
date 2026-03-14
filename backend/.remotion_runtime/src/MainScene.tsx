import { AbsoluteFill, useCurrentFrame, interpolate, spring } from "remotion";

export default function MainScene() {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 150], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const contextOpacity = interpolate(frame, [150, 300], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const coreConceptScale = interpolate(frame, [300, 500], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const keyInsightScale = interpolate(frame, [500, 700], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const summaryOpacity = interpolate(frame, [700, 900], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#121212", height: "100%" }}>
      {/* Phase 1: Title and intro */}
      <div
        style={{
          fontSize: 64,
          fontFamily: "Arial",
          color: "#66d9ef",
          fontWeight: "bold",
          opacity: titleOpacity,
          textAlign: "center",
          paddingTop: 100,
        }}
      >
        Detector Assembly and Use
      </div>

      {/* Phase 2: Setup/context */}
      <div
        style={{
          fontSize: 24,
          fontFamily: "Arial",
          color: "#ffffff",
          opacity: contextOpacity,
          textAlign: "center",
          paddingTop: 200,
        }}
      >
        In a classroom or laboratory setting, students assemble and use the detector to learn about its components and functionality.
      </div>

      {/* Phase 3: Core concept animation */}
      <div
        style={{
          fontSize: 48,
          fontFamily: "Arial",
          color: "#f1c40f",
          opacity: coreConceptScale,
          textAlign: "center",
          paddingTop: 300,
          transform: `scale(${coreConceptScale})`,
        }}
      >
        3D Visualization of Detector and Equipment
      </div>

      {/* Phase 4: Key insight or comparison */}
      <div
        style={{
          fontSize: 36,
          fontFamily: "Arial",
          color: "#2ecc71",
          opacity: keyInsightScale,
          textAlign: "center",
          paddingTop: 400,
          transform: `scale(${keyInsightScale})`,
        }}
      >
        Students interact with the device in a realistic and educational way, gaining hands-on experience with the detector's components and functionality.
      </div>

      {/* Phase 5: Summary and conclusion */}
      <div
        style={{
          fontSize: 48,
          fontFamily: "Arial",
          color: "#9b59b6",
          opacity: summaryOpacity,
          textAlign: "center",
          paddingTop: 500,
        }}
      >
        By assembling and using the detector, students develop a deeper understanding of its components, functionality, and applications in a real-world setting.
      </div>
    </AbsoluteFill>
  );
}