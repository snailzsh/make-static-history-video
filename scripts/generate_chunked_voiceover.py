#!/usr/bin/env python3
"""Resumable ElevenLabs v3 fallback using a small number of long chunks."""

from __future__ import annotations

import argparse
import base64
import hashlib
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


def media_duration(path: Path) -> float:
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


def chunk_shots(shots: list[dict], max_chars: int, forced_pauses: dict[str, float]) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0
    for shot in shots:
        shot_chars = len(shot["voiceover_text"].strip()) + (1 if current else 0)
        if current and current_chars + shot_chars > max_chars:
            chunks.append(current)
            current = []
            current_chars = 0
            shot_chars -= 1
        current.append(shot)
        current_chars += shot_chars
        if shot["shot_id"] in forced_pauses:
            chunks.append(current)
            current = []
            current_chars = 0
    if current:
        chunks.append(current)
    return chunks


def fetch_chunk(
    session: requests.Session,
    chunk_dir: Path,
    chunk_number: int,
    shots: list[dict],
    voice: dict,
    seed: int,
    api_key: str,
    speed: float,
    previous_text: str | None,
    next_text: str | None,
    previous_request_ids: list[str],
) -> dict:
    text = "\n".join(shot["voiceover_text"].strip() for shot in shots)
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "text": text,
                "voice_id": voice["voice_id"],
                "model_id": voice["model_id"],
                "stability": voice.get("stability", 1.0),
                "speed": speed,
                "seed": seed,
                "previous_text": previous_text,
                "next_text": next_text,
                "previous_request_ids": previous_request_ids,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    meta_path = chunk_dir / f"chunk_{chunk_number:02d}.json"
    mp3_path = chunk_dir / f"chunk_{chunk_number:02d}.mp3"
    wav_path = chunk_dir / f"chunk_{chunk_number:02d}.wav"
    if meta_path.exists() and mp3_path.exists() and wav_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("fingerprint") == fingerprint:
            return meta
        raise SystemExit(f"Existing chunk fingerprint mismatch: {meta_path}")

    endpoint = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}/with-timestamps"
        "?output_format=mp3_44100_128"
    )
    voice_settings = {"stability": float(voice.get("stability", 1.0))}
    if voice["model_id"] != "eleven_v3":
        voice_settings["speed"] = speed
    payload = {
        "text": text,
        "model_id": voice["model_id"],
        "language_code": voice.get("language_code", "zh"),
        "voice_settings": voice_settings,
        "seed": seed,
        "apply_text_normalization": "auto",
    }
    request_stitching_supported = voice["model_id"] != "eleven_v3"
    if request_stitching_supported and previous_text:
        payload["previous_text"] = previous_text
    if request_stitching_supported and next_text:
        payload["next_text"] = next_text
    if request_stitching_supported and previous_request_ids:
        payload["previous_request_ids"] = previous_request_ids
    try:
        response = session.post(
            endpoint,
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=(30, 360),
        )
    except requests.RequestException as exc:
        raise SystemExit(f"Chunk {chunk_number:02d} transport error: {type(exc).__name__}: {exc}") from exc
    request_id = response.headers.get("request-id", "")
    if response.status_code >= 400:
        raise SystemExit(f"Chunk {chunk_number:02d} HTTP {response.status_code} request_id={request_id}: {response.text[:1000]}")
    body = response.json()
    if not body.get("audio_base64") or not body.get("alignment"):
        raise SystemExit(f"Chunk {chunk_number:02d} missing audio/alignment request_id={request_id}")
    alignment = body["alignment"]
    if "".join(alignment.get("characters", [])) != text:
        raise SystemExit(f"Chunk {chunk_number:02d} alignment text mismatch")
    mp3_path.write_bytes(base64.b64decode(body["audio_base64"]))
    ffmpeg = require_tool("ffmpeg")
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3_path), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path)],
        check=True,
    )
    meta = {
        "chunk_number": chunk_number,
        "fingerprint": fingerprint,
        "shot_ids": [shot["shot_id"] for shot in shots],
        "text": text,
        "voice_id": voice["voice_id"],
        "model_id": voice["model_id"],
        "stability": float(voice.get("stability", 1.0)),
        "speed": speed,
        "seed": seed,
        "request_id": request_id,
        "mp3_file": mp3_path.name,
        "wav_file": wav_path.name,
        "duration_seconds": round(media_duration(wav_path), 6),
        "alignment": alignment,
        "normalized_alignment": body.get("normalized_alignment"),
        "continuity_context": {
            "request_stitching_supported": request_stitching_supported,
            "previous_text_characters": len(previous_text or ""),
            "next_text_characters": len(next_text or ""),
            "previous_request_ids": previous_request_ids,
        },
    }
    write_json(meta_path, meta)
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-chars", type=int, default=430)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--post-speed", type=float, default=1.0)
    parser.add_argument("--only-chunk", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8"))
    shots = project["shots"]
    voice = project["voice"]
    forced_pauses = {str(key): float(value) for key, value in voice.get("scripted_pauses", {}).items()}
    chunks = chunk_shots(shots, args.max_chars, forced_pauses)
    chunk_texts = ["\n".join(shot["voiceover_text"].strip() for shot in chunk) for chunk in chunks]
    context_characters = 300
    summary = [
        {
            "chunk": index,
            "shots": [shot["shot_id"] for shot in chunk],
            "characters": len("\n".join(shot["voiceover_text"].strip() for shot in chunk)),
            "pause_after": forced_pauses.get(chunk[-1]["shot_id"], 0.0),
        }
        for index, chunk in enumerate(chunks, 1)
    ]
    print(json.dumps({"chunks": summary}, ensure_ascii=False))
    if args.dry_run:
        return
    if not 0.7 <= args.speed <= 1.2:
        raise SystemExit("--speed must be between 0.7 and 1.2")
    if voice["model_id"] == "eleven_v3" and args.speed != 1.0:
        raise SystemExit("Eleven v3 does not support the API speed setting; keep --speed 1.0 and use --post-speed")
    if not 1.0 <= args.post_speed <= 2.0:
        raise SystemExit("--post-speed must be between 1.0 and 2.0")

    ffmpeg = require_tool("ffmpeg")
    require_tool("ffprobe")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY missing")
    args.out.mkdir(parents=True, exist_ok=True)
    chunk_dir = args.out / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.trust_env = False

    if args.only_chunk is not None:
        if not 1 <= args.only_chunk <= len(chunks):
            raise SystemExit(f"--only-chunk must be 1..{len(chunks)}")
        index = args.only_chunk
        previous_text = chunk_texts[index - 2][-context_characters:] if index > 1 else None
        next_text = chunk_texts[index][:context_characters] if index < len(chunks) else None
        meta = fetch_chunk(
            session,
            chunk_dir,
            index,
            chunks[index - 1],
            voice,
            args.seed + index,
            api_key,
            args.speed,
            previous_text,
            next_text,
            [],
        )
        print(json.dumps({"chunk": index, "duration": meta["duration_seconds"], "request_id": meta["request_id"], "speed": args.speed}, ensure_ascii=False))
        return

    metas: list[dict] = []
    for index, chunk in enumerate(chunks, 1):
        previous_text = chunk_texts[index - 2][-context_characters:] if index > 1 else None
        next_text = chunk_texts[index][:context_characters] if index < len(chunks) else None
        previous_request_ids = [
            meta["request_id"] for meta in metas[-3:] if meta.get("request_id")
        ]
        meta = fetch_chunk(
            session,
            chunk_dir,
            index,
            chunk,
            voice,
            args.seed + index,
            api_key,
            args.speed,
            previous_text,
            next_text,
            previous_request_ids,
        )
        metas.append(meta)
        print(json.dumps({"chunk": index, "duration": meta["duration_seconds"], "request_id": meta["request_id"]}, ensure_ascii=False), flush=True)

    for meta in metas:
        natural_wav = chunk_dir / meta["wav_file"]
        if args.post_speed == 1.0:
            render_wav = natural_wav
        else:
            render_wav = chunk_dir / f"chunk_{meta['chunk_number']:02d}_atempo_{args.post_speed:.2f}.wav"
            if not render_wav.exists():
                subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(natural_wav), "-af", f"atempo={args.post_speed}", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(render_wav)],
                    check=True,
                )
        meta["render_wav_file"] = render_wav.name
        meta["render_duration_seconds"] = round(media_duration(render_wav), 6)
        meta["timeline_scale"] = float(meta["render_duration_seconds"]) / float(meta["duration_seconds"])

    silence_files: dict[float, Path] = {}
    concat_entries: list[Path] = []
    for chunk, meta in zip(chunks, metas):
        concat_entries.append(chunk_dir / meta["render_wav_file"])
        pause = forced_pauses.get(chunk[-1]["shot_id"], 0.0)
        if pause:
            if pause not in silence_files:
                silence = chunk_dir / f"silence_{pause:.1f}s.wav"
                subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", str(pause), "-c:a", "pcm_s16le", str(silence)],
                    check=True,
                )
                silence_files[pause] = silence
            concat_entries.append(silence_files[pause])

    concat_file = args.out / "concat.txt"
    concat_file.write_text("".join(f"file '{path.resolve()}'\n" for path in concat_entries), encoding="utf-8")
    combined = args.out / "voiceover_full_48k.wav"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(combined)],
        check=True,
    )

    global_cursor = 0.0
    rows: list[dict] = []
    for chunk, meta in zip(chunks, metas):
        alignment = meta["alignment"]
        characters = alignment["characters"]
        starts = alignment["character_start_times_seconds"]
        ends = alignment["character_end_times_seconds"]
        positions: list[tuple[int, int]] = []
        cursor = 0
        for shot in chunk:
            length = len(shot["voiceover_text"].strip())
            positions.append((cursor, cursor + length))
            cursor += length + 1
        for index, shot in enumerate(chunk):
            start_index, end_index = positions[index]
            scale = float(meta["timeline_scale"])
            local_start = 0.0 if index == 0 else float(starts[start_index]) * scale
            local_end = float(starts[positions[index + 1][0]]) * scale if index + 1 < len(chunk) else float(meta["render_duration_seconds"])
            relative = {
                "characters": characters[start_index:end_index],
                "character_start_times_seconds": [round(float(value) * scale - local_start, 6) for value in starts[start_index:end_index]],
                "character_end_times_seconds": [round(float(value) * scale - local_start, 6) for value in ends[start_index:end_index]],
            }
            alignment_file = f"shot_{shot['shot_id']}_alignment.json"
            write_json(
                args.out / alignment_file,
                {
                    "shot_id": shot["shot_id"],
                    "text": shot["voiceover_text"],
                    "voice_id": voice["voice_id"],
                    "model_id": voice["model_id"],
                    "request_id": meta["request_id"],
                    "alignment": relative,
                },
            )
            rows.append(
                {
                    "shot_id": shot["shot_id"],
                    "text": shot["voiceover_text"],
                    "file": combined.name,
                    "alignment_file": alignment_file,
                    "timeline_start_seconds": round(global_cursor + local_start, 3),
                    "timeline_end_seconds": round(global_cursor + local_end, 3),
                    "audio_duration_seconds": round(local_end - local_start, 3),
                    "request_id": meta["request_id"],
                    "chunk_number": meta["chunk_number"],
                }
            )
        global_cursor += float(meta["render_duration_seconds"])
        global_cursor += forced_pauses.get(chunk[-1]["shot_id"], 0.0)

    combined_duration = media_duration(combined)
    chunk_joins: list[dict] = []
    chunk_cursor = 0.0
    for index, (chunk, meta) in enumerate(zip(chunks, metas)):
        speech_end = chunk_cursor + float(meta["render_duration_seconds"])
        pause = forced_pauses.get(chunk[-1]["shot_id"], 0.0)
        next_start = speech_end + pause
        if index + 1 < len(metas):
            chunk_joins.append(
                {
                    "from_chunk": meta["chunk_number"],
                    "to_chunk": metas[index + 1]["chunk_number"],
                    "speech_end_seconds": round(speech_end, 3),
                    "next_start_seconds": round(next_start, 3),
                    "scripted_pause_seconds": pause,
                    "review_window_start_seconds": round(max(0.0, speech_end - 3.0), 3),
                    "review_window_end_seconds": round(min(combined_duration, next_start + 3.0), 3),
                }
            )
        chunk_cursor = next_start
    write_json(
        args.out / "voiceover_manifest.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_mode": "chunked_fallback_with_scripted_pauses",
            "fallback_reason": voice.get("fallback_reason", "continuous request unavailable or rejected"),
            "voice_id": voice["voice_id"],
            "model_id": voice["model_id"],
            "stability": float(voice.get("stability", 1.0)),
            "speed": args.speed,
            "api_speed_effective_note": "Measure model output; post_speed is applied with atempo and alignment is scaled to match.",
            "post_speed": args.post_speed,
            "combined_wav": combined.name,
            "combined_wav_duration_seconds": round(combined_duration, 3),
            "scripted_pauses": forced_pauses,
            "chunk_joins": chunk_joins,
            "voice_continuity_qa_required": True,
            "chunks": [
                {key: meta[key] for key in ("chunk_number", "shot_ids", "request_id", "wav_file", "duration_seconds", "render_wav_file", "render_duration_seconds", "timeline_scale")}
                for meta in metas
            ],
            "shots": rows,
        },
    )
    print(json.dumps({"duration_seconds": round(combined_duration, 3), "shots": len(rows), "chunks": len(chunks), "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
