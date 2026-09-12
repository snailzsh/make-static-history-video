#!/usr/bin/env python3
"""Map approved subtitle text onto homophone TTS character alignment."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DIGITS = str.maketrans("0123456789", "〇一二三四五六七八九")
PUNCT = set("，。！？；：、—…‘’“”\"'（）()《》·- ")


def resolve_font(requested: Path | None) -> Path:
    if requested:
        candidate = requested.expanduser().resolve()
        if candidate.is_file():
            return candidate
        raise SystemExit(f"Requested font not found: {candidate}")
    candidates = [
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
    ]
    windows = os.environ.get("WINDIR")
    if windows:
        candidates.extend([Path(windows) / "Fonts/msyh.ttc", Path(windows) / "Fonts/simhei.ttf"])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    fc_match = shutil.which("fc-match")
    if fc_match:
        import subprocess

        result = subprocess.run(
            [fc_match, "-f", "%{file}", "Noto Sans CJK SC"],
            check=False,
            capture_output=True,
            text=True,
        )
        candidate = Path(result.stdout.strip())
        if candidate.is_file():
            return candidate
    raise SystemExit("No supported Chinese font found; pass --font /absolute/path/to/font.ttf")


def srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def apply_pronunciation(text: str, pronunciation: dict) -> str:
    mappings: dict[str, str] = {}
    for group in ("high_risk", "mid_risk", "numerals"):
        mappings.update({key: value for key, value in pronunciation.get(group, {}).items() if not key.startswith("_")})
    for source in sorted(mappings, key=len, reverse=True):
        text = text.replace(source, mappings[source])
    return text.translate(DIGITS)


def normalized_chars(text: str, pronunciation: dict | None = None) -> list[str]:
    if pronunciation is not None:
        text = apply_pronunciation(text, pronunciation)
    return [char for char in text if not char.isspace() and char not in PUNCT]


def split_caption(text: str, max_chars: int = 16) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    result: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        cut = -1
        for index in range(min(max_chars, len(remaining) - 1), max(4, max_chars // 2) - 1, -1):
            if remaining[index - 1] in "，。！？；：、——":
                cut = index
                break
        if cut < 0:
            cut = max_chars
        result.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        result.append(remaining)
    return [item for item in result if item]


def remove_unicode_punctuation(text: str) -> str:
    return "".join(char for char in text if not unicodedata.category(char).startswith("P")).strip()


def map_sub_to_tts(sub_chars: list[str], tts_chars: list[str]) -> list[int]:
    if not sub_chars:
        return []
    matcher = difflib.SequenceMatcher(a=sub_chars, b=tts_chars, autojunk=False)
    mapping: list[int | None] = [None] * len(sub_chars)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            mapping[block.a + offset] = block.b + offset
    known = [index for index, value in enumerate(mapping) if value is not None]
    if not known:
        return [min(len(tts_chars) - 1, round(index * max(0, len(tts_chars) - 1) / max(1, len(sub_chars) - 1))) for index in range(len(sub_chars))]
    first = known[0]
    first_value = int(mapping[first])
    for index in range(first):
        mapping[index] = max(0, first_value - (first - index))
    for left, right in zip(known, known[1:]):
        if right == left + 1:
            continue
        left_value = int(mapping[left])
        right_value = int(mapping[right])
        width = right - left
        for index in range(left + 1, right):
            fraction = (index - left) / width
            mapping[index] = round(left_value + fraction * (right_value - left_value))
    last = known[-1]
    last_value = int(mapping[last])
    for index in range(last + 1, len(mapping)):
        mapping[index] = min(len(tts_chars) - 1, last_value + index - last)
    result: list[int] = []
    previous = 0
    for value in mapping:
        current = max(previous, min(len(tts_chars) - 1, int(value)))
        result.append(current)
        previous = current
    return result


def text_width(font: ImageFont.FreeTypeFont, text: str) -> int:
    box = font.getbbox(text)
    return box[2] - box[0]


def render_overlay(
    text: str,
    output: Path,
    font: ImageFont.FreeTypeFont,
    width: int,
    height: int,
) -> None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    lines = [text]
    if text_width(font, text) > width * 0.833:
        midpoint = (len(text) + 1) // 2
        lines = [text[:midpoint], text[midpoint:]]
    boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=3) for line in lines]
    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    scale = height / 1920
    spacing, pad_x, pad_y = round(16 * scale), round(46 * scale), round(28 * scale)
    content_height = sum(heights) + spacing * (len(lines) - 1)
    box_width = min(round(width * 0.926), max(widths) + pad_x * 2)
    box_height = content_height + pad_y * 2
    left = (width - box_width) // 2
    top = height - round(148 * scale) - box_height
    right, bottom = left + box_width, top + box_height
    draw.rounded_rectangle((left, top, right, bottom), radius=round(28 * scale), fill=(22, 24, 25, 218), outline=(250, 247, 239, 52), width=max(1, round(2 * scale)))
    draw.rounded_rectangle((left + round(14 * scale), top + round(20 * scale), left + round(22 * scale), bottom - round(20 * scale)), radius=round(4 * scale), fill=(178, 58, 46, 255))
    cursor_y = top + pad_y
    for line, line_width, line_height in zip(lines, widths, heights):
        draw.text(((width - line_width) // 2, cursor_y), line, font=font, fill=(250, 247, 239, 255), stroke_width=max(1, round(3 * scale)), stroke_fill=(12, 14, 15, 255))
        cursor_y += line_height + spacing
    image.save(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--voice-manifest", required=True, type=Path)
    parser.add_argument("--pronunciation", required=True, type=Path)
    parser.add_argument("--caption-dir", required=True, type=Path)
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8"))
    manifest = json.loads(args.voice_manifest.read_text(encoding="utf-8"))
    pronunciation = json.loads(args.pronunciation.read_text(encoding="utf-8"))
    subtitle_mode = project["settings"].get("subtitle_mode", "rendered")
    if subtitle_mode not in {"rendered", "none"}:
        raise SystemExit(f"Unsupported subtitle_mode: {subtitle_mode}")
    shots = {shot["shot_id"]: shot for shot in project["shots"]}
    voice_dir = args.voice_manifest.parent
    overlay_dir = args.caption_dir / "overlays"
    if args.caption_dir.exists():
        occupied = [path for path in args.caption_dir.iterdir() if path.name != "overlays"]
        existing_overlays = args.caption_dir / "overlays"
        if occupied or (existing_overlays.exists() and any(existing_overlays.iterdir())):
            raise SystemExit(f"Refusing non-empty caption directory: {args.caption_dir}")
    overlay_dir.mkdir(parents=True, exist_ok=True)
    canvas = project["settings"]["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    font_size = round(64 * height / 1920)
    font_path = resolve_font(args.font) if subtitle_mode == "rendered" else None
    font = ImageFont.truetype(str(font_path), font_size) if font_path else None

    cues: list[dict] = []
    for voice_shot in manifest["shots"]:
        shot_id = voice_shot["shot_id"]
        shot = shots[shot_id]
        display_parts = [
            cleaned
            for part in shot["caption_parts"]
            for piece in split_caption(part)
            if (cleaned := remove_unicode_punctuation(piece))
        ]
        sub_norm_parts = [normalized_chars(part, pronunciation) for part in display_parts]
        sub_norm = [char for part in sub_norm_parts for char in part]

        alignment_doc = json.loads((voice_dir / voice_shot["alignment_file"]).read_text(encoding="utf-8"))
        alignment = alignment_doc["alignment"]
        original_tts_chars = alignment["characters"]
        tts_norm: list[str] = []
        tts_norm_to_original: list[int] = []
        for original_index, char in enumerate(original_tts_chars):
            if char.isspace() or char in PUNCT:
                continue
            tts_norm.append(char)
            tts_norm_to_original.append(original_index)
        sub_to_tts_norm = map_sub_to_tts(sub_norm, tts_norm)

        cue_starts: list[float] = []
        cursor = 0
        shot_start = float(voice_shot["timeline_start_seconds"])
        shot_end = float(voice_shot["timeline_end_seconds"])
        relative_starts = alignment["character_start_times_seconds"]
        for part_index, norm_part in enumerate(sub_norm_parts):
            if part_index == 0 or not norm_part:
                start = shot_start
            else:
                mapped_norm_index = sub_to_tts_norm[min(cursor, len(sub_to_tts_norm) - 1)]
                original_index = tts_norm_to_original[mapped_norm_index]
                start = shot_start + float(relative_starts[original_index])
            cue_starts.append(max(shot_start, min(shot_end, start)))
            cursor += len(norm_part)
        for index in range(1, len(cue_starts)):
            cue_starts[index] = max(cue_starts[index], cue_starts[index - 1] + 0.08)

        for index, text in enumerate(display_parts):
            start = cue_starts[index]
            end = cue_starts[index + 1] - 0.04 if index + 1 < len(display_parts) else shot_end
            if end <= start:
                end = min(shot_end, start + 0.08)
            cues.append(
                {
                    "shot_id": shot_id,
                    "text": text,
                    "start_seconds": round(start, 3),
                    "end_seconds": round(end, 3),
                    "alignment_source": "tts_sub_sequence_map",
                }
            )

    if subtitle_mode == "rendered":
        if font is None:
            raise SystemExit("Rendered subtitles require a font")
        for index, cue in enumerate(cues, 1):
            overlay = overlay_dir / f"cue_{index:03d}.png"
            render_overlay(cue["text"], overlay, font, width, height)
            cue["overlay_file"] = f"overlays/{overlay.name}"

    srt_path = args.caption_dir / "subtitles.srt"
    srt_path.write_text(
        "\n".join(
            f"{index}\n{srt_time(cue['start_seconds'])} --> {srt_time(cue['end_seconds'])}\n{cue['text']}\n"
            for index, cue in enumerate(cues, 1)
        ),
        encoding="utf-8",
    )
    write_value = {
        "canvas": {"width": width, "height": height},
        "subtitle_mode": subtitle_mode,
        "overlays_rendered": subtitle_mode == "rendered",
        "font": {"requested": str(args.font) if args.font else "auto", "resolved_name": font_path.name, "size": font_size} if font_path else None,
        "srt_file": "subtitles.srt",
        "cue_count": len(cues),
        "cues": cues,
    }
    (args.caption_dir / "caption-manifest.json").write_text(json.dumps(write_value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cue_count": len(cues), "start": cues[0]["start_seconds"], "end": cues[-1]["end_seconds"], "caption_dir": str(args.caption_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
