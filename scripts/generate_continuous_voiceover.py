#!/usr/bin/env python3
"""Generate one ElevenLabs request with actionable HTTP diagnostics."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Required executable not found on PATH: {name}")
    return path


def duration(path: Path) -> float:
    ffprobe = require_tool("ffprobe")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260730)
    args = parser.parse_args()

    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit(f"Refusing non-empty output directory: {args.out}")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY missing")

    project = json.loads(args.project.read_text(encoding="utf-8"))
    shots = project["shots"]
    voice = project["voice"]
    separator = "\n"
    full_text = separator.join(shot["voiceover_text"].strip() for shot in shots)
    args.out.mkdir(parents=True, exist_ok=True)

    endpoint = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}/with-timestamps"
        "?output_format=mp3_44100_128"
    )
    payload = {
        "text": full_text,
        "model_id": voice["model_id"],
        "language_code": voice.get("language_code", "zh"),
        "voice_settings": {"stability": float(voice.get("stability", 1.0))},
        "seed": args.seed,
        "apply_text_normalization": "auto",
    }
    session = requests.Session()
    # The local desktop proxy accepts short GETs but has been observed closing
    # long ElevenLabs POST uploads. Direct TLS to api.elevenlabs.io is verified.
    session.trust_env = False
    try:
        response = session.post(
            endpoint,
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=(30, 600),
        )
    except requests.RequestException as exc:
        raise SystemExit(f"ElevenLabs transport error: {type(exc).__name__}: {exc}") from exc
    request_id = response.headers.get("request-id", "")
    if response.status_code >= 400:
        raise SystemExit(
            f"ElevenLabs HTTP {response.status_code} request_id={request_id}: {response.text[:1000]}"
        )
    body = response.json()
    if not body.get("audio_base64") or not body.get("alignment"):
        raise SystemExit(f"ElevenLabs response missing audio/alignment request_id={request_id}")

    audio_mp3 = args.out / "voiceover_continuous.mp3"
    audio_wav = args.out / "voiceover_full_48k.wav"
    audio_mp3.write_bytes(base64.b64decode(body["audio_base64"]))
    ffmpeg = require_tool("ffmpeg")
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio_mp3), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(audio_wav)],
        check=True,
    )
    audio_duration = duration(audio_wav)

    alignment = body["alignment"]
    characters = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    if not (len(characters) == len(starts) == len(ends)):
        raise SystemExit("Alignment arrays have inconsistent lengths")
    if "".join(characters) != full_text:
        raise SystemExit(f"Alignment mismatch expected={len(full_text)} actual={len(characters)}")

    summary = {
        "generation_mode": "single_continuous_request",
        "voice_id": voice["voice_id"],
        "model_id": voice["model_id"],
        "language_code": voice.get("language_code", "zh"),
        "stability": float(voice.get("stability", 1.0)),
        "seed": args.seed,
        "characters": len(characters),
        "request_id": request_id,
    }
    write_json(
        args.out / "continuous_alignment.json",
        {
            **summary,
            "text": full_text,
            "alignment": alignment,
            "normalized_alignment": body.get("normalized_alignment"),
        },
    )

    positions: list[tuple[int, int]] = []
    cursor = 0
    for shot in shots:
        length = len(shot["voiceover_text"].strip())
        positions.append((cursor, cursor + length))
        cursor += length + len(separator)

    rows: list[dict] = []
    for index, shot in enumerate(shots):
        start_index, end_index = positions[index]
        timeline_start = 0.0 if index == 0 else float(starts[start_index])
        timeline_end = float(starts[positions[index + 1][0]]) if index + 1 < len(shots) else audio_duration
        relative = {
            "characters": characters[start_index:end_index],
            "character_start_times_seconds": [round(float(value) - timeline_start, 6) for value in starts[start_index:end_index]],
            "character_end_times_seconds": [round(float(value) - timeline_start, 6) for value in ends[start_index:end_index]],
        }
        alignment_file = f"shot_{shot['shot_id']}_alignment.json"
        write_json(
            args.out / alignment_file,
            {
                "shot_id": shot["shot_id"],
                "text": shot["voiceover_text"],
                "voice_id": voice["voice_id"],
                "model_id": voice["model_id"],
                "request_id": request_id,
                "alignment": relative,
            },
        )
        rows.append(
            {
                "shot_id": shot["shot_id"],
                "text": shot["voiceover_text"],
                "file": audio_mp3.name,
                "alignment_file": alignment_file,
                "timeline_start_seconds": round(timeline_start, 3),
                "timeline_end_seconds": round(timeline_end, 3),
                "audio_duration_seconds": round(timeline_end - timeline_start, 3),
                "request_id": request_id,
            }
        )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **summary,
        "combined_wav": audio_wav.name,
        "combined_wav_duration_seconds": round(audio_duration, 3),
        "shots": rows,
    }
    write_json(args.out / "voiceover_manifest.json", manifest)
    print(
        json.dumps(
            {
                "request_id": request_id,
                "duration_seconds": round(audio_duration, 3),
                "characters": len(characters),
                "shots": len(rows),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
