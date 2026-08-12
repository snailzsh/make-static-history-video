import React from 'react';
import {Composition} from 'remotion';
import timeline from '../../storyboards/timeline.json';
import {Episode} from './Episode';

export const Root: React.FC = () => (
  <Composition
    id="StaticHistoryInfographic"
    component={Episode}
    width={timeline.width}
    height={timeline.height}
    fps={timeline.fps}
    durationInFrames={timeline.duration_frames}
  />
);
