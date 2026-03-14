import { AbsoluteFill, useCurrentFrame, interpolate, spring } from "remotion";

const colors = {
  primary: '#3498db',
  secondary: '#f1c40f',
  background: '#2c3e50',
  highlight: '#e74c3c',
  text: '#ecf0f1',
  pipeline: '#e74c3c',
  data: '#2ecc71',
};

export default function MainScene() {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 50], [0, 1], { extrapolate: 'clamp' });
  const titleScale = interpolate(frame, [0, 100], [0, 1], { extrapolate: 'clamp' });

  const pipelineScale = interpolate(frame, [150, 200], [0, 1], { extrapolate: 'clamp' });
  const pipelineTranslateX = interpolate(frame, [150, 250], [-100, 0], { extrapolate: 'clamp' });

  const videoScale = interpolate(frame, [200, 250], [0, 1], { extrapolate: 'clamp' });
  const videoTranslateX = interpolate(frame, [200, 300], [-50, 0], { extrapolate: 'clamp' });

  const dataScale = interpolate(frame, [300, 350], [0, 1], { extrapolate: 'clamp' });
  const dataTranslateX = interpolate(frame, [300, 400], [-100, 0], { extrapolate: 'clamp' });

  const overflowScale = interpolate(frame, [500, 550], [0, 1], { extrapolate: 'clamp' });
  const overflowTranslateX = interpolate(frame, [500, 600], [-50, 0], { extrapolate: 'clamp' });

  const summaryOpacity = interpolate(frame, [700, 750], [0, 1], { extrapolate: 'clamp' });
  const summaryScale = interpolate(frame, [700, 800], [0, 1], { extrapolate: 'clamp' });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.background, fontFamily: 'Arial' }}>
      {/* Phase 1: Title and intro */}
      <div style={{
        fontSize: 48,
        fontWeight: 'bold',
        color: colors.text,
        opacity: titleOpacity,
        transform: `scale(${titleScale})`,
        textAlign: 'center',
        paddingTop: 100,
      }}>
        MLLM Overwhelmed by Video Data
      </div>

      {/* Phase 2: Setup/context */}
      <div style={{
        fontSize: 24,
        color: colors.text,
        opacity: interpolate(frame, [150, 200], [0, 1], { extrapolate: 'clamp' }),
        transform: `scale(${pipelineScale}) translateX(${pipelineTranslateX}px)`,
        textAlign: 'center',
        paddingTop: 200,
      }}>
        Large Language Model (LLM) Pipeline
      </div>
      <div style={{
        width: 200,
        height: 50,
        backgroundColor: colors.pipeline,
        opacity: pipelineScale,
        transform: `scale(${pipelineScale}) translateX(${pipelineTranslateX}px)`,
        borderRadius: 10,
        marginTop: 20,
        marginLeft: 'auto',
        marginRight: 'auto',
      }} />

      {/* Phase 3: Core concept animation */}
      <div style={{
        fontSize: 24,
        color: colors.text,
        opacity: interpolate(frame, [200, 250], [0, 1], { extrapolate: 'clamp' }),
        transform: `scale(${videoScale}) translateX(${videoTranslateX}px)`,
        textAlign: 'center',
        paddingTop: 300,
      }}>
        Video Data Input
      </div>
      <div style={{
        width: 200,
        height: 50,
        backgroundColor: colors.data,
        opacity: videoScale,
        transform: `scale(${videoScale}) translateX(${videoTranslateX}px)`,
        borderRadius: 10,
        marginTop: 20,
        marginLeft: 'auto',
        marginRight: 'auto',
      }} />

      {/* Phase 4: Key insight or comparison */}
      <div style={{
        fontSize: 24,
        color: colors.text,
        opacity: interpolate(frame, [300, 350], [0, 1], { extrapolate: 'clamp' }),
        transform: `scale(${dataScale}) translateX(${dataTranslateX}px)`,
        textAlign: 'center',
        paddingTop: 400,
      }}>
        Spatiotemporal Data Overflow
      </div>
      <div style={{
        width: 200,
        height: 50,
        backgroundColor: colors.data,
        opacity: dataScale,
        transform: `scale(${dataScale}) translateX(${dataTranslateX}px)`,
        borderRadius: 10,
        marginTop: 20,
        marginLeft: 'auto',
        marginRight: 'auto',
      }} />
      <div style={{
        width: 200,
        height: 50,
        backgroundColor: colors.pipeline,
        opacity: dataScale,
        transform: `scale(${dataScale}) translateX(${dataTranslateX}px)`,
        borderRadius: 10,
        marginTop: 20,
        marginLeft: 'auto',
        marginRight: 'auto',
        overflow: 'hidden',
        position: 'relative',
      }}>
        <div style={{
          width: 200,
          height: 50,
          backgroundColor: colors.data,
          opacity: dataScale,
          transform: `scale(${dataScale}) translateX(${dataTranslateX}px)`,
          borderRadius: 10,
          position: 'absolute',
          top: 0,
          left: 0,
        }} />
      </div>

      {/* Phase 5: Summary and conclusion */}
      <div style={{
        fontSize: 24,
        color: colors.text,
        opacity: summaryOpacity,
        transform: `scale(${summaryScale})`,
        textAlign: 'center',
        paddingTop: 500,
      }}>
        Conclusion: MLLM Overwhelmed by Video Data
      </div>
      <div style={{
        fontSize: 18,
        color: colors.text,
        opacity: summaryOpacity,
        transform: `scale(${summaryScale})`,
        textAlign: 'center',
        paddingTop: 20,
      }}>
        The large language model is overwhelmed by the massive amount of spatiotemporal data from the video input, causing the pipeline to overflow.
      </div>
    </AbsoluteFill>
  );
}