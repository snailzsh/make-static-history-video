from __future__ import annotations

import importlib.util
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "manage_workflow.py"
SPEC = importlib.util.spec_from_file_location("manage_workflow", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class GuidedWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_root = Path(tempfile.mkdtemp(prefix="history-workflow-tests-"))

    def create_project(self, root: Path) -> dict:
        project = {
            "project": "测试项目",
            "approvals": {"qc_passed": False, "final_promotion": False},
            "workflow": MODULE.default_workflow(),
        }
        (root / "project.json").write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return project

    def test_default_state_is_valid(self):
        root = self.test_root / "default"
        root.mkdir()
        project = self.create_project(root)
        self.assertEqual([], MODULE.validate(project, root))

    def test_storyboard_precedes_voice_for_executable_tts(self):
        self.assertLess(MODULE.STAGES.index("STORYBOARD"), MODULE.STAGES.index("VOICE"))

    def test_character_anchors_precede_image_prompts(self):
        self.assertLess(
            MODULE.STAGES.index("CHARACTER_ANCHORS"),
            MODULE.STAGES.index("IMAGE_PROMPTS"),
        )

    def test_guided_project_init_does_not_preconfirm_production_choices(self):
        root = self.test_root / "guided-init"
        result = subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "init_project.py"),
                str(root),
                "--title",
                "引导测试",
                "--guided",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        project = json.loads((root / "project.json").read_text(encoding="utf-8"))
        self.assertEqual("", project["voice"]["voice_id"])
        self.assertIsNone(project["settings"]["visual_style"])
        self.assertEqual([], project["publish"]["platforms"])
        self.assertFalse(project["approvals"]["settings_confirmed"])
        self.assertEqual([], MODULE.validate(project, root))

    def test_init_adds_workflow_without_replacing_existing_project_data(self):
        root = self.test_root / "legacy-project"
        root.mkdir()
        original = {"project": "旧项目", "approvals": {"qc_passed": False}}
        (root / "project.json").write_text(
            json.dumps(original, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self.assertEqual(0, MODULE.command_init(argparse.Namespace(project_root=root)))
        updated = json.loads((root / "project.json").read_text(encoding="utf-8"))
        self.assertEqual("旧项目", updated["project"])
        self.assertIn("workflow", updated)
        self.assertEqual([], MODULE.validate(updated, root))

    def test_migrate_v1_adds_character_anchor_stage(self):
        root = self.test_root / "migrate-v1"
        root.mkdir()
        project = self.create_project(root)
        project["workflow"]["schema_version"] = 1
        del project["workflow"]["stage_statuses"]["CHARACTER_ANCHORS"]
        (root / "project.json").write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self.assertEqual(0, MODULE.command_migrate(argparse.Namespace(project_root=root)))
        migrated = json.loads((root / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(2, migrated["workflow"]["schema_version"])
        self.assertEqual("未开始", migrated["workflow"]["stage_statuses"]["CHARACTER_ANCHORS"])
        self.assertEqual([], MODULE.validate(migrated, root))

    def test_future_stage_cannot_start_early(self):
        root = self.test_root / "future-stage"
        root.mkdir()
        project = self.create_project(root)
        project["workflow"]["stage_statuses"]["VOICE"] = "进行中"
        self.assertIn(
            "future-stage-already-started:VOICE:进行中",
            MODULE.validate(project, root),
        )

    def test_final_promotion_requires_release_evidence(self):
        root = self.test_root / "final-promotion"
        root.mkdir()
        project = self.create_project(root)
        statuses = project["workflow"]["stage_statuses"]
        for stage in MODULE.STAGES[: MODULE.STAGES.index("FINAL_PROMOTION")]:
            statuses[stage] = "已确认"
        project["workflow"]["current_stage"] = "FINAL_PROMOTION"
        project["workflow"]["next_stage"] = "FEEDBACK"
        statuses["FINAL_PROMOTION"] = "已确认"
        errors = MODULE.validate(project, root)
        self.assertIn("final-promotion-without-qc-passed", errors)
        self.assertIn("final-promotion-without-explicit-approval", errors)
        self.assertIn("final-promotion-without-final-file", errors)


if __name__ == "__main__":
    unittest.main()
