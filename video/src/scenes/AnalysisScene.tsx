import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { BRAND_COLORS, DEMO_HAND } from "../constants";
import { globalStyle } from "../theme";

const METRICS = [
  { label: "手型", value: DEMO_HAND.shape, icon: "✋", color: BRAND_COLORS.accent },
  { label: "肤色", value: DEMO_HAND.skin_tone, icon: "🎨", color: "#c08060" },
  { label: "色调", value: DEMO_HAND.undertone, icon: "🌡️", color: "#e0a040" },
  { label: "手指比例", value: "0.72  (纤细)", icon: "📏", color: BRAND_COLORS.success },
  { label: "关节显露度", value: "低  (光滑)", icon: "💎", color: BRAND_COLORS.pink },
];

export const AnalysisScene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const fadeIn = interpolate(f, [0, 20], [0, 1]);
  const exitOpacity = interpolate(f, [duration - 20, duration], [1, 0]);

  return (
    <div style={{ ...globalStyle, opacity: exitOpacity }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 70% 50%, #0d1220 0%, ${BRAND_COLORS.bg} 65%)`,
      }} />

      {/* Title */}
      <div style={{
        position: "absolute", left: 120, top: 120,
        opacity: fadeIn,
      }}>
        <div style={{ fontSize: 13, letterSpacing: "0.3em", color: BRAND_COLORS.accent, textTransform: "uppercase" }}>Step 2</div>
        <div style={{ fontSize: 52, fontWeight: 700, color: BRAND_COLORS.text, lineHeight: 1.15, marginTop: 8 }}>
          手部智能分析
        </div>
        <div style={{ fontSize: 18, color: BRAND_COLORS.textMuted, marginTop: 12 }}>
          MediaPipe 关键点检测 · 皮肤色彩科学算法
        </div>
      </div>

      {/* Hand silhouette placeholder */}
      <div style={{
        position: "absolute", left: 120, top: 240,
        opacity: fadeIn,
      }}>
        <div style={{
          width: 280, height: 380,
          borderRadius: 20,
          background: BRAND_COLORS.surface,
          border: `1px solid ${BRAND_COLORS.border}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 80,
          position: "relative",
          overflow: "hidden",
        }}>
          🖐
          {/* Landmark dots overlay */}
          {[
            [140, 60], [80, 100], [60, 160], [70, 220], [100, 270],
            [140, 290], [180, 270], [200, 210], [195, 150], [185, 95],
            [140, 130], [130, 185], [135, 230], [155, 265],
          ].map(([x, y], i) => (
            <div key={i} style={{
              position: "absolute", left: x, top: y,
              width: 8, height: 8, borderRadius: "50%",
              background: BRAND_COLORS.accent,
              opacity: interpolate(f, [20 + i * 3, 35 + i * 3], [0, 0.85], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            }} />
          ))}
          {/* Scan line */}
          <div style={{
            position: "absolute", left: 0, right: 0,
            top: `${interpolate(f, [5, 55], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}%`,
            height: 2,
            background: `linear-gradient(90deg, transparent, ${BRAND_COLORS.accent}80, transparent)`,
            opacity: interpolate(f, [5, 10, 55, 60], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }} />
        </div>
        <div style={{ fontSize: 12, color: BRAND_COLORS.textMuted, textAlign: "center", marginTop: 8, fontFamily: "monospace" }}>
          21 landmark points detected
        </div>
      </div>

      {/* Metric cards */}
      <div style={{
        position: "absolute", right: 120, top: "50%",
        transform: "translateY(-50%)",
        display: "flex", flexDirection: "column", gap: 14,
        width: 580,
      }}>
        {METRICS.map((m, i) => {
          const cardOpacity = interpolate(f, [25 + i * 12, 45 + i * 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const cardX = interpolate(f, [25 + i * 12, 45 + i * 12], [40, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              background: BRAND_COLORS.card,
              border: `1px solid ${BRAND_COLORS.border}`,
              borderLeft: `3px solid ${m.color}`,
              borderRadius: 12,
              padding: "14px 20px",
              display: "flex",
              alignItems: "center",
              gap: 16,
              opacity: cardOpacity,
              transform: `translateX(${cardX}px)`,
            }}>
              <span style={{ fontSize: 24 }}>{m.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: BRAND_COLORS.textMuted, letterSpacing: "0.05em" }}>{m.label}</div>
                <div style={{ fontSize: 18, color: BRAND_COLORS.text, fontWeight: 600, marginTop: 2 }}>{m.value}</div>
              </div>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: m.color, boxShadow: `0 0 8px ${m.color}` }} />
            </div>
          );
        })}

        {/* API tag */}
        <div style={{
          marginTop: 8, textAlign: "right", fontSize: 12,
          color: BRAND_COLORS.textMuted, fontFamily: "monospace",
          opacity: interpolate(f, [100, 115], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}>
          GET /hand/analyze → HandProfile JSON
        </div>
      </div>
    </div>
  );
};
