import React from "react";
import { AbsoluteFill } from "remotion";
import { SCENE_START, SCENE_DURATIONS } from "./constants";
import { IntroScene } from "./scenes/IntroScene";
import { UploadScene } from "./scenes/UploadScene";
import { AnalysisScene } from "./scenes/AnalysisScene";
import { Round1Scene } from "./scenes/Round1Scene";
import { InteractionScene } from "./scenes/InteractionScene";
import { Round2Scene } from "./scenes/Round2Scene";
import { TryOnScene } from "./scenes/TryOnScene";
import { OutroScene } from "./scenes/OutroScene";

export const NailsTryOnDemo: React.FC<{ apiBaseUrl: string }> = () => {
  return (
    <AbsoluteFill style={{ background: "#0a0a0f" }}>
      <IntroScene startFrame={SCENE_START.intro} duration={SCENE_DURATIONS.intro} />
      <UploadScene startFrame={SCENE_START.upload} duration={SCENE_DURATIONS.upload} />
      <AnalysisScene startFrame={SCENE_START.analysis} duration={SCENE_DURATIONS.analysis} />
      <Round1Scene startFrame={SCENE_START.round1} duration={SCENE_DURATIONS.round1} />
      <InteractionScene startFrame={SCENE_START.interaction} duration={SCENE_DURATIONS.interaction} />
      <Round2Scene startFrame={SCENE_START.round2} duration={SCENE_DURATIONS.round2} />
      <TryOnScene startFrame={SCENE_START.tryon} duration={SCENE_DURATIONS.tryon} />
      <OutroScene startFrame={SCENE_START.outro} duration={SCENE_DURATIONS.outro} />
    </AbsoluteFill>
  );
};
