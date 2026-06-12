import tempfile
import unittest
from pathlib import Path

from pointless_revision.transcripts import (
    build_script,
    episode_file,
    iter_episode_files,
    parse_segments,
)


SAMPLE_SRT = """1
00:00:20,040 --> 00:00:22,400
<font color="#ffffff">Hello, I'm Alexander Armstrong</font>

2
00:00:22,400 --> 00:00:23,560
<font color="#ffffff">and welcome to Pointless.</font>

3
00:00:36,320 --> 00:00:38,000
<font color="#00ffff">My name's Kelly.</font>
<font color="#00ffff">I'm from Shropshire.</font>

4
00:03:44,360 --> 00:03:47,120
<font color="#00ffff">From GCSE to A-level.</font><font color="#ffffff"> Right,</font>
<font color="#ffffff">A-level.</font>

5
00:15:03,160 --> 00:15:04,720
<font color="#ffff00">There were no pointless answers,</font>
"""


class TranscriptParsingTests(unittest.TestCase):
    def test_segments_attribute_speakers_by_colour(self):
        segments = parse_segments(SAMPLE_SRT)
        speakers = [s.speaker for s in segments]
        self.assertEqual(
            speakers,
            ["HOST", "HOST", "CONTESTANT", "CONTESTANT", "CONTESTANT", "HOST", "HOST", "COHOST"],
        )
        self.assertEqual(segments[0].start_seconds, 20.04)

    def test_mixed_colour_line_splits_into_two_speakers(self):
        segments = parse_segments(SAMPLE_SRT)
        self.assertIn(("CONTESTANT", "From GCSE to A-level."), [(s.speaker, s.text) for s in segments])
        self.assertIn(("HOST", "Right,"), [(s.speaker, s.text) for s in segments])

    def test_script_groups_consecutive_speaker_turns(self):
        script = build_script(parse_segments(SAMPLE_SRT))
        lines = script.splitlines()
        self.assertEqual(
            lines[0],
            "[00:20] HOST: Hello, I'm Alexander Armstrong and welcome to Pointless.",
        )
        self.assertEqual(lines[1], "[00:36] CONTESTANT: My name's Kelly. I'm from Shropshire. From GCSE to A-level.")
        self.assertTrue(lines[-1].startswith("[15:03] COHOST: There were no pointless answers,"))


class EpisodeFileTests(unittest.TestCase):
    def test_filename_metadata(self):
        ep = episode_file(Path("pointless-s34e01-m002jwx4.srt"))
        self.assertIsNotNone(ep)
        self.assertEqual(ep.episode_id, "s34e01")
        self.assertEqual(ep.episode_label, "Series 34 Episode 1")
        self.assertEqual(ep.bbc_url, "https://www.bbc.co.uk/programmes/m002jwx4")

    def test_partial_downloads_are_skipped(self):
        self.assertIsNone(episode_file(Path("pointless-s35e33-m002wm6q.partial.srt")))

    def test_iter_dedupes_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "s34").mkdir()
            (root / "test").mkdir()
            (root / "s34" / "pointless-s34e02-m0000002.srt").write_text("x")
            (root / "s34" / "pointless-s34e01-m0000001.srt").write_text("x")
            (root / "test" / "pointless-s34e01-m0000001.srt").write_text("x")
            (root / "s34" / "pointless-s34e03-m0000003.partial.srt").write_text("x")
            eps = iter_episode_files(root)
            self.assertEqual([ep.episode_id for ep in eps], ["s34e01", "s34e02"])


if __name__ == "__main__":
    unittest.main()
