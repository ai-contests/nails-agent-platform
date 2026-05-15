import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { BRAND_COLORS, DEMO_STYLES } from "../constants";
import { globalStyle } from "../theme";

export const InteractionScene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const exitOpacity = interpolate(f, [duration - 20, duration], [1, 0]);

  // Cursor appears and clicks at frame 40
  const cursorX = interpolate(f, [10, 40], [800, 520], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const cursorY = interpolate(f, [10, 40], [300, 480], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const clickScale = spring({ frame: Math.max(f - 42, 0), fps, config: { damping: 8, stiffness: 300 }, from: 1.4, to: 1 });
  const rippleScale = interpolate(f, [42, 65], [0.5, 3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const rippleOpacity = interpolate(f, [42, 65], [0.7, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const tagOpacity = interpolate(f, [50, 70], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tagY = interpolate(f, [50, 70], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const style = DEMO_STYLES[0];

  return (
    <div style={{ ...globalStyle, opacity: exitOpacity }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 50% 45%, #140e1a 0%, ${BRAND_COLORS.bg} 70%)`,
      }} />

      {/* Title */}
      <div style={{
        position: "absolute", top: 80, left: 0, right: 0, textAlign: "center",
        opacity: interpolate(f, [0, 20], [0, 1]),
      }}>
        <div style={{ fontSize: 13, letterSpacing: "0.3em", color: BRAND_COLORS.accent, textTransform: "uppercase" }}>Step 4</div>
        <div style={{ fontSize: 48, fontWeight: 700, color: BRAND_COLORS.text, marginTop: 8 }}>用户点击 · 行为学习</div>
        <div style={{ fontSize: 17, color: BRAND_COLORS.textMuted, marginTop: 8 }}>每一次点击都在训练你的专属推荐模型</div>
      </div>

      {/* Center: highlighted card */}
      <div style={{
        position: "absolute", left: "50%", top: "52%",
        transform: `translate(-50%, -50%) scale(${clickScale})`,
        background: `${BRAND_COLORS.accent}22`,
        border: `2px solid ${BRAND_COLORS.accent}`,
        borderRadius: 20,
        padding: "20px 24px",
        width: 280,
        boxShadow: `0 0 40px ${BRAND_COLORS.accent}40`,
      }}>
        <div style={{
          width: "100%", height: 140, borderRadius: 12,
          background: `linear-gradient(135deg, ${style.color}, ${style.accent})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 48, marginBottom: 16,
        }}>💅</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: BRAND_COLORS.text }}>{style.title}</div>
        <div style={{ fontSize: 13, color: BRAND_COLORS.accent, marginTop: 4 }}>✓ 已点击查看</div>
      </div>

      {/* Click ripple */}
      <div style={{
        position: "absolute",
        left: "50%", top: "52%",
        width: 80, height: 80,
        borderRadius: "50%",
        border: `2px solid ${BRAND_COLORS.accent}`,
        transform: `translate(-50%, -50%) scale(${rippleScale})`,
        opacity: rippleOpacity,
        pointerEvents: "none",
      }} />

      {/* Animated cursor */}
      <div style={{
        position: "absolute",
        left: cursorX, top: cursorY,
        fontSize: 28,
        transform: "rotate(-15deg)",
        pointerEvents: "none",
        filter: `drop-shadow(0 2px 8px ${BRAND_COLORS.accent}60)`,
      }}>
        👆
      </div>

      {/* Event log tag */}
      <div style={{
        position: "absolute", bottom: 120, left: "50%",
        transform: `translateX(-50%) translateY(${tagY}px)`,
        opacity: tagOpacity,
        background: BRAND_COLORS.surface,
        border: `1px solid ${BRAND_COLORS.border}`,
        borderRadius: 10,
        padding: "12px 24px",
        fontFamily: "monospace",
        fontSize: 14,
        color: BRAND_COLORS.accentSoft,
        textAlign: "center",
        whiteSpace: "nowrap",
      }}>
        <span style={{ color: BRAND_COLORS.textMuted }}>POST /sessions/{"{"}{"}"}id{"}"}/events  </span>
        {`{ "style_id": "${style.id}", "event_type": "click" }`}
      </div>

      {/* Event tags */}
      <div style={{
        position: "absolute", bottom: 60, left: "50%",
        transform: "translateX(-50%)",
        opacity: tagOpacity,
        display: "flex", gap: 12,
      }}>
        {["click", "view_detail", "like"].map((t, i) => (
          <div key={i} style={{
            background: i === 0 ? `${BRAND_COLORS.accent}30` : BRAND_COLORS.card,
            border: `1px solid ${i === 0 ? BRAND_COLORS.accent : BRAND_COLORS.border}`,
            borderRadius: 6, padding: "4px 12px",
            fontSize: 12, color: i === 0 ? BRAND_COLORS.accent : BRAND_COLORS.textMuted,
          }}>{t}</div>
        ))}
      </div>
    </div>
  );
};
