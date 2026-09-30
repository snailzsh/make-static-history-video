#!/usr/bin/env python3
"""Prepare approved JPEG working images without changing canonical PNGs or timing."""
from __future__ import annotations

import argparse
import errno
import hashlib
import io
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from PIL import Image, JpegImagePlugin


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_render_images(root: Path) -> dict:
    project = load(root / "project.json")
    settings = project["settings"]
    image_format = settings.get("render_image_format", "png")
    if image_format == "png":
        return {"status": "legacy_png_unchanged"}
    if image_format != "jpeg" or settings.get("render_jpeg_quality") != 92 or settings.get("render_jpeg_subsampling") != "4:4:4":
        raise ValueError("Only the approved JPEG quality 92 / 4:4:4 profile is supported")

    canvas = settings["canvas"]
    size = (int(canvas["width"]), int(canvas["height"]))
    frames = load(root / "storyboards/frame-manifest.json")["frames"]
    ids = [frame["frame_id"] for frame in frames]
    if not ids or len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", identifier) for identifier in ids):
        raise ValueError("Frame IDs must be nonempty, unique, safe filenames")
    sources = {identifier: root / "assets/backgrounds" / f"{identifier}.png" for identifier in ids}
    # Check the whole set before creating outputs; never silently drop a missing frame.
    for source in sources.values():
        with Image.open(source) as image:
            image.load()
            if image.format != "PNG" or image.size != size or image.mode != "RGB":
                raise ValueError(f"Expected canonical RGB PNG {size}: {source}")

    timeline_path = root / "storyboards/timeline.json"
    timeline = load(timeline_path) if timeline_path.exists() else None
    if timeline is not None:
        referenced = {entry["frame_id"] for entry in timeline["entries"] if entry["type"] == "image"}
        if not referenced.issubset(sources):
            raise ValueError("Timeline references unknown canonical frame IDs")

    report_path = root / "logs/working-image-compression.json"
    previous = load(report_path) if report_path.exists() else {}
    old_rows = {row["frame_id"]: row for row in previous.get("images", [])}
    rows = []
    for identifier, source in sources.items():
        source_hash = digest(source)
        working = root / "assets/render-images" / f"{identifier}.jpg"
        public = root / "remotion/public/frames" / f"{identifier}.jpg"
        old = old_rows.get(identifier, {})
        if old.get("source_sha256") == source_hash and working.exists() and digest(working) == old.get("jpeg_sha256"):
            encoded_hash = old["jpeg_sha256"]
            encoded = None
        else:
            with Image.open(source) as image:
                output = io.BytesIO()
                options = {"icc_profile": image.info["icc_profile"]} if image.info.get("icc_profile") else {}
                image.save(output, format="JPEG", quality=92, subsampling=0, optimize=True, **options)
                encoded = output.getvalue()
            encoded_hash = hashlib.sha256(encoded).hexdigest()

        # Reuse identical crash-recovery outputs; refuse unrelated JPEG overwrites.
        for target in (working, public):
            if target.is_symlink():
                raise ValueError(f"Refusing to replace a symlink: {target}")
            if target.exists() and digest(target) not in {encoded_hash, old.get("jpeg_sha256")}:
                raise ValueError(f"Untracked or modified JPEG must be preserved: {target}")

        working.parent.mkdir(parents=True, exist_ok=True)
        if encoded is not None and (not working.exists() or digest(working) != encoded_hash):
            temporary = working.with_name(f".{identifier}-{uuid.uuid4().hex}.jpg")
            temporary.write_bytes(encoded)
            temporary.replace(working)
        with Image.open(working) as image:
            image.load()
            if image.format != "JPEG" or image.mode != "RGB" or image.size != size or JpegImagePlugin.get_sampling(image) != 0:
                raise ValueError(f"JPEG verification failed: {working}")

        public.parent.mkdir(parents=True, exist_ok=True)
        if not public.exists() or digest(public) != encoded_hash:
            temporary = public.with_name(f".{identifier}-{uuid.uuid4().hex}.jpg")
            try:
                os.link(working, temporary)
            except OSError as error:
                if error.errno != errno.EXDEV:
                    raise
                shutil.copy2(working, temporary)
            temporary.replace(public)
        if digest(source) != source_hash or digest(public) != encoded_hash:
            raise ValueError(f"Source or public hash changed during compression: {identifier}")
        rows.append({
            "frame_id": identifier,
            "source": str(source.relative_to(root)), "source_sha256": source_hash,
            "working": str(working.relative_to(root)), "jpeg_sha256": encoded_hash,
            "public": str(public.relative_to(root)),
            "public_shares_working_inode": working.samefile(public),
            "png_bytes": source.stat().st_size, "jpeg_bytes": working.stat().st_size,
        })

    if timeline is not None:
        backup = root / "logs/timeline-before-working-jpeg.json"
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(timeline_path, backup)
        for entry in timeline["entries"]:
            if entry["type"] == "image":
                entry["asset_file"] = f"frames/{entry['frame_id']}.jpg"
        value = json.dumps(timeline, ensure_ascii=False, indent=2) + "\n"
        if timeline_path.read_text(encoding="utf-8") != value:
            timeline_path.write_text(value, encoding="utf-8")

    png_bytes = sum(row["png_bytes"] for row in rows)
    jpeg_bytes = sum(row["jpeg_bytes"] for row in rows)
    report = {
        "status": "working_images_prepared_not_new_video_release",
        "profile": {"format": "JPEG", "quality": 92, "subsampling": "4:4:4", "size": list(size)},
        "frame_count": len(rows), "png_bytes": png_bytes, "jpeg_bytes": jpeg_bytes,
        "savings_percent": round(100 * (1 - jpeg_bytes / png_bytes), 2),
        "canonical_pngs_unchanged": True, "timeline_timing_unchanged": True,
        "old_public_pngs_preserved": True, "paid_calls": 0,
        "existing_videos_and_voice_not_modified": True,
        "configuration_basis": "project.json.settings explicitly selects JPEG quality 92 / 4:4:4; this report grants no approval",
        "full_batch_visual_qa_not_inferred": True, "images": rows,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {key: value for key, value in report.items() if key != "images"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_render_images(args.project_root.expanduser().resolve()), ensure_ascii=False))


if __name__ == "__main__":
    main()
