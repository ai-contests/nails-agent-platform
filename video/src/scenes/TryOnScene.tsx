import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { BRAND_COLORS, DEMO_STYLES } from "../constants";
import { globalStyle } from "../theme";

export const TryOnScene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const exitOpacity = interpolate(f, [duration - 20, duration], [1, 0]);
  const style = DEMO_STYLES[0];

  // Reveal animation: wipe left→right at frame 40
  const wipeProgress = interpolate(f, [35, 85], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const resultScale = spring({ frame: Math.max(f - 80, 0), fps, config: { damping: 14, stiffness: 100 }, from: 0.85, to: 1 });
  const resultOpacity = interpolate(f, [80, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const loadingOpacity = interpolate(f, [0, 10, 34, 38], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const spinAngle = f * 6; // degrees

  return (
    <div style={{ ...globalStyle, opacity: exitOpacity }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 60% 40%, #0d1820 0%, ${BRAND_COLORS.bg} 65%)`,
      }} />

      {/* Title */}
      <div style={{
        position: "absolute", left: 120, top: 80,
        opacity: interpolate(f, [0, 20], [0, 1]),
      }}>
        <div style={{ fontSize: 13, letterSpacing: "0.3em", color: BRAND_COLORS.accent, textTransform: "uppercase" }}>Step 6</div>
        <div style={{ fontSize: 52, fontWeight: 700, color: BRAND_COLORS.text, lineHeight: 1.15, marginTop: 8 }}>
          AI 虚拟试戴
        </div>
        <div style={{ fontSize: 17, color: BRAND_COLORS.textMuted, marginTop: 8 }}>
          ComfyUI · FLUX.2 [klein] · 多参考图融合生成
        </div>
      </div>

      {/* Before / After comparison */}
      <div style={{
        position: "absolute", left: "50%", top: "56%",
        transform: "translate(-50%, -50%)",
        display: "flex", gap: 32, alignItems: "center",
      }}>
        {/* Before: hand */}
        <div style={{
          opacity: interpolate(f, [5, 25], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}>
          <div style={{
            width: 280, height: 360, borderRadius: 16,
            background: BRAND_COLORS.surface,
            border: `1px solid ${BRAND_COLORS.border}`,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            gap: 12,
          }}>
            <div style={{ fontSize: 72 }}>🖐</div>
            <div style={{ fontSize: 14, color: BRAND_COLORS.textMuted }}>裸手照片</div>
          </div>
          <div style={{ textAlign: "center", marginTop: 10, fontSize: 13, color: BRAND_COLORS.textMuted }}>参考图 1 · 手</div>
        </div>

        {/* Style reference */}
        <div style={{
          opacity: interpolate(f, [10, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}>
          <div style={{
            width: 180, height: 220, borderRadius: 16,
            background: `linear-gradient(135deg, ${style.color}, ${style.accent})`,
            border: `1px solid ${BRAND_COLORS.border}`,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            gap: 12,
          }}>
            <div style={{ fontSize: 56 }}>💅</div>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)" }}>{style.title}</div>
          </div>
          <div style={{ textAlign: "center", marginTop: 10, fontSize: 13, color: BRAND_COLORS.textMuted }}>参考图 2 · 款式</div>
        </div>

        {/* Arrow with loading */}
        <div style={{ textAlign: "center", position: "relative" }}>
          {/* Loading spinner */}
          <div style={{
            position: "absolute", left: "50%", top: "50%",
            transform: `translate(-50%, -50%) rotate(${spinAngle}deg)`,
            width: 50, height: 50,
            border: `3px solid ${BRAND_COLORS.border}`,
            borderTopColor: BRAND_COLORS.accent,
            borderRadius: "50%",
            opacity: loadingOpacity,
          }} />
          <div style={{
            fontSize: 36, color: BRAND_COLORS.accent,
            opacity: interpolate(f, [38, 50], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}>→</div>
          <div style={{
            fontSize: 12, color: BRAND_COLORS.textMuted, marginTop: 8,
            opacity: interpolate(f, [38, 50], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}>ComfyUI</div>
        </div>

        {/* Result */}
        <div style={{
          opacity: resultOpacity,
          transform: `scale(${resultScale})`,
        }}>
          <div style={{
            width: 280, height: 360, borderRadius: 16,
            background: `linear-gradient(145deg, ${style.color}88, ${style.accent}44, ${BRAND_COLORS.surface})`,
            border: `2px solid ${BRAND_COLORS.accent}`,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            gap: 12,
            boxShadow: `0 0 40px ${BRAND_COLORS.accent}40, 0 8px 32px rgba(0,0,0,0.5)`,
            position: "relative",
            overflow: "hidden",
          }}>
            {/* Shimmer overlay */}
            <div style={{
              position: "absolute", inset: 0,
              background: `linear-gradient(135deg, transparent 40%, ${BRAND_COLORS.accent}15 50%, transparent 60%)`,
              transform: `translateX(${interpolate(f, [80, 120], [-300, 300], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
            }} />
            <div style={{ fontSize: 72 }}>🖐💅</div>
            <div style={{
              fontSize: 14, color: BRAND_COLORS.accentSoft,
              background: `${BRAND_COLORS.accent}20`,
              padding: "4px 12px", borderRadius: 20,
            }}>试戴效果图</div>
          </div>
          <div style={{ textAlign: "center", marginTop: 10, fontSize: 13, color: BRAND_COLORS.accent }}>
            ✓ 生成完成 · 2.4s
          </div>
        </div>
      </div>

      {/* Wipe progress bar at bottom */}
      <div style={{
        position: "absolute", bottom: 60, left: 120,
        right: 120, height: 3,
        background: BRAND_COLORS.border, borderRadius: 2, overflow: "hidden",
        opacity: interpolate(f, [30, 45, 88, 95], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        <div style={{
          width: `${wipeProgress * 100}%`, height: "100%",
          background: `linear-gradient(90deg, ${BRAND_COLORS.accent}, ${BRAND_COLORS.pink})`,
        }} />
      </div>

      {/* Generating label */}
      <div style={{
        position: "absolute", bottom: 72, left: "50%", transform: "translateX(-50%)",
        fontSize: 12, color: BRAND_COLORS.textMuted, fontFamily: "monospace",
        opacity: interpolate(f, [35, 50, 82, 90], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        POST /sessions/{"{id}"}/tryon → ComfyUI → CDN URL
      </div>
    </div>
  );
};
