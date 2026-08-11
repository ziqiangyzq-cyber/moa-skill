from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def make_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class VendorCliAdapterTests(unittest.TestCase):
    def test_agy_worker_is_sandboxed_and_forwards_model_and_effort(self) -> None:
        adapter = ROOT / "adapters/examples/agy-cli.sh"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake = root / "fake-agy"
            args_file = root / "args.json"
            make_executable(
                fake,
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "with open(os.environ['MOA_TEST_ARGS_FILE'], 'w') as f:\n"
                "    json.dump(sys.argv[1:], f)\n"
                "print('AGY_OK')\n",
            )
            env = {
                **os.environ,
                "MOA_AGY_BIN": str(fake),
                "MOA_AGY_MODEL": "gemini-test-high",
                "MOA_AGY_EFFORT": "high",
                "MOA_TEST_ARGS_FILE": str(args_file),
            }
            result = subprocess.run(
                [str(adapter)],
                input="committee prompt",
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            args = json.loads(args_file.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "AGY_OK\n")
        self.assertIn("committee prompt", args)
        self.assertIn("gemini-test-high", args)
        self.assertIn("high", args)
        self.assertIn("--sandbox", args)
        self.assertIn("--disable-slash-commands", args)

    def test_grok_worker_uses_prompt_file_and_disables_tools(self) -> None:
        adapter = ROOT / "adapters/examples/grok-cli.sh"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake = root / "fake-grok"
            capture_file = root / "capture.json"
            make_executable(
                fake,
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "prompt_path = pathlib.Path(args[args.index('--prompt-file') + 1])\n"
                "with open(os.environ['MOA_TEST_CAPTURE_FILE'], 'w') as f:\n"
                "    json.dump({'args': args, 'prompt': prompt_path.read_text()}, f)\n"
                "print('GROK_OK')\n",
            )
            env = {
                **os.environ,
                "MOA_GROK_BIN": str(fake),
                "MOA_GROK_MODEL": "grok-test",
                "MOA_TEST_CAPTURE_FILE": str(capture_file),
            }
            result = subprocess.run(
                [str(adapter)],
                input="committee prompt",
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            capture = json.loads(capture_file.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "GROK_OK\n")
        self.assertEqual(capture["prompt"], "committee prompt")
        self.assertIn("--prompt-file", capture["args"])
        self.assertIn("--disable-web-search", capture["args"])
        self.assertIn("--no-memory", capture["args"])
        self.assertIn("--no-subagents", capture["args"])
        self.assertIn("grok-test", capture["args"])


if __name__ == "__main__":
    unittest.main()
