#!/usr/bin/env python3
"""Initialize a non-destructive static history infographic video project."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from manage_workflow import default_workflow


DIRECTORIES = (
    "source",
    "writing-pack",
    "prompts",
    "storyboards",
    "assets/backgrounds",
    "assets/source-images",
    "characters/anchors",
    "characters/source-anchors",
    "voice",
    "captions/overlays",
    "audio/music",
    "remotion",
    "out/candidates",
    "out/qa",
    "logs",
    "feedback",
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--guided",
        action="store_true",
        help="initialize pre-production workflow without requiring confirmed voice or visual settings",
    )
    parser.add_argument("--voice-id")
    parser.add_argument("--model-id")
    parser.add_argument(
        "--visual-style",
        choices=("warm-xuan-vox", "american-comic-vox", "knowledge-card", "qibaishi-xieyi"),
        default=None,
    )
    parser.add_argument("--subtitle-mode", choices=("rendered", "none"), default="rendered")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    if not args.voice_id and not args.guided:
        args.voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    if not args.model_id:
        args.model_id = "eleven_v3" if args.guided else os.environ.get("ELEVENLABS_MODEL_ID", "eleven_v3")
    if not args.voice_id and not args.guided:
        parser.error("provide --voice-id or set ELEVENLABS_VOICE_ID")

    visual_style = args.visual_style or (None if args.guided else "warm-xuan-vox")

    if args.width * 9 == args.height * 16:
        aspect_ratio = "16:9"
    elif args.width * 16 == args.height * 9:
        aspect_ratio = "9:16"
    else:
        aspect_ratio = f"{args.width}:{args.height}"

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
            "visual_style": visual_style,
            "subtitle_mode": args.subtitle_mode,
            "caption_sidecar_for_alignment_only": args.subtitle_mode == "none",
            "aspect_ratio": aspect_ratio,
            "image_generation_mode": f"independent {aspect_ratio} 1K images concurrency four no grid",
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
            "voice_id": args.voice_id or "",
            "model_id": args.model_id,
            "language_code": "zh",
            "stability": 0.5,
            "generation_mode": "single_continuous_request_with_chunked_fallback_at_shot_boundaries",
            "alignment_endpoint": "/v1/text-to-speech/{voice_id}/with-timestamps",
            "scripted_pauses": {},
            "voice_continuity_qa_required": True,
        },
        "publish": {
            "platforms": [] if args.guided else ["微信公众号", "抖音", "X"],
            "title_punctuation": "none",
        },
        "approvals": {
            "source_ready": False,
            "script_confirmed": False,
            "storyboard_confirmed": False,
            "character_anchors_confirmed": False,
            "paid_generation_confirmed": False,
            "settings_confirmed": not args.guided,
            "assets_ready": False,
            "voice_generated": False,
            "voice_continuity_passed": False,
            "assembled": False,
            "captioned": False,
            "qc_passed": False,
            "final_promotion": False,
            "publish_copy_ready": False,
        },
        "workflow": default_workflow(),
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
    project_templates = template.parent / "project-templates"
    shutil.copy2(project_templates / "brief.md", root / "brief.md")
    shutil.copy2(project_templates / "production-review.md", root / "feedback/production-review.md")
    print(root)


if __name__ == "__main__":
    main()
