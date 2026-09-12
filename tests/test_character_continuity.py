from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "generate_apimart_images.py"
SPEC = importlib.util.spec_from_file_location("generate_apimart_images", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CharacterContinuityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="character-continuity-tests-"))
        (self.root / "characters/anchors").mkdir(parents=True)

    def write_manifest(self, status: str) -> None:
        manifest = {
            "schema_version": 1,
            "style_preset": "qibaishi-xieyi",
            "characters": [
                {
                    "character_id": "C01",
                    "name": "测试人物",
                    "continuity": "strict",
                    "identity_prompt": "青年 瘦长脸 清初剃发留辫 青灰长衫",
                    "anchors": {
                        "face": "characters/anchors/C01-face.png",
                        "full_body": "characters/anchors/C01-full-body.png",
                    },
                    "status": status,
                }
            ],
        }
        (self.root / "characters/character-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )

    def test_strict_character_requires_confirmation(self):
        self.write_manifest("draft")
        with self.assertRaisesRegex(SystemExit, "strict character C01 is not confirmed"):
            MODULE.apply_character_locks(
                self.root,
                [{"frame_id": "F01", "prompt": "场景", "character_ids": ["C01"]}],
                "qibaishi-xieyi",
            )

    def test_confirmed_character_injects_prompt_and_both_anchors(self):
        self.write_manifest("confirmed")
        for name in ("C01-face.png", "C01-full-body.png"):
            (self.root / "characters/anchors" / name).write_bytes(b"test")
        frames = MODULE.apply_character_locks(
            self.root,
            [{"frame_id": "F01", "prompt": "场景", "character_ids": ["C01"]}],
            "qibaishi-xieyi",
        )
        self.assertIn("青年 瘦长脸", frames[0]["prompt"])
        self.assertEqual(
            [
                "characters/anchors/C01-face.png",
                "characters/anchors/C01-full-body.png",
            ],
            frames[0]["generation_reference_images"],
        )


if __name__ == "__main__":
    unittest.main()
