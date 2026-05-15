import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { BRAND_COLORS, DEMO_STYLES } from "../constants";
import { globalStyle } from "../theme";

const REASON_TAGS = ["视觉相似", "同色系", "相似调色板", "冷暖接近", "偏好来源"];

export const Round2Scene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const exitOpacity = interpolate(f, [duration - 20, duration], [1, 0]);

  // Re-ranked order: 0, 2, 1, 4, 5, 3 (slightly shuffled to show learning)
  const reranked = [0, 2, 1, 4, 5, 3].map((i) => DEMO_STYLES[i]);

  return (
    <div style={{ ...globalStyle, opacity: exitOpacity }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 40% 60%, #0a1218 0%, ${BRAND_COLORS.bg} 70%)`,
      }} />

      {/* Title */}
      <div style={{
        position: "absolute", left: 120, top: 80,
        opacity: interpolate(f, [0, 20], [0, 1]),
      }}>
        <div style={{ fontSize: 13, letterSpacing: "0.3em", color: BRAND_COLORS.accent, textTransform: "uppercase" }}>Step 5</div>
        <div style={{ fontSize: 52, fontWeight: 700, color: BRAND_COLORS.text, lineHeight: 1.15, marginTop: 8 }}>
          第二轮推荐
        </div>
        <div style={{ fontSize: 17, color: BRAND_COLORS.textMuted, marginTop: 8 }}>
          融合行为偏好 · 视觉相似度重排序
        </div>
      </div>

      {/* Before → After comparison labels */}
      <div style={{
        position: "absolute", left: "50%", top: 210,
        transform: "translateX(-50%)",
        display: "flex", gap: 280, alignItems: "center",
        opacity: interpolate(f, [15, 35], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        <div style={{ fontSize: 13, color: BRAND_COLORS.textMuted, letterSpacing: "0.1em" }}>Round 1 排序</div>
        <div style={{ fontSize: 13, color: BRAND_COLORS.accent, letterSpacing: "0.1em", fontWeight: 600 }}>Round 2 重排 ↑</div>
      </div>

      {/* Comparison rows */}
      <div style={{
        position: "absolute", left: "50%", top: "55%",
        transform: "translate(-50%, -50%)",
        width: 900,
      }}>
        {DEMO_STYLES.slice(0, 4).map((origStyle, i) => {
          const newStyle = reranked[i];
          const rowOpacity = interpolate(f, [20 + i * 15, 40 + i * 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const rowX = interpolate(f, [20 + i * 15, 40 + i * 15], [-30, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const changed = origStyle.id !== newStyle.id;

          return (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 24,
              marginBottom: 16,
              opacity: rowOpacity,
              transform: `translateX(${rowX}px)`,
            }}>
              {/* Old */}
              <div style={{
                flex: 1, background: BRAND_COLORS.surface,
                border: `1px solid ${BRAND_COLORS.border}`,
                borderRadius: 10, padding: "10px 16px",
                display: "flex", alignItems: "center", gap: 12,
                opacity: 0.6,
              }}>
                <div style={{ width: 32, height: 32, borderRadius: 6, background: `linear-gradient(135deg, ${origStyle.color}, ${origStyle.accent})` }} />
                <span style={{ fontSize: 14, color: BRAND_COLORS.textMuted }}>{origStyle.title}</span>
                <span style={{ marginLeft: "auto", fontSize: 12, color: BRAND_COLORS.textMuted }}>#{i + 1}</span>
              </div>

              {/* Arrow */}
              <div style={{ fontSize: 20, color: changed ? BRAND_COLORS.accent : BRAND_COLORS.textMuted }}>
                {changed ? "→" : "→"}
              </div>

              {/* New */}
              <div style={{
                flex: 1, background: changed ? `${BRAND_COLORS.accent}14` : BRAND_COLORS.surface,
                border: `1.5px solid ${changed ? BRAND_COLORS.accent : BRAND_COLORS.border}`,
                borderRadius: 10, padding: "10px 16px",
                display: "flex", alignItems: "center", gap: 12,
              }}>
                <div style={{ width: 32, height: 32, borderRadius: 6, background: `linear-gradient(135deg, ${newStyle.color}, ${newStyle.accent})` }} />
                <span style={{ fontSize: 14, color: changed ? BRAND_COLORS.accentSoft : BRAND_COLORS.textMuted }}>{newStyle.title}</span>
                <span style={{ marginLeft: "auto", fontSize: 12, color: BRAND_COLORS.accent }}>#{i + 1}</span>
                {changed && <span style={{ fontSize: 10, background: `${BRAND_COLORS.accent}30`, color: BRAND_COLORS.accent, borderRadius: 4, padding: "2px 6px" }}>↑ 重排</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Reason tags */}
      <div style={{
        position: "absolute", bottom: 80, left: "50%",
        transform: "translateX(-50%)",
        display: "flex", gap: 10,
        opacity: interpolate(f, [100, 130], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        {REASON_TAGS.map((t, i) => (
          <div key={i} style={{
            background: BRAND_COLORS.card, border: `1px solid ${BRAND_COLORS.border}`,
            borderRadius: 20, padding: "5px 14px",
            fontSize: 12, color: BRAND_COLORS.accent,
          }}>{t}</div>
        ))}
      </div>

      {/* API */}
      <div style={{
        position: "absolute", bottom: 40, right: 120,
        fontSize: 12, color: BRAND_COLORS.textMuted, fontFamily: "monospace",
        opacity: interpolate(f, [100, 120], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        POST /sessions/{"{id}"}/recommendations/round2
      </div>
    </div>
  );
};
