import React from "react";
import { useCurrentFrame, spring, useVideoConfig, interpolate } from "remotion";
import { BRAND_COLORS } from "../constants";
import { globalStyle } from "../theme";

export const IntroScene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const logoScale = spring({ frame: f, fps, config: { damping: 14, stiffness: 120 }, from: 0.6, to: 1 });
  const logoOpacity = interpolate(f, [0, 20], [0, 1]);
  const taglineOpacity = interpolate(f, [30, 60], [0, 1]);
  const taglineY = interpolate(f, [30, 60], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitOpacity = interpolate(f, [duration - 20, duration], [1, 0]);

  return (
    <div style={{ ...globalStyle, opacity: exitOpacity }}>
      {/* Background gradient */}
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 50% 40%, #1a1020 0%, ${BRAND_COLORS.bg} 70%)`,
      }} />

      {/* Decorative rings */}
      {[320, 480, 640].map((r, i) => (
        <div key={i} style={{
          position: "absolute",
          left: "50%", top: "42%",
          width: r, height: r,
          borderRadius: "50%",
          border: `1px solid ${BRAND_COLORS.accent}${20 - i * 5}`,
          transform: "translate(-50%, -50%)",
          opacity: 0.4 - i * 0.1,
        }} />
      ))}

      {/* Logo */}
      <div style={{
        position: "absolute", left: "50%", top: "38%",
        transform: `translate(-50%, -50%) scale(${logoScale})`,
        opacity: logoOpacity,
        textAlign: "center",
      }}>
        <div style={{
          fontSize: 88,
          fontWeight: 700,
          letterSpacing: "0.05em",
          background: `linear-gradient(135deg, ${BRAND_COLORS.accent}, ${BRAND_COLORS.accentSoft}, ${BRAND_COLORS.pink})`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          lineHeight: 1.1,
        }}>
          NAILS AI
        </div>
        <div style={{
          fontSize: 20,
          letterSpacing: "0.4em",
          color: BRAND_COLORS.textMuted,
          marginTop: 8,
          textTransform: "uppercase",
        }}>
          智能美甲试戴平台
        </div>
      </div>

      {/* Tagline */}
      <div style={{
        position: "absolute", left: "50%", top: "62%",
        transform: `translate(-50%, ${taglineY}px)`,
        opacity: taglineOpacity,
        textAlign: "center",
        width: 700,
      }}>
        <div style={{ fontSize: 26, color: BRAND_COLORS.accentSoft, fontWeight: 300 }}>
          上传手部照片 · AI 识别手型肤色 · 个性化推荐
        </div>
        <div style={{
          marginTop: 16,
          fontSize: 16,
          color: BRAND_COLORS.textMuted,
          letterSpacing: "0.05em",
        }}>
          Powered by MediaPipe · FastAPI · ComfyUI
        </div>
      </div>
    </div>
  );
};
