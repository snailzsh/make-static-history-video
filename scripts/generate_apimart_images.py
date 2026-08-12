#!/usr/bin/env python3
"""Generate independent APIMart history frames without overwriting existing assets."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageOps


ENDPOINT = "https://api.apimart.ai/v1/images/generations"
TASK_ENDPOINT = "https://api.apimart.ai/v1/tasks/{task_id}"
ALLOWED_STYLES = {"warm-xuan-vox", "american-comic-vox"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session() -> requests.Session:
    client = requests.Session()
    client.trust_env = False
    return client


def generate(root: Path, frame: dict, settings: dict, references: list[str], key: str) -> dict:
    frame_id = frame["frame_id"]
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    client = session()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.get("model", "gpt-image-2"),
        "prompt": settings["global_style"] + "\n\nCURRENT FRAME:\n" + frame["prompt"],
        "n": 1,
        "size": settings.get("size", "9:16"),
        "resolution": settings.get("resolution", "1k"),
        "image_urls": references,
    }
    task_id = None
    last_error = None
    for attempt in range(1, 4):
        try:
            response = client.post(ENDPOINT, headers=headers, json=payload, timeout=(60, 360))
            if response.status_code >= 400:
                raise RuntimeError(f"submit HTTP {response.status_code}: {response.text[:600]}")
            data = response.json().get("data")
            if isinstance(data, list):
                data = data[0]
            task_id = (data or {}).get("task_id")
            if not task_id:
                raise RuntimeError("submit returned no task_id")
            break
        except Exception as exc:
            last_error = str(exc)
            if attempt == 3:
                raise
            time.sleep(5 * attempt)
    write(root / "logs" / f"submitted-{frame_id}.json", {"frame_id": frame_id, "task_id": task_id})
    last = None
    while time.monotonic() - started < 1200:
        poll = client.get(TASK_ENDPOINT.format(task_id=task_id), headers=headers, timeout=(30, 120))
        if poll.status_code >= 400:
            raise RuntimeError(f"poll {frame_id} HTTP {poll.status_code}: {poll.text[:600]}")
        last = poll.json().get("data", poll.json())
        if last.get("status") == "failed":
            raise RuntimeError(f"task failed {frame_id}: {last.get('error')}")
        if last.get("status") == "completed":
            images = last.get("result", {}).get("images", [])
            urls = images[0].get("url", []) if images else []
            if not urls:
                raise RuntimeError(f"completed {frame_id} has no image URL")
            result = client.get(urls[0], timeout=(30, 240))
            result.raise_for_status()
            raw = root / "assets/source-images" / f"{frame_id}.png"
            output = root / "assets/backgrounds" / f"{frame_id}.png"
            if raw.exists() or output.exists():
                raise RuntimeError(f"refusing to overwrite existing frame {frame_id}")
            raw.parent.mkdir(parents=True, exist_ok=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(result.content)
            with Image.open(raw) as image:
                original_size = list(image.size)
                ImageOps.fit(
                    image.convert("RGB"),
                    (1080, 1920),
                    method=Image.Resampling.LANCZOS,
                ).save(output, format="PNG", optimize=True)
            row = {
                "frame_id": frame_id,
                "approved_text": frame.get("approved_text", []),
                "task_id": task_id,
                "status": "completed",
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "provider_actual_time_seconds": last.get("actual_time"),
                "cost": last.get("cost"),
                "credits_cost": last.get("credits_cost"),
                "raw_output": str(raw.relative_to(root)),
                "canonical_output": str(output.relative_to(root)),
                "original_size": original_size,
                "canonical_size": [1080, 1920],
                "sha256": sha256(output),
                "reference_count": len(references),
                "submit_last_error_before_success": last_error,
            }
            write(root / "logs" / f"completed-{frame_id}.json", row)
            return row
        time.sleep(4)
    raise RuntimeError(f"timeout {frame_id} task_id={task_id} status={(last or {}).get('status')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    key = os.environ.get("APIMART_API_KEY")
    if not key:
        raise SystemExit("APIMART_API_KEY missing")
    root = args.project_root.expanduser().resolve()
    project = load(root / "project.json")
    visual_style = project["settings"].get("visual_style")
    if visual_style not in ALLOWED_STYLES:
        raise SystemExit(f"unsupported visual style: {visual_style}")
    settings = load(root / "prompts/frame-prompts.json")
    if settings.get("style_preset", visual_style) != visual_style:
        raise SystemExit("prompt style preset does not match project visual style")
    frames = settings.get("frames", [])
    pending = [
        frame
        for frame in frames
        if not (root / "assets/backgrounds" / f"{frame['frame_id']}.png").exists()
    ]
    if not pending:
        raise SystemExit("All frames already exist")
    references = [data_uri(Path(path).expanduser().resolve()) for path in settings.get("reference_images", [])]
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    concurrency = min(int(settings.get("concurrency", 4)), 4, len(pending))
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(generate, root, frame, settings, references, key) for frame in pending]
        results = [future.result() for future in futures]
    report = {
        "provider": "APIMart",
        "model": settings.get("model", "gpt-image-2"),
        "style_preset": visual_style,
        "size": settings.get("size", "9:16"),
        "resolution": settings.get("resolution", "1k"),
        "mode": "independent_single_images_no_grid",
        "concurrency": concurrency,
        "started_at": started_at,
        "wall_elapsed_seconds": round(time.monotonic() - started, 3),
        "total_cost": round(sum(float(row.get("cost") or 0) for row in results), 6),
        "results": sorted(results, key=lambda row: row["frame_id"]),
    }
    write(root / "logs/apimart-generation.json", report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
