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
    prompt_path = root / "prompts/frame-prompts.json"
    prompt_frames = {}
    if prompt_path.exists():
        prompt_frames = {
            row["frame_id"]: row
            for row in load(prompt_path).get("frames", [])
            if isinstance(row, dict) and row.get("frame_id")
        }
    else:
        failures.append("missing:prompts/frame-prompts.json")
    voice = load(root / "voice/voiceover_manifest.json")
    captions = load(root / "captions/caption-manifest.json")
    canvas = project["settings"]["canvas"]
    expected_size = (int(canvas["width"]), int(canvas["height"]))
    allowed_styles = {"warm-xuan-vox", "american-comic-vox", "knowledge-card", "qibaishi-xieyi"}
    visual_style = project["settings"].get("visual_style")
    if visual_style not in allowed_styles:
        failures.append(f"unsupported-visual-style:{visual_style}")
    if project["settings"].get("image_provider") != "APIMart gpt-image-2 1K independent single-image generation":
        warnings.append("image-provider-deviates-from-workflow-default")
    subtitle_mode = project["settings"].get("subtitle_mode", "rendered")
    if subtitle_mode not in {"rendered", "none"}:
        failures.append(f"unsupported-subtitle-mode:{subtitle_mode}")

    for frame in frames:
        frame_id = frame["frame_id"]
        if visual_style == "knowledge-card":
            prompt_frame = prompt_frames.get(frame_id)
            if prompt_frame is None:
                failures.append(f"missing-prompt-frame:{frame_id}")
            else:
                required_text = prompt_frame.get("required_text", [])
                text_plan = prompt_frame.get("text_plan", [])
                if not required_text:
                    failures.append(f"knowledge-card-required-text-empty:{frame_id}")
                if not text_plan:
                    failures.append(f"knowledge-card-text-plan-empty:{frame_id}")
                elif len(text_plan) < 3:
                    failures.append(f"knowledge-card-text-plan-too-small:{frame_id}")
                if prompt_frame.get("blank_text_containers_allowed") is not False:
                    failures.append(f"knowledge-card-blank-container-policy:{frame_id}")
                if not any(isinstance(item, dict) and item.get("role") == "main_title" for item in text_plan):
                    failures.append(f"knowledge-card-main-title-missing:{frame_id}")
                if any(not isinstance(item, dict) or not str(item.get("text", "")).strip() for item in text_plan):
                    failures.append(f"knowledge-card-empty-text-plan-item:{frame_id}")
                planned_text = {
                    item.get("text")
                    for item in text_plan
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                }
                missing = [text for text in required_text if text not in planned_text]
                if missing:
                    failures.append(f"knowledge-card-text-plan-missing:{frame_id}:{missing}")
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
    previous_voice_end = 0.0
    for shot in voice["shots"]:
        start = float(shot["timeline_start_seconds"])
        end = float(shot["timeline_end_seconds"])
        if start < previous_voice_end - 0.001:
            failures.append(f"voice-shot-overlap:{shot['shot_id']}:{start}:{previous_voice_end}")
        if end <= start:
            failures.append(f"voice-shot-duration:{shot['shot_id']}:{start}:{end}")
        previous_voice_end = max(previous_voice_end, end)

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
        if subtitle_mode == "rendered":
            overlay_file = cue.get("overlay_file")
            if not overlay_file:
                failures.append(f"missing-caption-overlay-field:{cue['text']}")
            else:
                overlay = root / "captions" / overlay_file
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

    approvals = project.get("approvals", {})
    continuity_report_path = root / "out/qa/voice-continuity-review.json"
    continuity_report = {}
    if continuity_report_path.exists():
        continuity_report = load(continuity_report_path)
    continuity_result = continuity_report.get("result")
    expected_joins = len(voice.get("chunk_joins", []))
    if expected_joins == 0 and len(voice.get("chunks", [])) > 1:
        expected_joins = len(voice["chunks"]) - 1
    passing_continuity_report = (
        continuity_result == "pass"
        and continuity_report.get("full_playback_reviewed") is True
        and continuity_report.get("chunk_joins_reviewed") == expected_joins
        and continuity_report.get("overlap_count") == 0
        and continuity_report.get("failure_timestamps", []) == []
    )
    if continuity_report_path.exists() and not passing_continuity_report:
        failures.append("voice-continuity-report-not-passing")
    if approvals.get("voice_continuity_passed") is True and not passing_continuity_report:
        failures.append("voice-continuity-approval-without-passing-report")
    if approvals.get("qc_passed") is True:
        if approvals.get("voice_continuity_passed") is not True:
            failures.append("qc-passed-without-voice-continuity-approval")
        if not passing_continuity_report:
            failures.append("qc-passed-without-passing-voice-continuity-report")
    if approvals.get("final_promotion") is True:
        if approvals.get("qc_passed") is not True:
            failures.append("final-promotion-without-qc-approval")
        if not passing_continuity_report:
            failures.append("final-promotion-without-passing-voice-continuity-report")

    report = {
        "passed": not failures,
        "metrics": {
            "shots": len(shot_ids),
            "frames": len(frames),
            "captions": len(captions["cues"]),
            "voice_duration_seconds": voice_end,
            "canvas": expected_size,
            "visual_style": visual_style,
            "subtitle_mode": subtitle_mode,
            "voice_continuity_result": continuity_result,
            "voice_chunk_joins": expected_joins,
        },
        "failures": failures,
        "warnings": warnings,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
