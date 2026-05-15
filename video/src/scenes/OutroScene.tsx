import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { BRAND_COLORS } from "../constants";
import { globalStyle } from "../theme";

const STACK = [
  { label: "FastAPI", desc: "REST API · 10+ endpoints", icon: "⚡" },
  { label: "MediaPipe", desc: "手部关键点 · 肤色识别", icon: "🤖" },
  { label: "SQLite + FTS5", desc: "会话状态 · 推荐快照", icon: "🗄️" },
  { label: "ComfyUI", desc: "FLUX.2 [klein] 试戴生成", icon: "🎨" },
  { label: "Streamlit", desc: "商家端 + 消费者端 UI", icon: "💻" },
  { label: "Caddy", desc: "反向代理 · /user/ 路由", icon: "🔀" },
];

export const OutroScene: React.FC<{ startFrame: number; duration: number }> = ({
  startFrame,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - startFrame;
  if (f < 0 || f >= duration) return null;

  const fadeIn = interpolate(f, [0, 25], [0, 1]);

  return (
    <div style={{ ...globalStyle }}>
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at 50% 50%, #180e20 0%, ${BRAND_COLORS.bg} 65%)`,
        opacity: fadeIn,
      }} />

      {/* Decorative dots */}
      {Array.from({ length: 20 }).map((_, i) => (
        <div key={i} style={{
          position: "absolute",
          left: `${(i * 47) % 100}%`, top: `${(i * 37) % 100}%`,
          width: 3, height: 3, borderRadius: "50%",
          background: BRAND_COLORS.accent,
          opacity: 0.2 + (i % 4) * 0.1,
        }} />
      ))}

      {/* Title */}
      <div style={{
        position: "absolute", top: 90, left: 0, right: 0, textAlign: "center",
        opacity: fadeIn,
      }}>
        <div style={{
          fontSize: 58, fontWeight: 800,
          background: `linear-gradient(135deg, ${BRAND_COLORS.accent}, ${BRAND_COLORS.pink})`,
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        }}>
          技术栈总览
        </div>
        <div style={{ fontSize: 18, color: BRAND_COLORS.textMuted, marginTop: 10 }}>
          nails-agent-platform · demo_v1 整合完成
        </div>
      </div>

      {/* Stack grid */}
      <div style={{
        position: "absolute", left: "50%", top: "54%",
        transform: "translate(-50%, -50%)",
        display: "grid", gridTemplateColumns: "repeat(3, 260px)", gap: 18,
      }}>
        {STACK.map((item, i) => {
          const delay = 20 + i * 10;
          const cardOpacity = interpolate(f, [delay, delay + 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const cardY = interpolate(f, [delay, delay + 15], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              background: BRAND_COLORS.card,
              border: `1px solid ${BRAND_COLORS.border}`,
              borderRadius: 14,
              padding: "18px 20px",
              opacity: cardOpacity,
              transform: `translateY(${cardY}px)`,
            }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>{item.icon}</div>
              <div style={{ fontSize: 17, fontWeight: 700, color: BRAND_COLORS.text }}>{item.label}</div>
              <div style={{ fontSize: 13, color: BRAND_COLORS.textMuted, marginTop: 4 }}>{item.desc}</div>
            </div>
          );
        })}
      </div>

      {/* Bottom CTA */}
      <div style={{
        position: "absolute", bottom: 70, left: 0, right: 0, textAlign: "center",
        opacity: interpolate(f, [75, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        <div style={{
          display: "inline-block",
          background: `linear-gradient(135deg, ${BRAND_COLORS.accent}, ${BRAND_COLORS.pink})`,
          borderRadius: 40,
          padding: "12px 40px",
          fontSize: 18, fontWeight: 700, color: "#000",
          letterSpacing: "0.05em",
        }}>
          ./scripts/dev.sh  →  http://localhost:8080/user/
        </div>
      </div>
    </div>
  );
};
