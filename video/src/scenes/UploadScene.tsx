import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { BRAND_COLORS } from "../constants";
import { globalStyle, easeOut } from "../theme";

export const UploadScene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const panelOpacity = interpolate(f, [0, 20], [0, 1]);
  const exitOpacity = interpolate(f, [duration - 20, duration], [1, 0]);

  // File "drop" animation at frame 30
  const fileScale = spring({ frame: Math.max(f - 30, 0), fps, config: { damping: 12, stiffness: 160 }, from: 0, to: 1 });
  const fileOpacity = interpolate(f, [30, 50], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const progressWidth = interpolate(f, [45, 80], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const doneOpacity = interpolate(f, [82, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{ ...globalStyle, opacity: exitOpacity }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 30% 50%, #12101a 0%, ${BRAND_COLORS.bg} 65%)`,
      }} />

      {/* Left: step label */}
      <div style={{
        position: "absolute", left: 120, top: 120,
        opacity: panelOpacity,
      }}>
        <div style={{ fontSize: 13, letterSpacing: "0.3em", color: BRAND_COLORS.accent, textTransform: "uppercase" }}>
          Step 1
        </div>
        <div style={{ fontSize: 52, fontWeight: 700, color: BRAND_COLORS.text, lineHeight: 1.15, marginTop: 8 }}>
          上传手部照片
        </div>
        <div style={{ fontSize: 18, color: BRAND_COLORS.textMuted, marginTop: 12, maxWidth: 360 }}>
          支持 JPG / PNG · AI 自动识别手型与肤色
        </div>

        {/* Feature list */}
        <div style={{ marginTop: 40 }}>
          {["手型分类（方形 / 圆形 / 尖形 / 椭圆形）", "肤色检测（5 个等级）", "冷暖色调识别"].map((t, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 12, marginBottom: 14,
              opacity: interpolate(f, [10 + i * 8, 30 + i * 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
              transform: `translateX(${interpolate(f, [10 + i * 8, 30 + i * 8], [-16, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
            }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: BRAND_COLORS.accent }} />
              <span style={{ fontSize: 16, color: BRAND_COLORS.accentSoft }}>{t}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Upload UI mockup */}
      <div style={{
        position: "absolute", right: 180, top: "50%",
        transform: "translateY(-50%)",
        opacity: panelOpacity,
      }}>
        {/* Upload drop zone */}
        <div style={{
          width: 440, height: 360,
          border: `2px dashed ${BRAND_COLORS.accent}60`,
          borderRadius: 16,
          background: BRAND_COLORS.surface,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          overflow: "hidden",
        }}>
          {/* Before drop */}
          <div style={{ opacity: interpolate(f, [28, 35], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), textAlign: "center" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🖐</div>
            <div style={{ fontSize: 18, color: BRAND_COLORS.textMuted }}>拖拽或点击上传</div>
            <div style={{ fontSize: 14, color: BRAND_COLORS.textMuted, marginTop: 6 }}>hand.jpg / hand.png</div>
          </div>

          {/* File card appearing */}
          <div style={{
            position: "absolute",
            transform: `scale(${fileScale})`,
            opacity: fileOpacity,
            background: BRAND_COLORS.card,
            border: `1px solid ${BRAND_COLORS.border}`,
            borderRadius: 12,
            padding: "16px 24px",
            width: 320,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
              <div style={{ fontSize: 28 }}>🖼️</div>
              <div>
                <div style={{ fontSize: 15, color: BRAND_COLORS.text }}>hand_photo.jpg</div>
                <div style={{ fontSize: 12, color: BRAND_COLORS.textMuted }}>2.3 MB · 2048×1536</div>
              </div>
            </div>
            {/* Progress bar */}
            <div style={{ background: BRAND_COLORS.border, borderRadius: 4, height: 6, overflow: "hidden" }}>
              <div style={{
                width: `${progressWidth}%`,
                height: "100%",
                background: `linear-gradient(90deg, ${BRAND_COLORS.accent}, ${BRAND_COLORS.pink})`,
                borderRadius: 4,
                transition: "width 0.1s linear",
              }} />
            </div>
            <div style={{ fontSize: 12, color: BRAND_COLORS.accent, marginTop: 6, opacity: doneOpacity }}>
              ✓ 上传完成，正在分析…
            </div>
          </div>
        </div>

        {/* API endpoint label */}
        <div style={{
          marginTop: 16, textAlign: "center",
          opacity: panelOpacity,
          fontSize: 13, color: BRAND_COLORS.textMuted,
          fontFamily: "monospace",
        }}>
          POST /sessions  ·  POST /hand/analyze
        </div>
      </div>
    </div>
  );
};
