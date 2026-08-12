#!/usr/bin/env python3
"""Generate a quiet rights-clear procedural documentary bed for the full timeline."""

from __future__ import annotations

import argparse
import json
import math
import wave
from pathlib import Path

import numpy as np


RATE = 48_000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--seed", type=int, default=202)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    timeline = json.loads((root / "storyboards/timeline.json").read_text(encoding="utf-8"))
    duration = timeline["duration_frames"] / timeline["fps"]
    rng = np.random.default_rng(args.seed)
    notes = np.array([73.42, 82.41, 98.00, 110.00, 123.47, 146.83])
    events = []
    event_time = 7.0
    index = 0
    while event_time < duration - 2:
        events.append((event_time, float(notes[index % len(notes)])))
        index += 1
        event_time += float(rng.uniform(7.5, 12.0))

    target = root / "audio/music/bed.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    total_samples = math.ceil(duration * RATE)
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        for block_start in range(0, total_samples, RATE):
            count = min(RATE, total_samples - block_start)
            time = (block_start + np.arange(count, dtype=np.float64)) / RATE
            mono = 0.014 * np.sin(2 * np.pi * 55.0 * time)
            mono += 0.009 * np.sin(2 * np.pi * 82.5 * time + 0.4)
            left = mono.copy()
            right = mono.copy()
            block_begin = block_start / RATE
            block_end = (block_start + count) / RATE
            for start, frequency in events:
                if start + 4 < block_begin or start > block_end:
                    continue
                delta = time - start
                active = (delta >= 0) & (delta <= 4)
                envelope = np.exp(-1.35 * delta[active])
                tone = np.sin(2 * np.pi * frequency * delta[active])
                tone += 0.4 * np.sin(2 * np.pi * frequency * 2.01 * delta[active] + 0.2)
                left[active] += 0.025 * tone * envelope
                right[active] += 0.02 * tone * envelope
            fade_in = np.clip(time / 2.5, 0, 1)
            fade_out = np.clip((duration - time) / 2.5, 0, 1)
            fade = np.minimum(fade_in, fade_out)
            stereo = np.column_stack((left * fade, right * fade))
            pcm = np.round(np.clip(np.tanh(stereo * 1.15) * 0.85, -1, 1) * 32767).astype("<i2")
            wav.writeframes(pcm.tobytes())
    print(target)


if __name__ == "__main__":
    main()
