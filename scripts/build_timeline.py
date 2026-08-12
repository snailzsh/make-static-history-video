#!/usr/bin/env python3
"""Build a frame-accurate static edit timeline from voice character alignment."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def word_time(root: Path, voice_shot: dict, word: str) -> float:
    alignment = load(root / "voice" / voice_shot["alignment_file"])["alignment"]
    text = "".join(alignment["characters"])
    index = text.index(word)
    return float(voice_shot["timeline_start_seconds"]) + float(alignment["character_start_times_seconds"][index])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    project = load(root / "project.json")
    frame_manifest = load(root / "storyboards/frame-manifest.json")
    voice = load(root / "voice/voiceover_manifest.json")
    fps = int(project["settings"]["fps"])
    canvas = project["settings"]["canvas"]
    shots = {shot["shot_id"]: shot for shot in voice["shots"]}

    entries: list[dict] = []
    same_anchor_offsets: dict[tuple[str, str], float] = {}
    for frame in frame_manifest["frames"]:
        voice_shot = shots[frame["shot_id"]]
        anchor_word = frame.get("anchor_word")
        if anchor_word:
            key = (frame["shot_id"], anchor_word)
            base = word_time(root, voice_shot, anchor_word)
            start = base + same_anchor_offsets.get(key, 0.0)
            same_anchor_offsets[key] = same_anchor_offsets.get(key, 0.0) + float(frame.get("hold_seconds", 0.0))
        else:
            start = float(voice_shot["timeline_start_seconds"])
        entries.append(
            {
                "type": "image",
                "shot_id": frame["shot_id"],
                "frame_id": frame["frame_id"],
                "asset_file": f"frames/{frame['frame_id']}.png",
                "start_seconds": round(start, 6),
                "end_seconds": None,
            }
        )

    entries.sort(key=lambda item: item["start_seconds"])
    total = float(voice["combined_wav_duration_seconds"])
    for index, entry in enumerate(entries):
        next_start = entries[index + 1]["start_seconds"] if index + 1 < len(entries) else total
        frame = next(frame for frame in frame_manifest["frames"] if frame["frame_id"] == entry["frame_id"])
        hold = float(frame.get("hold_seconds", 0.0))
        entry["end_seconds"] = round(min(next_start, entry["start_seconds"] + hold) if hold else next_start, 6)

    ending = project.get("ending")
    if ending:
        after = next(item for item in entries if item["frame_id"] == ending["after_frame"])
        endcard_start = float(after["end_seconds"])
        voice_shot = shots[after["shot_id"]]
        black_word = ending.get("black_on_word")
        black_start = word_time(root, voice_shot, black_word) if black_word else total
        entries.append(
            {
                "type": "endcard",
                "shot_id": after["shot_id"],
                "frame_id": "ENDCARD",
                "start_seconds": round(endcard_start, 6),
                "end_seconds": round(black_start, 6),
                "episode": str(ending.get("episode", "")),
                "next_title": ending.get("next_title", ""),
            }
        )
        if black_start < total:
            entries.append(
                {
                    "type": "black",
                    "shot_id": after["shot_id"],
                    "frame_id": "BLACK_END",
                    "start_seconds": round(black_start, 6),
                    "end_seconds": total,
                }
            )

    entries.sort(key=lambda item: item["start_seconds"])
    for current, following in zip(entries, entries[1:]):
        if current["end_seconds"] < following["start_seconds"]:
            current["end_seconds"] = following["start_seconds"]
        elif current["end_seconds"] > following["start_seconds"]:
            current["end_seconds"] = following["start_seconds"]

    duration_frames = math.ceil(total * fps)
    for entry in entries:
        entry["start_frame"] = round(entry["start_seconds"] * fps)
        entry["end_frame"] = round(entry["end_seconds"] * fps)
        entry["duration_frames"] = max(1, entry["end_frame"] - entry["start_frame"])
    entries[-1]["end_frame"] = duration_frames
    entries[-1]["duration_frames"] = duration_frames - entries[-1]["start_frame"]

    payload = {
        "schema_version": 1,
        "width": int(canvas["width"]),
        "height": int(canvas["height"]),
        "fps": fps,
        "duration_seconds": total,
        "duration_frames": duration_frames,
        "timing_source": "ElevenLabs character alignment",
        "entries": entries,
    }
    target = root / "storyboards/timeline.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
