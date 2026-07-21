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


if __name__ == "__main__":
    unittest.main()
