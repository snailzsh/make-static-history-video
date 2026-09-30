#!/usr/bin/env python3
"""Check one request/shot alignment. Read-only; never certifies human listening."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def check_alignment(alignment: dict, expected: str, duration: float) -> dict:
    errors = []
    zero_speech = []
    characters = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    arrays_valid = all(isinstance(value, list) for value in (characters, starts, ends))
    if not arrays_valid or not characters or len(characters) != len(starts) or len(starts) != len(ends):
        errors.append("alignment-arrays-empty-or-length-mismatch")
    if not isinstance(characters, list) or not all(isinstance(c, str) for c in characters):
        errors.append("invalid-characters")
    elif "".join(characters) != expected:
        errors.append("request-text-mismatch")
    if not math.isfinite(duration) or duration <= 0:
        errors.append("invalid-measured-audio-duration")
    if not errors:
        previous_start = previous_end = -1.0
        for index, (char, start, end) in enumerate(zip(characters, starts, ends)):
            if any(isinstance(t, bool) or not isinstance(t, (float, int)) or not math.isfinite(t) for t in (start, end)):
                errors.append(f"invalid-time:{index}")
                continue
            if start < 0 or end < start or end > duration + 0.05:
                errors.append(f"time-outside-audio-or-reversed:{index}")
            if start < previous_start - 1e-6 or end < previous_end - 1e-6:
                errors.append(f"nonmonotonic-time:{index}")
            if any(c.isalnum() for c in char) and end - start <= 1e-6:
                zero_speech.append(index)
            previous_start, previous_end = start, end
        if zero_speech:
            errors.append("zero-duration-spoken-characters-review-required")
    return {
        "technical_alignment_passed": not errors,
        "request_text_sha256": hashlib.sha256(expected.encode()).hexdigest(),
        "expected_characters": len(expected),
        "measured_audio_duration_seconds": duration,
        "zero_duration_spoken_character_indices": zero_speech,
        "errors": errors,
        "listening_review": "not_performed_by_this_tool",
        "release_approval": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alignment", type=Path, help="JSON alignment object or response containing alignment")
    parser.add_argument("--text-file", required=True, type=Path, help="exact submitted text; no automatic strip")
    parser.add_argument("--duration", required=True, type=float, help="measured duration on the same local timebase")
    args = parser.parse_args()
    raw = json.loads(args.alignment.read_text(encoding="utf-8"))
    result = check_alignment(raw.get("alignment", raw), args.text_file.read_text(encoding="utf-8"), args.duration)
    result["alignment_file"] = str(args.alignment.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["technical_alignment_passed"] else 1)


if __name__ == "__main__":
    main()
