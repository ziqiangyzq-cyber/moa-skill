from __future__ import annotations

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
        self.assertNotIn("dangerously-bypass-approvals-and-sandbox", text)


if __name__ == "__main__":
    unittest.main()
