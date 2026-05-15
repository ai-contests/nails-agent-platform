# Nails AI — Remotion Video Demo

31-second product demo video showcasing the consumer nail try-on flow, built with [Remotion](https://remotion.dev).

## Scenes

| Scene | Duration | Frame range | Description |
|---|---|---|---|
| Intro | 3s | 0–89 | Logo + tagline fade-in with decorative rings |
| Upload | 3s | 90–179 | File drop zone + upload progress animation |
| Analysis | 4s | 180–299 | MediaPipe landmark scan + metric cards |
| Round 1 | 5s | 300–449 | 6 style cards spring in with match scores |
| Interaction | 3s | 450–539 | Animated cursor click + behavior event log |
| Round 2 | 5s | 540–689 | Before/After re-rank comparison |
| Try-on | 5s | 690–839 | ComfyUI generation wipe reveal |
| Outro | 3s | 840–929 | Tech stack grid + CTA |

## Commands

```bash
# Install
npm install

# Open Remotion Studio (browser-based scrubber)
npm start

# Render full MP4 (requires Chrome Headless Shell, downloaded on first run)
npm run build
# → out/demo.mp4

# Render a single frame
npx remotion still src/index.ts NailsTryOnDemo out/snapshot.png --frame=60
```

## Customizing

- **Scene timing** — edit `src/constants.ts` → `SCENE_DURATIONS`
- **Brand colors** — edit `src/constants.ts` → `BRAND_COLORS`
- **Style data** — edit `src/constants.ts` → `DEMO_STYLES`
- **Add a new scene** — create `src/scenes/MyScene.tsx`, import in `NailsTryOnDemo.tsx`, add to `SCENE_DURATIONS`
