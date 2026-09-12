import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, staticFile} from 'remotion';
import timelineData from '../../storyboards/timeline.json';
import captionData from '../../captions/caption-manifest.json';
import projectData from '../../project.json';

type TimelineEntry = {
  type: 'image' | 'endcard' | 'black';
  frame_id: string;
  asset_file?: string;
  start_frame: number;
  duration_frames: number;
  episode?: string;
  next_title?: string;
};

type CaptionCue = {
  start_seconds: number;
  end_seconds: number;
  overlay_file: string;
};

const entries = timelineData.entries as TimelineEntry[];
const cues = captionData.cues as CaptionCue[];
const showCaptions = projectData.settings?.subtitle_mode !== 'none';

const EndCard: React.FC<{entry: TimelineEntry}> = ({entry}) => (
  <AbsoluteFill
    style={{
      backgroundColor: '#0a0807',
      color: '#e7d8bd',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'Songti SC, STSong, serif',
      textAlign: 'center',
    }}
  >
    <div style={{border: '8px solid #9c2f20', padding: '34px 46px', color: '#b43b28', fontSize: 88}}>
      {entry.episode ?? 'END'}
    </div>
    <div style={{fontSize: 72, letterSpacing: 8, marginTop: 72}}>本集完</div>
    {entry.next_title ? <div style={{fontSize: 54, marginTop: 58}}>下集　{entry.next_title}</div> : null}
  </AbsoluteFill>
);

export const Episode: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: '#000'}}>
    {entries.map((entry) => (
      <Sequence key={entry.frame_id} from={entry.start_frame} durationInFrames={entry.duration_frames}>
        {entry.type === 'image' && entry.asset_file ? (
          <Img src={staticFile(entry.asset_file)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        ) : null}
        {entry.type === 'endcard' ? <EndCard entry={entry} /> : null}
        {entry.type === 'black' ? <AbsoluteFill style={{backgroundColor: '#000'}} /> : null}
      </Sequence>
    ))}
    <Audio src={staticFile('audio/voiceover_full_48k.wav')} />
    <Audio src={staticFile('audio/bed.wav')} />
    {showCaptions ? cues.map((cue, index) => {
      const start = Math.round(cue.start_seconds * timelineData.fps);
      const end = Math.round(cue.end_seconds * timelineData.fps);
      return (
        <Sequence key={index} from={start} durationInFrames={Math.max(1, end - start)}>
          <Img src={staticFile(`captions/${cue.overlay_file.split('/').pop()}`)} style={{width: '100%', height: '100%'}} />
        </Sequence>
      );
    }) : null}
  </AbsoluteFill>
);
