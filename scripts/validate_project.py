#!/usr/bin/env python3
"""Validate artifact counts and release gates without changing the project."""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path

from PIL import Image


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    failures: list[str] = []
    warnings: list[str] = []

    required = [
        "project.json",
        "storyboards/production-storyboard.json",
        "storyboards/frame-manifest.json",
        "voice/voiceover_manifest.json",
        "captions/caption-manifest.json",
    ]
    for relative in required:
        if not (root / relative).exists():
            failures.append(f"missing:{relative}")
    if failures:
        print(json.dumps({"passed": False, "failures": failures, "warnings": warnings}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    project = load(root / "project.json")
    frames = load(root / "storyboards/frame-manifest.json")["frames"]
    voice = load(root / "voice/voiceover_manifest.json")
    captions = load(root / "captions/caption-manifest.json")
    canvas = project["settings"]["canvas"]
    expected_size = (int(canvas["width"]), int(canvas["height"]))
    allowed_styles = {"warm-xuan-vox", "american-comic-vox"}
    visual_style = project["settings"].get("visual_style")
    if visual_style not in allowed_styles:
        failures.append(f"unsupported-visual-style:{visual_style}")
    if project["settings"].get("image_provider") != "APIMart gpt-image-2 1K independent single-image generation":
        warnings.append("image-provider-deviates-from-workflow-default")

    for frame in frames:
        frame_id = frame["frame_id"]
        image_path = root / "assets/backgrounds" / f"{frame_id}.png"
        if not image_path.exists():
            failures.append(f"missing-image:{frame_id}")
            continue
        with Image.open(image_path) as image:
            if image.size != expected_size:
                failures.append(f"bad-image-size:{frame_id}:{image.size}")

    shot_ids = [shot["shot_id"] for shot in project["shots"]]
    voice_ids = [shot["shot_id"] for shot in voice["shots"]]
    if shot_ids != voice_ids:
        failures.append("voice-shot-order-mismatch")
    for shot in voice["shots"]:
        alignment = root / "voice" / shot["alignment_file"]
        if not alignment.exists():
            failures.append(f"missing-alignment:{shot['shot_id']}")

    cue_end = 0.0
    for cue in captions["cues"]:
        start = float(cue["start_seconds"])
        end = float(cue["end_seconds"])
        if start < cue_end - 0.001:
            failures.append(f"caption-overlap:{cue['text']}")
        if end <= start:
            failures.append(f"caption-duration:{cue['text']}")
        if any(unicodedata.category(char).startswith("P") for char in cue["text"]):
            failures.append(f"caption-punctuation:{cue['text']}")
        cue_end = end
        overlay = root / "captions" / cue["overlay_file"]
        if not overlay.exists():
            failures.append(f"missing-caption-overlay:{overlay.name}")
    voice_end = float(voice["combined_wav_duration_seconds"])
    if abs(cue_end - voice_end) > 0.25:
        failures.append(f"caption-end-mismatch:{cue_end}:{voice_end}")

    if not project["voice"].get("voice_id") or not project["voice"].get("model_id"):
        failures.append("voice-configuration-missing")
    if project["voice"]["voice_id"] != voice["voice_id"] or project["voice"]["model_id"] != voice["model_id"]:
        failures.append("voice-identity-mismatch")
    if project["settings"]["production_mode"] != "static-infographic":
        warnings.append("production-mode-is-not-static-infographic")

    report = {
        "passed": not failures,
        "metrics": {
            "shots": len(shot_ids),
            "frames": len(frames),
            "captions": len(captions["cues"]),
            "voice_duration_seconds": voice_end,
            "canvas": expected_size,
            "visual_style": visual_style,
        },
        "failures": failures,
        "warnings": warnings,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
