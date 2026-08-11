from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliAdapterDefaultTests(unittest.TestCase):
    def test_bootstrap_protects_private_roster(self) -> None:
        text = (ROOT / "scripts/bootstrap-local.sh").read_text(encoding="utf-8")
        self.assertIn('chmod 600 "$root/roster.yaml"', text)

    def test_claude_worker_has_no_tools_or_permission_bypass(self) -> None:
        text = (ROOT / "adapters/examples/claude-code.sh").read_text(encoding="utf-8")
        self.assertIn('--tools\n  ""', text)
        self.assertIn("--bare", text)
        self.assertNotIn("bypassPermissions", text)

    def test_codex_worker_is_ephemeral_and_sandboxed(self) -> None:
        text = (ROOT / "adapters/examples/codex-cli.sh").read_text(encoding="utf-8")
        for expected in (
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            'work_dir="$(mktemp -d)"',
        ):
            self.assertIn(expected, text)
        self.assertIn('codex_bin="${MOA_CODEX_BIN:-codex}"', text)
        self.assertNotIn("dangerously-bypass-approvals-and-sandbox", text)

    def test_codex_worker_preserves_cli_failure_code(self) -> None:
        adapter = ROOT / "adapters/examples/codex-cli.sh"
        with tempfile.TemporaryDirectory() as temp_dir:
            fake = Path(temp_dir) / "fake-codex"
            fake.write_text("#!/usr/bin/env bash\nexit 17\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            env = {**os.environ, "MOA_CODEX_BIN": str(fake)}
            result = subprocess.run(
                [str(adapter)],
                input="test prompt",
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
        self.assertEqual(result.returncode, 17)
        self.assertIn("codex adapter failed (exit 17)", result.stderr)

    def test_codex_worker_forwards_reasoning_effort(self) -> None:
        adapter = ROOT / "adapters/examples/codex-cli.sh"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake = root / "fake-codex"
            args_file = root / "args.txt"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                ': > "$MOA_TEST_ARGS_FILE"\n'
                "out_file=''\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  printf '%s\\n' \"$1\" >> \"$MOA_TEST_ARGS_FILE\"\n"
                "  if [ \"$1\" = '--output-last-message' ]; then\n"
                "    shift\n"
                "    out_file=\"$1\"\n"
                "    printf '%s\\n' \"$1\" >> \"$MOA_TEST_ARGS_FILE\"\n"
                "  fi\n"
                "  shift\n"
                "done\n"
                "printf 'CODEX_OK\\n' > \"$out_file\"\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            env = {
                **os.environ,
                "MOA_CODEX_BIN": str(fake),
                "MOA_CODEX_MODEL": "gpt-test",
                "MOA_CODEX_EFFORT": "ultra",
                "MOA_TEST_ARGS_FILE": str(args_file),
            }
            result = subprocess.run(
                [str(adapter)],
                input="test prompt",
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            args = args_file.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "CODEX_OK\n")
        self.assertIn("gpt-test", args)
        self.assertIn("model_reasoning_effort=ultra", args)


if __name__ == "__main__":
    unittest.main()
