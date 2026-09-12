#!/usr/bin/env python3
"""Initialize, validate, summarize, and advance guided project workflow state."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


STAGES = (
    "START",
    "BRIEF",
    "BENCHMARKS",
    "WRITING_PACK",
    "SCRIPT",
    "FACT_CHECK",
    "PRODUCTION_CONTRACT",
    "STORYBOARD",
    "VOICE",
    "VISUAL_STYLE",
    "CHARACTER_ANCHORS",
    "IMAGE_PROMPTS",
    "IMAGE_GENERATION",
    "ASSET_QC",
    "MUSIC",
    "CANDIDATE",
    "RELEASE_QA",
    "FINAL_PROMOTION",
    "FEEDBACK",
)
CURRENT_SCHEMA_VERSION = 2
STATUSES = {"未开始", "进行中", "待确认", "已确认", "需要返工", "已跳过"}
COMPLETED = {"已确认", "已跳过"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_path(root: Path) -> Path:
    return root.expanduser().resolve() / "project.json"


def load_project(root: Path) -> tuple[Path, dict]:
    path = project_path(root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing project.json: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid project.json at line {exc.lineno} column {exc.colno}") from exc
    if not isinstance(value, dict):
        raise ValueError("project.json root must be an object")
    return path, value


def save_project(path: Path, project: dict) -> None:
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_workflow() -> dict:
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "current_stage": "START",
        "next_stage": "BRIEF",
        "pending_request": "确认项目目录以及这是新选题还是续做项目",
        "stage_statuses": {
            stage: "进行中" if stage == "START" else "未开始" for stage in STAGES
        },
        "artifacts": {},
        "history": [],
        "updated_at": now_iso(),
    }


def validate(project: dict, root: Path) -> list[str]:
    errors: list[str] = []
    workflow = project.get("workflow")
    if not isinstance(workflow, dict):
        return ["missing-or-invalid:workflow"]
    if workflow.get("schema_version") != CURRENT_SCHEMA_VERSION:
        errors.append(f"workflow-schema-version-must-be-{CURRENT_SCHEMA_VERSION}")
    current = workflow.get("current_stage")
    if current not in STAGES:
        return errors + [f"unknown-current-stage:{current}"]
    current_index = STAGES.index(current)
    expected_next = STAGES[current_index + 1] if current_index + 1 < len(STAGES) else None
    if workflow.get("next_stage") != expected_next:
        errors.append(f"next-stage-mismatch:{workflow.get('next_stage')}:{expected_next}")
    statuses = workflow.get("stage_statuses")
    if not isinstance(statuses, dict):
        return errors + ["missing-or-invalid:stage_statuses"]
    if set(statuses) != set(STAGES):
        errors.append("stage-status-keys-mismatch")
    for stage in STAGES:
        status = statuses.get(stage)
        if status not in STATUSES:
            errors.append(f"invalid-stage-status:{stage}:{status}")
    for stage in STAGES[:current_index]:
        if statuses.get(stage) not in COMPLETED:
            errors.append(f"unfinished-prior-stage:{stage}:{statuses.get(stage)}")
    if statuses.get(current) == "未开始":
        errors.append(f"current-stage-not-started:{current}")
    for stage in STAGES[current_index + 1 :]:
        if statuses.get(stage) != "未开始":
            errors.append(f"future-stage-already-started:{stage}:{statuses.get(stage)}")
    if not isinstance(workflow.get("artifacts"), dict):
        errors.append("workflow-artifacts-must-be-object")
    if not isinstance(workflow.get("history"), list):
        errors.append("workflow-history-must-be-array")
    if statuses.get("FINAL_PROMOTION") == "已确认":
        approvals = project.get("approvals", {})
        if approvals.get("qc_passed") is not True:
            errors.append("final-promotion-without-qc-passed")
        if approvals.get("final_promotion") is not True:
            errors.append("final-promotion-without-explicit-approval")
        if not (root / "out/final.mp4").is_file():
            errors.append("final-promotion-without-final-file")
    return errors


def command_init(args: argparse.Namespace) -> int:
    path, project = load_project(args.project_root)
    if "workflow" in project:
        raise ValueError("workflow already exists; refusing to overwrite")
    project["workflow"] = default_workflow()
    save_project(path, project)
    print(path)
    return 0


def command_migrate(args: argparse.Namespace) -> int:
    path, project = load_project(args.project_root)
    workflow = project.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("workflow missing; run init first")
    version = workflow.get("schema_version")
    if version == CURRENT_SCHEMA_VERSION:
        print(f"already-current:{CURRENT_SCHEMA_VERSION}")
        return 0
    if version != 1:
        raise ValueError(f"unsupported workflow schema version: {version}")
    statuses = workflow.get("stage_statuses")
    if not isinstance(statuses, dict):
        raise ValueError("missing-or-invalid:stage_statuses")
    current = workflow.get("current_stage")
    if current not in STAGES:
        raise ValueError(f"unknown-current-stage:{current}")
    anchor_index = STAGES.index("CHARACTER_ANCHORS")
    current_index = STAGES.index(current)
    anchor_status = "未开始" if current_index < anchor_index else "已跳过"
    migrated_statuses = {
        stage: statuses.get(stage, anchor_status if stage == "CHARACTER_ANCHORS" else "未开始")
        for stage in STAGES
    }
    workflow["stage_statuses"] = migrated_statuses
    workflow["schema_version"] = CURRENT_SCHEMA_VERSION
    next_index = current_index + 1
    workflow["next_stage"] = STAGES[next_index] if next_index < len(STAGES) else None
    workflow.setdefault("history", []).append(
        {
            "action": "schema_migration",
            "from_version": 1,
            "to_version": CURRENT_SCHEMA_VERSION,
            "character_anchors_status": anchor_status,
            "at": now_iso(),
        }
    )
    workflow["updated_at"] = now_iso()
    errors = validate(project, args.project_root.expanduser().resolve())
    if errors:
        raise ValueError("; ".join(errors))
    save_project(path, project)
    print(f"migrated:1:{CURRENT_SCHEMA_VERSION}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    _, project = load_project(args.project_root)
    root = args.project_root.expanduser().resolve()
    errors = validate(project, root)
    print(json.dumps({"passed": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def command_summary(args: argparse.Namespace) -> int:
    _, project = load_project(args.project_root)
    root = args.project_root.expanduser().resolve()
    errors = validate(project, root)
    workflow = project.get("workflow", {})
    print(
        json.dumps(
            {
                "project": project.get("project"),
                "current_stage": workflow.get("current_stage"),
                "status": workflow.get("stage_statuses", {}).get(workflow.get("current_stage")),
                "pending_request": workflow.get("pending_request"),
                "next_stage": workflow.get("next_stage"),
                "valid": not errors,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not errors else 1


def parse_artifacts(values: list[str]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for value in values:
        name, separator, relative = value.partition("=")
        if not separator or not name or not relative:
            raise ValueError(f"artifact must use name=relative/path: {value}")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"artifact path must stay inside project: {relative}")
        artifacts[name] = relative
    return artifacts


def command_mark(args: argparse.Namespace) -> int:
    path, project = load_project(args.project_root)
    root = args.project_root.expanduser().resolve()
    workflow = project.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("workflow missing; run init first")
    current = workflow["current_stage"]
    artifacts = parse_artifacts(args.artifact)
    for relative in artifacts.values():
        if not (root / relative).exists():
            raise ValueError(f"artifact does not exist: {relative}")
    workflow["stage_statuses"][current] = args.status
    workflow["artifacts"].setdefault(current, {}).update(artifacts)
    if args.pending_request is not None:
        workflow["pending_request"] = args.pending_request
    workflow["updated_at"] = now_iso()
    errors = validate(project, root)
    if errors:
        raise ValueError("; ".join(errors))
    save_project(path, project)
    print(f"{current}:{args.status}")
    return 0


def command_advance(args: argparse.Namespace) -> int:
    path, project = load_project(args.project_root)
    root = args.project_root.expanduser().resolve()
    errors = validate(project, root)
    if errors:
        raise ValueError("; ".join(errors))
    workflow = project["workflow"]
    current = workflow["current_stage"]
    if workflow["stage_statuses"][current] not in COMPLETED:
        raise ValueError(f"current stage is not confirmed or skipped: {current}")
    next_stage = workflow["next_stage"]
    if next_stage is None:
        raise ValueError("workflow has no next stage")
    workflow["history"].append(
        {"from": current, "to": next_stage, "at": now_iso()}
    )
    workflow["current_stage"] = next_stage
    next_index = STAGES.index(next_stage) + 1
    workflow["next_stage"] = STAGES[next_index] if next_index < len(STAGES) else None
    workflow["stage_statuses"][next_stage] = "进行中"
    workflow["pending_request"] = args.pending_request
    workflow["updated_at"] = now_iso()
    errors = validate(project, root)
    if errors:
        raise ValueError("; ".join(errors))
    save_project(path, project)
    print(next_stage)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (
        ("init", command_init),
        ("migrate", command_migrate),
        ("validate", command_validate),
        ("summary", command_summary),
    ):
        subparser = commands.add_parser(name)
        subparser.add_argument("project_root", type=Path)
        subparser.set_defaults(handler=handler)
    mark = commands.add_parser("mark")
    mark.add_argument("project_root", type=Path)
    mark.add_argument("--status", choices=sorted(STATUSES), required=True)
    mark.add_argument("--artifact", action="append", default=[])
    mark.add_argument("--pending-request")
    mark.set_defaults(handler=command_mark)
    advance = commands.add_parser("advance")
    advance.add_argument("project_root", type=Path)
    advance.add_argument("--pending-request", required=True)
    advance.set_defaults(handler=command_advance)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.handler(args)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
