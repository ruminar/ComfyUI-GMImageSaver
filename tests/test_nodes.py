import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import nodes


class _FakeImageTensor:
    def __init__(self):
        self._array = np.zeros((2, 2, 3), dtype=np.float32)

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self._array


class CommentNormalizationTests(unittest.TestCase):
    def test_removes_bom_nul_and_unsafe_control_characters(self):
        result = nodes._normalize_comment_bytes(
            "\ufeffhello\x00world\x01\tline\n日本語😀"
        )

        self.assertEqual(result, "helloworld\tline\n日本語😀".encode("utf-8"))

    def test_truncates_at_utf8_character_boundary(self):
        result = nodes._normalize_comment_bytes("あ" * 30000)

        self.assertLessEqual(len(result), nodes.MAX_JPEG_COMMENT_BYTES)
        result.decode("utf-8")


class CommentFileTests(unittest.TestCase):
    def _save_with_mocked_gm(self, comment, run_side_effect=None):
        captured = {}
        self.captured = captured

        def fake_run(cmd, **kwargs):
            comment_arg = cmd[cmd.index("-comment") + 1]
            captured["path"] = comment_arg[1:]
            captured["bytes"] = Path(captured["path"]).read_bytes()
            if run_side_effect:
                raise run_side_effect
            return subprocess.CompletedProcess(cmd, 0, b"", b"")

        with tempfile.TemporaryDirectory() as output_dir:
            with mock.patch.object(nodes, "_resolve_gm_command", return_value="gm"):
                with mock.patch.object(nodes.subprocess, "run", side_effect=fake_run):
                    nodes.GMImageJpegSave().save_images(
                        [_FakeImageTensor()],
                        "test",
                        "none",
                        "none",
                        80,
                        "4:2:2",
                        False,
                        output_dir=output_dir,
                        comment=comment,
                    )

        return captured

    def test_passes_long_utf8_comment_through_a_temp_file(self):
        comment = "日本語😀" + ("A" * 5000)

        captured = self._save_with_mocked_gm(comment)

        self.assertEqual(captured["bytes"], comment.encode("utf-8"))
        self.assertFalse(os.path.exists(captured["path"]))

    def test_does_not_create_temp_file_without_comment(self):
        commands = []

        def fake_run(cmd, **kwargs):
            commands.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, b"", b"")

        with tempfile.TemporaryDirectory() as output_dir:
            with mock.patch.object(nodes, "_resolve_gm_command", return_value="gm"):
                with mock.patch.object(nodes, "_write_temp_comment_file") as writer:
                    with mock.patch.object(
                        nodes.subprocess,
                        "run",
                        side_effect=fake_run,
                    ):
                        nodes.GMImageJpegSave().save_images(
                            [_FakeImageTensor()],
                            "test",
                            "none",
                            "none",
                            80,
                            "4:2:2",
                            False,
                            output_dir=output_dir,
                            comment=None,
                        )

        writer.assert_not_called()
        self.assertNotIn("-comment", commands[0])

    def test_removes_temp_file_when_graphicsmagick_fails(self):
        with self.assertRaises(RuntimeError):
            self._save_with_mocked_gm(
                "prompt",
                run_side_effect=OSError("test failure"),
            )

        self.assertFalse(os.path.exists(self.captured["path"]))


if __name__ == "__main__":
    unittest.main()
