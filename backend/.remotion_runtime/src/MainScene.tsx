import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export default function MainScene() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animated gradient background
  const bgHue = interpolate(frame, [0, 900], [220, 260], { extrapolateRight: "clamp" });

  // Phase 1: Central core introduction (0-150 frames / 0-5s)
  const coreProgress = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });
  const coreScale = interpolate(coreProgress, [0, 1], [0.5, 1]);
  const coreOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  // Phase 2: Branching arms introduction (150-300 frames / 5-10s)
  const armProgress = spring({ frame: Math.max(0, frame - 150), fps, config: { damping: 14 } });
  const armScale = interpolate(armProgress, [0, 1], [0.5, 1]);
  const armOpacity = interpolate(frame, [150, 180], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Phase 3: Problem generation (300-450 frames / 10-15s)
  const problemProgress = spring({ frame: Math.max(0, frame - 300), fps, config: { damping: 10 } });
  const problemOpacity = interpolate(frame, [300, 330], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Phase 4: Pattern flow (450-600 frames / 15-20s)
  const patternProgress = interpolate(frame, [450, 550], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Phase 5: Framework highlight (600-750 frames / 20-25s)
  const highlightProgress = spring({ frame: Math.max(0, frame - 600), fps, config: { damping: 10 } });
  const highlightOpacity = interpolate(frame, [600, 630], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Phase 6: Conclusion (750-900 frames / 25-30s)
  const conclusionOpacity = interpolate(frame, [750, 780, 860, 900], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, hsl(${bgHue}, 35%, 8%), hsl(${bgHue + 20}, 40%, 14%))`,
        fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
      }}
    >
      {/* Subtle grid pattern */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* Central core */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%) scale(${coreScale})`,
          opacity: coreOpacity,
          background: `rgba(255,255,255,0.06)`,
          backdropFilter: "blur(20px)",
          borderRadius: 20,
          padding: "40px",
          width: 100,
          height: 100,
          boxShadow: `0 8px 32px rgba(63, 99, 255, 0.2)`,
        }}
      >
        <div
          style={{
            background: "#4FC3F7",
            borderRadius: 10,
            padding: "10px",
            width: 40,
            height: 40,
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: `translate(-50%, -50%)`,
          }}
        >
          <div
            style={{
              background: "#FFA726",
              borderRadius: 5,
              padding: "5px",
              width: 20,
              height: 20,
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: `translate(-50%, -50%)`,
              opacity: interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" }),
            }}
          />
        </div>
      </div>

      {/* Branching arms */}
      <div
        style={{
          display: "flex",
          gap: 40,
          alignItems: "center",
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%) scale(${armScale})`,
          opacity: armOpacity,
        }}
      >
        <div
          style={{
            background: `rgba(255,255,255,0.06)`,
            backdropFilter: "blur(20px)",
            borderRadius: 20,
            padding: "20px",
            width: 100,
            height: 100,
            boxShadow: `0 8px 32px rgba(99, 255, 63, 0.2)`,
          }}
        >
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: "#000000",
              textAlign: "center",
            }}
          >
            Inference
          </div>
        </div>
        <div
          style={{
            background: `rgba(255,255,255,0.06)`,
            backdropFilter: "blur(20px)",
            borderRadius: 20,
            padding: "20px",
            width: 100,
            height: 100,
            boxShadow: `0 8px 32px rgba(63, 99, 255, 0.2)`,
          }}
        >
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: "#000000",
              textAlign: "center",
            }}
          >
            Entailment
          </div>
        </div>
        <div
          style={{
            background: `rgba(255,255,255,0.06)`,
            backdropFilter: "blur(20px)",
            borderRadius: 20,
            padding: "20px",
            width: 100,
            height: 100,
            boxShadow: `0 8px 32px rgba(255, 171, 38, 0.2)`,
          }}
        >
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: "#000000",
              textAlign: "center",
            }}
          >
            Consistency
          </div>
        </div>
        <div
          style={{
            background: `rgba(255,255,255,0.06)`,
            backdropFilter: "blur(20px)",
            borderRadius: 20,
            padding: "20px",
            width: 100,
            height: 100,
            boxShadow: `0 8px 32px rgba(99, 255, 63, 0.2)`,
          }}
        >
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: "#000000",
              textAlign: "center",
            }}
          >
            Reasoning
          </div>
        </div>
      </div>

      {/* Problem generation */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%)`,
          opacity: problemOpacity,
        }}
      >
        <div
          style={{
            background: `linear-gradient(135deg, #6c5ce7, #66BB6A)`,
            borderRadius: 10,
            padding: "10px",
            width: 200,
            height: 200,
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: `translate(-50%, -50%)`,
          }}
        />
      </div>

      {/* Pattern flow */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%)`,
          opacity: patternProgress,
        }}
      >
        <div
          style={{
            background: `linear-gradient(135deg, #6c5ce7, #66BB6A)`,
            borderRadius: 10,
            padding: "10px",
            width: 400,
            height: 400,
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: `translate(-50%, -50%)`,
          }}
        />
      </div>

      {/* Framework highlight */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%)`,
          opacity: highlightOpacity,
        }}
      >
        <div
          style={{
            background: `rgba(255,255,255,0.06)`,
            backdropFilter: "blur(20px)",
            borderRadius: 20,
            padding: "20px",
            width: 200,
            height: 200,
            boxShadow: `0 8px 32px rgba(63, 99, 255, 0.2)`,
          }}
        />
      </div>

      {/* Conclusion */}
      <div
        style={{
          position: "absolute",
          bottom: 30,
          opacity: conclusionOpacity,
          fontSize: 16,
          color: "rgba(255,255,255,0.5)",
        }}
      >
        Logifus Framework: Enhancing Reasoning through Obfuscated Problem Generation
      </div>
    </AbsoluteFill>
  );
}