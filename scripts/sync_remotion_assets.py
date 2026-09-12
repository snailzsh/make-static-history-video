#!/usr/bin/env python3
"""Copy only canonical approved media into the Remotion public bundle."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def copy(source: Path, target: Path) -> None:
    if not source.exists():
        raise SystemExit(f"Missing source: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    public = root / "remotion/public"
    project = load(root / "project.json")
    frames = load(root / "storyboards/frame-manifest.json")["frames"]
    captions = load(root / "captions/caption-manifest.json")
    voice = load(root / "voice/voiceover_manifest.json")

    for frame in frames:
        frame_id = frame["frame_id"]
        copy(root / "assets/backgrounds" / f"{frame_id}.png", public / "frames" / f"{frame_id}.png")
    subtitle_mode = project["settings"].get("subtitle_mode", "rendered")
    rendered_caption_count = 0
    if subtitle_mode == "rendered":
        for cue in captions["cues"]:
            source = root / "captions" / cue["overlay_file"]
            copy(source, public / "captions" / source.name)
            rendered_caption_count += 1
    copy(root / "voice" / voice["combined_wav"], public / "audio/voiceover_full_48k.wav")
    copy(root / "audio/music/bed.wav", public / "audio/bed.wav")
    print(json.dumps({"frames": len(frames), "caption_cues": len(captions["cues"]), "rendered_captions": rendered_caption_count, "subtitle_mode": subtitle_mode, "public": str(public)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
