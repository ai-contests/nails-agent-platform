import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { BRAND_COLORS, DEMO_STYLES } from "../constants";
import { globalStyle } from "../theme";

const StyleCard: React.FC<{
  style: (typeof DEMO_STYLES)[0];
  rank: number;
  delayFrames: number;
  frame: number;
  fps: number;
  highlighted?: boolean;
}> = ({ style, rank, delayFrames, frame, fps, highlighted }) => {
  const scale = spring({
    frame: Math.max(frame - delayFrames, 0),
    fps,
    config: { damping: 14, stiffness: 130 },
    from: 0,
    to: 1,
  });
  const opacity = interpolate(frame, [delayFrames, delayFrames + 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{
      transform: `scale(${scale})`,
      opacity,
      background: highlighted ? `${BRAND_COLORS.accent}18` : BRAND_COLORS.card,
      border: `1.5px solid ${highlighted ? BRAND_COLORS.accent : BRAND_COLORS.border}`,
      borderRadius: 14,
      padding: "14px 16px",
      width: 240,
      position: "relative",
      boxShadow: highlighted ? `0 0 20px ${BRAND_COLORS.accent}30` : "none",
    }}>
      {/* Nail color swatch */}
      <div style={{
        width: "100%", height: 100, borderRadius: 10, marginBottom: 10,
        background: `linear-gradient(135deg, ${style.color}, ${style.accent})`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 32,
      }}>
        💅
      </div>
      {/* Rank badge */}
      <div style={{
        position: "absolute", top: 10, left: 10,
        background: rank === 1 ? BRAND_COLORS.accent : BRAND_COLORS.surface,
        color: rank === 1 ? "#000" : BRAND_COLORS.textMuted,
        borderRadius: 6, padding: "2px 8px", fontSize: 11, fontWeight: 700,
      }}>
        #{rank}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: BRAND_COLORS.text, marginBottom: 4 }}>{style.title}</div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 11, color: BRAND_COLORS.textMuted }}>匹配度</span>
        <span style={{ fontSize: 13, color: BRAND_COLORS.accent, fontWeight: 700 }}>{style.score}</span>
      </div>
      {/* Score bar */}
      <div style={{ background: BRAND_COLORS.border, borderRadius: 3, height: 4, marginTop: 6, overflow: "hidden" }}>
        <div style={{
          width: `${style.score}%`, height: "100%",
          background: `linear-gradient(90deg, ${BRAND_COLORS.accent}, ${BRAND_COLORS.pink})`,
          borderRadius: 3,
        }} />
      </div>
    </div>
  );
};

export const Round1Scene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const headerOpacity = interpolate(f, [0, 20], [0, 1]);
  const exitOpacity = interpolate(f, [duration - 20, duration], [1, 0]);

  return (
    <div style={{ ...globalStyle, opacity: exitOpacity }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 50% 60%, #0e0d18 0%, ${BRAND_COLORS.bg} 70%)`,
      }} />

      {/* Header */}
      <div style={{ position: "absolute", left: 120, top: 80, opacity: headerOpacity }}>
        <div style={{ fontSize: 13, letterSpacing: "0.3em", color: BRAND_COLORS.accent, textTransform: "uppercase" }}>Step 3</div>
        <div style={{ fontSize: 52, fontWeight: 700, color: BRAND_COLORS.text, lineHeight: 1.15, marginTop: 8 }}>
          第一轮推荐
        </div>
        <div style={{ fontSize: 17, color: BRAND_COLORS.textMuted, marginTop: 8 }}>
          根据手型 · 肤色 · 色调智能匹配 · 从 {DEMO_STYLES.length} 款精选
        </div>
      </div>

      {/* Cards grid */}
      <div style={{
        position: "absolute",
        left: "50%", top: "55%",
        transform: "translate(-50%, -50%)",
        display: "flex", gap: 20, alignItems: "center",
        flexWrap: "wrap", justifyContent: "center",
        width: 1600,
      }}>
        {DEMO_STYLES.map((style, i) => (
          <StyleCard
            key={style.id}
            style={style}
            rank={i + 1}
            delayFrames={i * 12 + 10}
            frame={f}
            fps={fps}
            highlighted={i === 0}
          />
        ))}
      </div>

      {/* API tag */}
      <div style={{
        position: "absolute", bottom: 60, right: 120,
        fontSize: 12, color: BRAND_COLORS.textMuted, fontFamily: "monospace",
        opacity: interpolate(f, [80, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        POST /sessions/{"{id}"}/recommendations/round1
      </div>
    </div>
  );
};
