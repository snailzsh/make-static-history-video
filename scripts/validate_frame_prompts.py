#!/usr/bin/env python3
"""Validate and preview structured image prompts without calling a provider."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("generate_apimart_images.py")
SPEC = importlib.util.spec_from_file_location("generate_apimart_images", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt_file", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    settings = json.loads(args.prompt_file.read_text(encoding="utf-8"))
    errors = MODULE.validate_structured_prompts(settings)
    previews = []
    if not errors:
        previews = [
            {
                "frame_id": frame["frame_id"],
                "compiled_prompt": MODULE.compile_structured_prompt(frame),
                "model_misread_risk": frame.get("model_misread_risk", ""),
                "risk_flags": frame.get("risk_flags", []),
            }
            for frame in settings.get("frames", [])
        ]
    result = {
        "passed": not errors,
        "prompt_contract_version": settings.get("prompt_contract_version", 1),
        "errors": errors,
        "previews": previews,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
