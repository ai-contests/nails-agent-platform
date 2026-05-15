import React from "react";
import { Composition } from "remotion";
import { NailsTryOnDemo } from "./NailsTryOnDemo";
import { DEMO_PROPS, TOTAL_FRAMES, FPS } from "./constants";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="NailsTryOnDemo"
        component={NailsTryOnDemo}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={DEMO_PROPS}
      />
    </>
  );
};
