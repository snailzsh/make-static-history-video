#!/usr/bin/env python3
"""Verify that every static-image cut is frame-exact and decoder-friendly."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


SAMPLE_SIZE = (90, 160)


def run(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, check=True, capture_output=True)


def rms_difference(left: Image.Image, right: Image.Image) -> float:
    channels = ImageStat.Stat(ImageChops.difference(left, right)).rms
    return sum(channels) / len(channels)


def source_frame(root: Path, frame_id: str) -> Image.Image:
    path = root / "assets" / "backgrounds" / f"{frame_id}.png"
    with Image.open(path) as image:
        return image.convert("RGB").resize(SAMPLE_SIZE, Image.Resampling.LANCZOS)


def decoded_samples(candidate: Path, frame_numbers: list[int]) -> dict[int, Image.Image]:
    selected = sorted(set(frame_numbers))
    expression = "+".join(f"eq(n\\,{number})" for number in selected)
    result = run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(candidate),
            "-vf",
            f"select='{expression}',scale={SAMPLE_SIZE[0]}:{SAMPLE_SIZE[1]}:flags=lanczos",
            "-fps_mode",
            "passthrough",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ]
    )
    frame_size = SAMPLE_SIZE[0] * SAMPLE_SIZE[1] * 3
    actual = len(result.stdout) // frame_size
    if len(result.stdout) % frame_size or actual != len(selected):
        raise RuntimeError(f"decoded {actual} boundary samples, expected {len(selected)}")
    return {
        number: Image.frombytes(
            "RGB",
            SAMPLE_SIZE,
            result.stdout[index * frame_size : (index + 1) * frame_size],
        )
        for index, number in enumerate(selected)
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    root = args.project_root.expanduser().resolve()
    candidate = args.candidate
    if candidate is None:
        candidate = root / "out" / "candidates" / f"{root.name}-nosubs.mp4"
    elif not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not candidate.exists():
        raise SystemExit(f"candidate missing: {candidate}")

    timeline = json.loads((root / "storyboards" / "timeline.json").read_text(encoding="utf-8"))
    fps = int(timeline["fps"])
    entries = timeline["entries"]
    cuts = list(zip(entries, entries[1:]))

    discontinuities = [
        {
            "from": previous["frame_id"],
            "to": current["frame_id"],
            "previous_end_frame": int(previous["end_frame"]),
            "current_start_frame": int(current["start_frame"]),
        }
        for previous, current in cuts
        if int(previous["end_frame"]) != int(current["start_frame"])
    ]

    frame_probe = json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_frames",
                "-show_entries",
                "frame=best_effort_timestamp_time,key_frame",
                "-of",
                "json",
                str(candidate),
            ]
        ).stdout.decode("utf-8")
    )["frames"]
    timestamps = [float(frame["best_effort_timestamp_time"]) for frame in frame_probe]
    expected_step = 1.0 / fps
    tolerance = expected_step / 1000
    missing_keyframes: list[dict[str, object]] = []
    pts_discontinuities: list[dict[str, object]] = []
    for previous, current in cuts:
        cut_frame = int(current["start_frame"])
        if cut_frame >= len(frame_probe):
            missing_keyframes.append(
                {"from": previous["frame_id"], "to": current["frame_id"], "cut_frame": cut_frame, "reason": "out_of_range"}
            )
            continue
        if int(frame_probe[cut_frame].get("key_frame", 0)) != 1:
            missing_keyframes.append(
                {"from": previous["frame_id"], "to": current["frame_id"], "cut_frame": cut_frame}
            )
        step = timestamps[cut_frame] - timestamps[cut_frame - 1]
        if abs(step - expected_step) > tolerance:
            pts_discontinuities.append(
                {
                    "from": previous["frame_id"],
                    "to": current["frame_id"],
                    "cut_frame": cut_frame,
                    "actual_step_seconds": step,
                    "expected_step_seconds": expected_step,
                }
            )

    image_cuts = [
        (previous, current)
        for previous, current in cuts
        if previous["type"] == "image" and current["type"] == "image"
    ]
    sample_numbers = [
        number
        for _, current in image_cuts
        for number in (int(current["start_frame"]) - 1, int(current["start_frame"]))
    ]
    samples = decoded_samples(candidate, sample_numbers) if sample_numbers else {}
    visual_cut_results: list[dict[str, object]] = []
    bad_visual_swaps: list[dict[str, object]] = []
    for previous, current in image_cuts:
        cut_frame = int(current["start_frame"])
        before = samples[cut_frame - 1]
        after = samples[cut_frame]
        previous_source = source_frame(root, previous["frame_id"])
        current_source = source_frame(root, current["frame_id"])
        before_previous = rms_difference(before, previous_source)
        before_current = rms_difference(before, current_source)
        after_previous = rms_difference(after, previous_source)
        after_current = rms_difference(after, current_source)
        boundary_change = rms_difference(before, after)
        passed = (
            before_previous < before_current
            and after_current < after_previous
            and boundary_change >= 1.0
        )
        row = {
            "from": previous["frame_id"],
            "to": current["frame_id"],
            "cut_frame": cut_frame,
            "cut_seconds": cut_frame / fps,
            "passed": passed,
            "rms": {
                "before_to_previous": round(before_previous, 3),
                "before_to_current": round(before_current, 3),
                "after_to_previous": round(after_previous, 3),
                "after_to_current": round(after_current, 3),
                "before_to_after": round(boundary_change, 3),
            },
        }
        visual_cut_results.append(row)
        if not passed:
            bad_visual_swaps.append(row)

    checks = {
        "timeline_cuts_contiguous": not discontinuities,
        "cut_pts_continuous": not pts_discontinuities,
        "cut_keyframes_exact": not missing_keyframes,
        "visual_swaps_frame_exact": not bad_visual_swaps,
    }
    report = {
        "passed": all(checks.values()),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "candidate": str(candidate),
        "checks": checks,
        "metrics": {
            "fps": fps,
            "cut_count": len(cuts),
            "image_cut_count": len(image_cuts),
            "timeline_discontinuities": discontinuities,
            "pts_discontinuities": pts_discontinuities,
            "missing_keyframes": missing_keyframes,
            "bad_visual_swaps": bad_visual_swaps,
            "visual_cut_results": visual_cut_results,
        },
    }
    report_path = args.report or root / "out" / "qa" / "cut-boundaries.json"
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
