"""Local JPEG preparation tests; no paid requests or production approvals."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, JpegImagePlugin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_compressed_images import prepare_render_images


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class WorkingImages(unittest.TestCase):
    def setUp(self):
        # Keep temporary fixtures; project rules prohibit recursive cleanup.
        self.root = Path(tempfile.mkdtemp(prefix="history-working-images-"))
        self.project = {"settings": {"canvas": {"width": 120, "height": 200}, "render_image_format": "jpeg", "render_jpeg_quality": 92, "render_jpeg_subsampling": "4:4:4"}, "approvals": {"paid_generation_confirmed": False, "qc_passed": False}}
        write(self.root / "project.json", self.project)
        write(self.root / "storyboards/frame-manifest.json", {"frames": [{"frame_id": "F01"}, {"frame_id": "F02"}]})
        self.timeline = {"fps": 30, "duration_frames": 240, "entries": [{"type": "image", "frame_id": f"F0{i+1}", "asset_file": f"frames/F0{i+1}.png", "start_frame": i*120, "end_frame": (i+1)*120, "duration_frames": 120} for i in range(2)]}
        write(self.root / "storyboards/timeline.json", self.timeline)
        (self.root / "assets/backgrounds").mkdir(parents=True)
        for i, color in enumerate(((120, 20, 30), (30, 50, 70)), 1):
            Image.new("RGB", (120, 200), color).save(self.root / f"assets/backgrounds/F0{i}.png")

    def test_dimensions_sampling_paths_and_originals(self):
        paths = [self.root / "project.json", *sorted((self.root / "assets/backgrounds").iterdir())]
        before = {p: p.read_bytes() for p in paths}
        result = prepare_render_images(self.root)
        self.assertEqual(result["frame_count"], 2)
        for p, value in before.items():
            self.assertEqual(p.read_bytes(), value)
        after = json.loads((self.root / "storyboards/timeline.json").read_text())
        for old, new in zip(self.timeline["entries"], after["entries"]):
            self.assertEqual({k:v for k,v in old.items() if k != "asset_file"}, {k:v for k,v in new.items() if k != "asset_file"})
            self.assertTrue(new["asset_file"].endswith(".jpg"))
            public = self.root / "remotion/public" / new["asset_file"]
            with Image.open(public) as image:
                self.assertEqual(image.size, (120, 200))
                self.assertEqual(JpegImagePlugin.get_sampling(image), 0)
        self.assertEqual(json.loads((self.root / "logs/timeline-before-working-jpeg.json").read_text()), self.timeline)

    def test_idempotent_without_recompression(self):
        prepare_render_images(self.root)
        files = list((self.root / "assets/render-images").iterdir())
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
        prepare_render_images(self.root)
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}, before)

    def test_repair_uses_new_canonical_not_stale_jpeg(self):
        prepare_render_images(self.root)
        jpeg = self.root / "assets/render-images/F01.jpg"
        old_hash = hashlib.sha256(jpeg.read_bytes()).hexdigest()
        Image.new("RGB", (120, 200), (200, 120, 70)).save(self.root / "assets/backgrounds/F01.png")
        prepare_render_images(self.root)
        self.assertNotEqual(hashlib.sha256(jpeg.read_bytes()).hexdigest(), old_hash)
        self.assertEqual(jpeg.read_bytes(), (self.root / "remotion/public/frames/F01.jpg").read_bytes())

    def test_missing_image_stops_before_outputs(self):
        write(self.root / "storyboards/frame-manifest.json", {"frames": [{"frame_id": "F01"}, {"frame_id": "MISSING"}]})
        with self.assertRaises(FileNotFoundError):
            prepare_render_images(self.root)
        self.assertFalse((self.root / "assets/render-images").exists())

    def test_modified_working_image_is_not_overwritten(self):
        prepare_render_images(self.root)
        jpeg = self.root / "assets/render-images/F01.jpg"
        jpeg.write_bytes(b"user modified file")
        with self.assertRaisesRegex(ValueError, "Untracked or modified"):
            prepare_render_images(self.root)
        self.assertEqual(jpeg.read_bytes(), b"user modified file")

    def test_legacy_project_is_unchanged(self):
        write(self.root / "project.json", {"settings": {}})
        self.assertEqual(prepare_render_images(self.root)["status"], "legacy_png_unchanged")
        self.assertFalse((self.root / "assets/render-images").exists())

    def test_wrong_size_or_alpha_is_rejected(self):
        Image.new("RGBA", (120, 200), (0, 0, 0, 0)).save(self.root / "assets/backgrounds/F01.png")
        with self.assertRaises(ValueError):
            prepare_render_images(self.root)
        self.assertFalse((self.root / "assets/render-images").exists())


if __name__ == "__main__":
    unittest.main()
