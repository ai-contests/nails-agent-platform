export const FPS = 30;

// Scene durations in frames
export const SCENE_DURATIONS = {
  intro: 90,       // 3s – logo + tagline
  upload: 90,      // 3s – drag hand photo
  analysis: 120,   // 4s – hand analysis results
  round1: 150,     // 5s – 9 style cards slide in
  interaction: 90, // 3s – user clicks a style card
  round2: 150,     // 5s – updated recommendations
  tryon: 150,      // 5s – try-on result reveal
  outro: 90,       // 3s – call to action
} as const;

export const TOTAL_FRAMES = Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0);

// Scene start frames (computed)
export const SCENE_START: Record<string, number> = (() => {
  const keys = Object.keys(SCENE_DURATIONS) as (keyof typeof SCENE_DURATIONS)[];
  const result: Record<string, number> = {};
  let acc = 0;
  for (const k of keys) {
    result[k] = acc;
    acc += SCENE_DURATIONS[k];
  }
  return result;
})();

export const BRAND_COLORS = {
  bg: "#0a0a0f",
  surface: "#13131a",
  card: "#1c1c28",
  accent: "#c9a96e",    // gold
  accentSoft: "#e8d5b0",
  pink: "#f0a3c0",
  text: "#f4f1ec",
  textMuted: "#8a8a9a",
  border: "#2a2a3a",
  success: "#5ec49a",
};

// Demo data – styles that will appear in the video
export const DEMO_STYLES = [
  { id: "STYLE001", title: "酒红金线方格甲", color: "#8B1A1A", accent: "#c9a96e", score: 100 },
  { id: "STYLE002", title: "酒红鎏金短甲",  color: "#7a1515", accent: "#d4af37", score: 94 },
  { id: "STYLE003", title: "黑曜星芒裸透甲", color: "#1a1a2e", accent: "#9090c0", score: 88 },
  { id: "STYLE004", title: "香槟碎钻长甲",  color: "#c8b89a", accent: "#ffffff", score: 82 },
  { id: "STYLE005", title: "裸透蝴蝶钻饰甲", color: "#e8d5c4", accent: "#f0c8e0", score: 76 },
  { id: "STYLE006", title: "浓郁玫瑰红甲",  color: "#c0305a", accent: "#ff8090", score: 70 },
];

export const DEMO_HAND = {
  shape: "方形 (Square)",
  skin_tone: "自然色 (Medium)",
  undertone: "暖调 (Warm)",
};

export const DEMO_PROPS = {
  apiBaseUrl: "http://localhost:8000",
};
