#!/usr/bin/env python3
"""Initialize a non-destructive static history infographic video project."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DIRECTORIES = (
    "source",
    "prompts",
    "storyboards",
    "assets/backgrounds",
    "assets/source-images",
    "voice",
    "captions/overlays",
    "audio/music",
    "remotion",
    "out/candidates",
    "out/qa",
    "logs",
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--voice-id", default="DowyQ68vDpgFYdWVGjc3")
    parser.add_argument("--model-id", default="eleven_v3")
    parser.add_argument(
        "--visual-style",
        choices=("warm-xuan-vox", "american-comic-vox"),
        default="warm-xuan-vox",
    )
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    root = args.project_root.expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing non-empty project directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for directory in DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)

    project = {
        "project": args.title,
        "source": {"title": args.title, "path": "", "attribution": ""},
        "settings": {
            "language": "zh-CN",
            "production_mode": "static-infographic",
            "image_provider": "APIMart gpt-image-2 1K independent single-image generation",
            "visual_style": args.visual_style,
            "image_generation_mode": "independent 9:16 1K images concurrency four no grid",
            "canvas": {"width": args.width, "height": args.height},
            "fps": args.fps,
            "caption_safe_zone_bottom_percent": 18,
            "image_low_detail_bottom_percent": 22,
            "duration_policy": "voice alignment authoritative",
            "caption_punctuation_policy": "remove all Unicode punctuation",
            "semantic_content_policy": "scene information is baked into generated images; Remotion assembles only frames captions voice BGM and approved end cards",
        },
        "voice": {
            "provider": "ElevenLabs",
            "voice_id": args.voice_id,
            "model_id": args.model_id,
            "language_code": "zh",
            "stability": 0.5,
            "generation_mode": "single_continuous_request_with_chunked_fallback_at_shot_boundaries",
            "alignment_endpoint": "/v1/text-to-speech/{voice_id}/with-timestamps",
            "scripted_pauses": {},
        },
        "publish": {
            "platforms": ["微信公众号", "抖音", "X"],
            "title_punctuation": "none",
        },
        "approvals": {
            "source_ready": False,
            "script_confirmed": False,
            "storyboard_confirmed": False,
            "settings_confirmed": True,
            "assets_ready": False,
            "voice_generated": False,
            "assembled": False,
            "captioned": False,
            "qc_passed": False,
            "publish_copy_ready": False,
        },
        "shots": [],
    }
    write_json(root / "project.json", project)
    write_json(
        root / "pronunciation.json",
        {
            "high_risk": {"_note": "Map approved subtitle spelling to TTS-safe homophones only when needed"},
            "mid_risk": {},
            "numerals": {},
        },
    )

    template = Path(__file__).resolve().parents[1] / "assets/remotion-template"
    shutil.copytree(template, root / "remotion", dirs_exist_ok=True)
    print(root)


if __name__ == "__main__":
    main()
