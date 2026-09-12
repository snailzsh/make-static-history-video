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
ALLOWED_STYLES = {"warm-xuan-vox", "american-comic-vox", "knowledge-card", "qibaishi-xieyi"}
PROMPT_CONTRACT_VERSION = 2


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


def request_with_retry(
    client: requests.Session,
    method: str,
    url: str,
    *,
    attempts: int = 5,
    **kwargs: object,
) -> requests.Response:
    """Retry transient APIMart transport and 5xx failures without resubmitting completed work."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = client.request(method, url, **kwargs)
            if response.status_code >= 500:
                raise requests.HTTPError(
                    f"transient HTTP {response.status_code}: {response.text[:400]}",
                    response=response,
                )
            response.raise_for_status()
            return response
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            last_error = exc
            if attempt == attempts:
                raise
            time.sleep(4 * attempt)
    raise RuntimeError(f"request failed: {last_error}")


def resolve_inside_project(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def _text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def validate_structured_prompts(settings: dict) -> list[str]:
    """Validate prompt-contract v2 before any paid request is submitted."""
    if int(settings.get("prompt_contract_version", 1)) < PROMPT_CONTRACT_VERSION:
        return []
    errors: list[str] = []
    frames = settings.get("frames", [])
    if not isinstance(frames, list) or not frames:
        return ["prompt contract v2 requires at least one frame"]
    seen: set[str] = set()
    for frame in frames:
        frame_id = str(frame.get("frame_id", "unknown"))
        if frame_id in seen:
            errors.append(f"{frame_id}: duplicate frame_id")
        seen.add(frame_id)
        for field in ("narrative_goal", "literal_scene", "primary_action", "action_direction"):
            if not str(frame.get(field, "")).strip():
                errors.append(f"{frame_id}: missing {field}")
        inventory = frame.get("visual_inventory")
        if not isinstance(inventory, dict):
            errors.append(f"{frame_id}: visual_inventory must be an object")
            inventory = {}
        inventory_items: list[str] = []
        for group in ("people", "objects", "environment"):
            value = inventory.get(group, [])
            if not isinstance(value, list):
                errors.append(f"{frame_id}: visual_inventory.{group} must be a list")
            else:
                inventory_items.extend(_text_list(value))
        if not inventory_items:
            errors.append(f"{frame_id}: visual_inventory is empty")
        historical = frame.get("historical_constraints")
        if not _text_list(historical):
            errors.append(f"{frame_id}: historical_constraints is empty")
        risk_flags = _text_list(frame.get("risk_flags", []))
        replacements = _text_list(frame.get("positive_replacements", []))
        if risk_flags and not replacements:
            errors.append(f"{frame_id}: risk_flags require positive_replacements")
        if risk_flags and not str(frame.get("model_misread_risk", "")).strip():
            errors.append(f"{frame_id}: risk_flags require model_misread_risk")
        if "unapproved_text" in risk_flags and not str(frame.get("surface_contract", "")).strip():
            errors.append(f"{frame_id}: unapproved_text risk requires surface_contract")
        positive_fields = [
            str(frame.get("literal_scene", "")),
            str(frame.get("primary_action", "")),
            str(frame.get("action_direction", "")),
            *inventory_items,
            *replacements,
            str(frame.get("surface_contract", "")),
        ]
        positive_prompt = "\n".join(positive_fields).casefold()
        for term in _text_list(frame.get("avoid_terms_in_prompt", [])):
            if term.casefold() in positive_prompt:
                errors.append(f"{frame_id}: attractor term remains in positive scene: {term}")
    return errors


def compile_structured_prompt(frame: dict) -> str:
    inventory = frame["visual_inventory"]

    def joined(group: str) -> str:
        values = _text_list(inventory.get(group, []))
        return "; ".join(values) if values else "none"

    approved_text = _text_list(frame.get("approved_text", []))
    if approved_text:
        text_contract = "Render exactly these visible strings and no others: " + " | ".join(approved_text)
    else:
        text_contract = (
            "Every visible surface contains only uninterrupted natural material texture. "
            "Paper may show broad irregular ink wash that cannot resolve into glyphs."
        )
    replacements = _text_list(frame.get("positive_replacements", []))
    sections = [
        f"FRAME: {frame['frame_id']}",
        "NARRATIVE GOAL:\n" + str(frame["narrative_goal"]).strip(),
        "LITERAL SCENE:\n" + str(frame["literal_scene"]).strip(),
        (
            "VISIBLE INVENTORY — use these content-bearing elements:\n"
            f"People: {joined('people')}\nObjects: {joined('objects')}\nEnvironment: {joined('environment')}"
        ),
        "ONE PRIMARY ACTION:\n" + str(frame["primary_action"]).strip(),
        "ACTION DIRECTION:\n" + str(frame["action_direction"]).strip(),
        "TEXT CONTRACT:\n" + text_contract,
        "HISTORICAL CONSTRAINTS:\n" + "; ".join(_text_list(frame["historical_constraints"])),
    ]
    if replacements:
        sections.append("POSITIVE RISK CONTROLS:\n" + "; ".join(replacements))
    surface_contract = str(frame.get("surface_contract", "")).strip()
    if surface_contract:
        sections.append("VISIBLE SURFACE CONTRACT:\n" + surface_contract)
    composition = str(frame.get("composition", "")).strip()
    if composition:
        sections.append("COMPOSITION:\n" + composition)
    return "\n\n".join(sections)


def prepare_prompt_frames(settings: dict) -> list[dict]:
    errors = validate_structured_prompts(settings)
    if errors:
        raise SystemExit("prompt preflight failed:\n- " + "\n- ".join(errors))
    frames = settings.get("frames", [])
    if int(settings.get("prompt_contract_version", 1)) < PROMPT_CONTRACT_VERSION:
        return frames
    return [{**frame, "prompt": compile_structured_prompt(frame)} for frame in frames]


def apply_character_locks(root: Path, frames: list[dict], style_preset: str) -> list[dict]:
    if not any(frame.get("character_ids") for frame in frames):
        return frames
    manifest_path = root / "characters/character-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("frames declare character_ids but characters/character-manifest.json is missing")
    manifest = load(manifest_path)
    if manifest.get("style_preset") != style_preset:
        raise SystemExit("character manifest style preset does not match project visual style")
    characters = manifest.get("characters", [])
    by_id = {item.get("character_id"): item for item in characters if isinstance(item, dict)}
    if len(by_id) != len(characters):
        raise SystemExit("character manifest has missing or duplicate character_id")
    locked_frames: list[dict] = []
    for frame in frames:
        identities: list[str] = []
        anchor_paths = list(frame.get("generation_reference_images", []))
        for character_id in frame.get("character_ids", []):
            character = by_id.get(character_id)
            if character is None:
                raise SystemExit(f"unknown character_id {character_id} in frame {frame.get('frame_id')}")
            identity_prompt = str(character.get("identity_prompt", "")).strip()
            if not identity_prompt:
                raise SystemExit(f"character {character_id} has no identity_prompt")
            identities.append(f"{character_id} {character.get('name', '')}: {identity_prompt}")
            if character.get("continuity") == "strict":
                if character.get("status") != "confirmed":
                    raise SystemExit(f"strict character {character_id} is not confirmed")
                anchors = character.get("anchors", {})
                for kind in ("face", "full_body"):
                    value = anchors.get(kind)
                    if not value:
                        raise SystemExit(f"strict character {character_id} has no {kind} anchor")
                    path = resolve_inside_project(root, value)
                    if not path.is_file():
                        raise SystemExit(f"missing {kind} anchor for {character_id}: {path}")
                    if value not in anchor_paths:
                        anchor_paths.append(value)
        prompt = frame["prompt"]
        if identities:
            prompt += (
                "\n\nCHARACTER IDENTITY LOCKS:\n"
                + "\n".join(identities)
                + "\nUse anchor images only for identity. Preserve age, face shape, body silhouette, "
                "hairstyle, facial hair, clothing silhouette and stable colors. Do not copy anchor pose, "
                "framing, background, props, lighting, composition, whitespace or brush marks."
            )
        locked_frames.append(
            {**frame, "prompt": prompt, "generation_reference_images": anchor_paths}
        )
    return locked_frames


def generate(
    root: Path,
    frame: dict,
    settings: dict,
    references: list[str],
    key: str,
    raw_dir: Path,
    canonical_dir: Path,
) -> dict:
    frame_id = frame["frame_id"]
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    client = session()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    frame_reference_paths = frame.get("generation_reference_images", [])
    frame_references: list[str] = []
    for value in frame_reference_paths:
        path = resolve_inside_project(root, value)
        if not path.is_file():
            raise RuntimeError(f"missing frame reference {frame_id}: {path}")
        frame_references.append(data_uri(path))
    all_references = references + frame_references
    payload = {
        "model": settings.get("model", "gpt-image-2"),
        "prompt": "CURRENT FRAME — follow this scene first:\n" + frame["prompt"]
        + "\n\nVISUAL STYLE — apply without changing the scene inventory:\n"
        + settings["global_style"],
        "n": 1,
        "size": settings.get("size", "9:16"),
        "resolution": settings.get("resolution", "1k"),
        "image_urls": all_references,
    }
    task_id = None
    last_error = None
    for attempt in range(1, 4):
        try:
            response = request_with_retry(
                client,
                "POST",
                ENDPOINT,
                headers=headers,
                json=payload,
                timeout=(60, 360),
            )
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
        poll = request_with_retry(
            client,
            "GET",
            TASK_ENDPOINT.format(task_id=task_id),
            headers=headers,
            timeout=(30, 120),
        )
        last = poll.json().get("data", poll.json())
        if last.get("status") == "failed":
            raise RuntimeError(f"task failed {frame_id}: {last.get('error')}")
        if last.get("status") == "completed":
            images = last.get("result", {}).get("images", [])
            urls = images[0].get("url", []) if images else []
            if not urls:
                raise RuntimeError(f"completed {frame_id} has no image URL")
            result = request_with_retry(client, "GET", urls[0], timeout=(30, 240))
            raw = root / raw_dir / f"{frame_id}.png"
            output = root / canonical_dir / f"{frame_id}.png"
            if raw.exists() or output.exists():
                raise RuntimeError(f"refusing to overwrite existing frame {frame_id}")
            raw.parent.mkdir(parents=True, exist_ok=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(result.content)
            canonical_size = tuple(int(value) for value in settings.get("_canonical_size", [1080, 1920]))
            with Image.open(raw) as image:
                original_size = list(image.size)
                ImageOps.fit(
                    image.convert("RGB"),
                    canonical_size,
                    method=Image.Resampling.LANCZOS,
                ).save(output, format="PNG", optimize=True)
            row = {
                "frame_id": frame_id,
                "character_ids": frame.get("character_ids", []),
                "required_text": frame.get("required_text", frame.get("approved_text", [])),
                "approved_text": frame.get("approved_text", []),
                "text_plan": frame.get("text_plan", []),
                "blank_text_containers_allowed": frame.get("blank_text_containers_allowed"),
                "task_id": task_id,
                "status": "completed",
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "provider_actual_time_seconds": last.get("actual_time"),
                "cost": last.get("cost"),
                "credits_cost": last.get("credits_cost"),
                "raw_output": str(raw.relative_to(root)),
                "canonical_output": str(output.relative_to(root)),
                "original_size": original_size,
                "canonical_size": list(canonical_size),
                "sha256": sha256(output),
                "reference_count": len(all_references),
                "generation_reference_images": frame_reference_paths,
                "submit_last_error_before_success": last_error,
            }
            write(root / "logs" / f"completed-{frame_id}.json", row)
            return row
        time.sleep(4)
    raise RuntimeError(f"timeout {frame_id} task_id={task_id} status={(last or {}).get('status')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--frame-id", action="append", dest="frame_ids")
    parser.add_argument("--prompt-file", type=Path, default=Path("prompts/frame-prompts.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("assets/source-images"))
    parser.add_argument("--canonical-dir", type=Path, default=Path("assets/backgrounds"))
    parser.add_argument("--report-file", type=Path, default=Path("logs/apimart-generation.json"))
    parser.add_argument(
        "--prompt-addenda-file",
        type=Path,
        help="Optional JSON repair plan whose prompt_addendum is appended by frame_id.",
    )
    args = parser.parse_args()
    key = os.environ.get("APIMART_API_KEY")
    if not key:
        raise SystemExit("APIMART_API_KEY missing")
    root = args.project_root.expanduser().resolve()
    project = load(root / "project.json")
    if project.get("approvals", {}).get("paid_generation_confirmed") is not True:
        raise SystemExit("paid generation is not confirmed in project.json")
    visual_style = project["settings"].get("visual_style")
    if visual_style not in ALLOWED_STYLES:
        raise SystemExit(f"unsupported visual style: {visual_style}")
    prompt_file = args.prompt_file if args.prompt_file.is_absolute() else root / args.prompt_file
    settings = load(prompt_file)
    canvas = project["settings"]["canvas"]
    settings["_canonical_size"] = [int(canvas["width"]), int(canvas["height"])]
    if settings.get("style_preset", visual_style) != visual_style:
        raise SystemExit("prompt style preset does not match project visual style")
    frames = prepare_prompt_frames(settings)
    if args.prompt_addenda_file:
        if int(settings.get("prompt_contract_version", 1)) >= PROMPT_CONTRACT_VERSION:
            raise SystemExit(
                "prompt contract v2 forbids appended repair instructions; create a new structured prompt file"
            )
        addenda_path = args.prompt_addenda_file.expanduser().resolve()
        addenda_data = load(addenda_path)
        addenda = {item["frame_id"]: item for item in addenda_data.get("repairs", [])}
        unknown_addenda = sorted(set(addenda) - {frame["frame_id"] for frame in frames})
        if unknown_addenda:
            raise SystemExit(f"unknown prompt addenda frame ids: {unknown_addenda}")
        frames = [
            {
                **frame,
                "prompt": addenda[frame["frame_id"]].get("prompt_override")
                or (
                    frame["prompt"]
                    + "\n\nREPAIR REQUIREMENT:\n"
                    + addenda[frame["frame_id"]]["prompt_addendum"]
                ),
            }
            if frame["frame_id"] in addenda
            else frame
            for frame in frames
        ]
    if args.frame_ids:
        selected = set(args.frame_ids)
        known = {frame["frame_id"] for frame in frames}
        missing = sorted(selected - known)
        if missing:
            raise SystemExit(f"unknown frame ids: {missing}")
        frames = [frame for frame in frames if frame["frame_id"] in selected]
    frames = apply_character_locks(root, frames, visual_style)
    if visual_style == "knowledge-card":
        for frame in frames:
            frame_id = frame.get("frame_id", "unknown")
            required_text = frame.get("required_text", [])
            text_plan = frame.get("text_plan", [])
            if not required_text:
                raise SystemExit(f"knowledge-card frame has no required_text: {frame_id}")
            if not text_plan:
                raise SystemExit(f"knowledge-card frame has no text_plan: {frame_id}")
            if len(text_plan) < 3:
                raise SystemExit(f"knowledge-card frame needs at least three planned text containers: {frame_id}")
            if frame.get("blank_text_containers_allowed") is not False:
                raise SystemExit(f"knowledge-card frame must forbid blank text containers: {frame_id}")
            if not any(isinstance(item, dict) and item.get("role") == "main_title" for item in text_plan):
                raise SystemExit(f"knowledge-card frame has no planned main title: {frame_id}")
            if any(not isinstance(item, dict) or not str(item.get("text", "")).strip() for item in text_plan):
                raise SystemExit(f"knowledge-card frame has an empty planned text item: {frame_id}")
            planned_text = {
                item.get("text")
                for item in text_plan
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            }
            missing = [text for text in required_text if text not in planned_text]
            if missing:
                raise SystemExit(
                    f"knowledge-card required_text missing from text_plan: {frame_id}: {missing}"
                )
    pending = [
        frame
        for frame in frames
        if not (root / args.canonical_dir / f"{frame['frame_id']}.png").exists()
    ]
    if not pending:
        raise SystemExit("All frames already exist")
    references = [
        data_uri(resolve_inside_project(root, path))
        for path in settings.get("reference_images", [])
    ]
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    concurrency = min(int(settings.get("concurrency", 4)), 4, len(pending))
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(
                generate,
                root,
                frame,
                settings,
                references,
                key,
                args.raw_dir,
                args.canonical_dir,
            )
            for frame in pending
        ]
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
    report_file = args.report_file if args.report_file.is_absolute() else root / args.report_file
    write(report_file, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
