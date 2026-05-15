import { BRAND_COLORS } from "./constants";

export const globalStyle = {
  fontFamily:
    "'PingFang SC', 'Noto Sans SC', 'Helvetica Neue', Arial, sans-serif",
  background: BRAND_COLORS.bg,
  color: BRAND_COLORS.text,
  width: "100%",
  height: "100%",
  overflow: "hidden",
  position: "absolute" as const,
  top: 0,
  left: 0,
};

export function lerp(a: number, b: number, t: number) {
  return a + (b - a) * Math.min(Math.max(t, 0), 1);
}

export function easeOut(t: number) {
  return 1 - Math.pow(1 - t, 3);
}

export function easeInOut(t: number) {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}
