"""Regression checks for truncated long TTS responses, with no API calls."""
import unittest

from check_voice_alignment import check_alignment


class AlignmentChecks(unittest.TestCase):
    def check(self, chars, starts, ends, duration=2.0, text=None):
        return check_alignment({"characters": list(chars), "character_start_times_seconds": starts,
                                "character_end_times_seconds": ends}, chars if text is None else text, duration)

    def test_complete_text_with_clamped_tail_fails(self):
        report = self.check("全文仍在但未说完", [0, .2, .4, .6, 1, 1, 1, 1], [.2, .4, .6, 1, 1, 1, 1, 1], 1)
        self.assertFalse(report["technical_alignment_passed"])
        self.assertEqual(report["zero_duration_spoken_character_indices"], [4, 5, 6, 7])

    def test_valid_alignment_does_not_grant_release(self):
        report = self.check("甲，乙", [0, .5, .5], [.5, .5, 1])
        self.assertTrue(report["technical_alignment_passed"])
        self.assertFalse(report["release_approval"])

    def test_missing_and_mismatched_text(self):
        self.assertFalse(self.check("甲", [0], [.5], text="甲乙")["technical_alignment_passed"])
        self.assertFalse(self.check("甲乙", [0], [.5])["technical_alignment_passed"])

    def test_invalid_times_fail(self):
        for starts, ends in [([0, .5], [.5, 3]), ([.5, .1], [.8, .6]),
                             ([0, .5], [.5, .4]), ([0, float('nan')], [.5, 1])]:
            with self.subTest(starts=starts, ends=ends):
                self.assertFalse(self.check("甲乙", starts, ends)["technical_alignment_passed"])

    def test_bad_duration_and_empty_arrays_fail(self):
        self.assertFalse(self.check("甲", [0], [.5], duration=float('inf'))["technical_alignment_passed"])
        self.assertFalse(self.check("", [], [])["technical_alignment_passed"])


if __name__ == "__main__":
    unittest.main()
