from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "generate_apimart_images.py"
SPEC = importlib.util.spec_from_file_location("generate_apimart_images", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_frame() -> dict:
    return {
        "frame_id": "F10",
        "narrative_goal": "A petition is altered by officials into a constrained confession.",
        "literal_scene": "An early-Qing clerical office with three ordinary writing desks in depth.",
        "primary_action": "Three clerks edit and fold the same continuous sheet by hand.",
        "action_direction": "The sheet moves from the open foreground toward a closed file at the rear.",
        "visual_inventory": {
            "people": ["exactly three early-Qing clerks"],
            "objects": ["one continuous sheet", "three flat four-legged writing desks", "three brushes"],
            "environment": ["plain early-Qing yamen office"],
        },
        "approved_text": [],
        "historical_constraints": ["early-Qing clothing", "handwritten clerical work"],
        "risk_flags": ["abstract_mechanism"],
        "model_misread_risk": "Compression language could be interpreted as manufacturing equipment.",
        "avoid_terms_in_prompt": ["machine", "press", "roller", "screw", "wooden frame"],
        "positive_replacements": ["Every wooden object is an ordinary flat four-legged writing desk."],
        "surface_contract": "Paper shows only broad irregular ink wash; timber and plaster are uninterrupted natural textures.",
    }


class PromptContractTests(unittest.TestCase):
    def test_structured_prompt_compiles_literal_scene_before_style(self):
        settings = {
            "prompt_contract_version": 2,
            "global_style": "STYLE",
            "frames": [valid_frame()],
        }
        frame = MODULE.prepare_prompt_frames(settings)[0]
        payload_prompt = (
            "CURRENT FRAME — follow this scene first:\n"
            + frame["prompt"]
            + "\n\nVISUAL STYLE — apply without changing the scene inventory:\n"
            + settings["global_style"]
        )
        self.assertLess(payload_prompt.index("LITERAL SCENE"), payload_prompt.index("VISUAL STYLE"))
        self.assertIn("ordinary flat four-legged writing desk", payload_prompt)

    def test_attractor_term_in_positive_scene_is_blocked(self):
        frame = valid_frame()
        frame["primary_action"] = "The paper passes through a wooden frame."
        errors = MODULE.validate_structured_prompts(
            {"prompt_contract_version": 2, "frames": [frame]}
        )
        self.assertIn("F10: attractor term remains in positive scene: wooden frame", errors)

    def test_risk_requires_misread_analysis_and_positive_replacement(self):
        frame = valid_frame()
        frame["model_misread_risk"] = ""
        frame["positive_replacements"] = []
        errors = MODULE.validate_structured_prompts(
            {"prompt_contract_version": 2, "frames": [frame]}
        )
        self.assertIn("F10: risk_flags require positive_replacements", errors)
        self.assertIn("F10: risk_flags require model_misread_risk", errors)

    def test_unapproved_text_risk_requires_visible_surface_contract(self):
        frame = valid_frame()
        frame["risk_flags"].append("unapproved_text")
        frame["surface_contract"] = ""
        errors = MODULE.validate_structured_prompts(
            {"prompt_contract_version": 2, "frames": [frame]}
        )
        self.assertIn("F10: unapproved_text risk requires surface_contract", errors)

    def test_no_text_contract_uses_positive_surface_language(self):
        prompt = MODULE.compile_structured_prompt(valid_frame())
        self.assertIn("uninterrupted natural material texture", prompt)
        self.assertNotIn("signs, labels", prompt)


if __name__ == "__main__":
    unittest.main()
