#!/usr/bin/env python3
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-codex.sh"


class CodexInstallTests(unittest.TestCase):
    def run_installer(self, destination):
        self.assertTrue(INSTALLER.exists(), "Codex installer is not published")
        return subprocess.run(
            [str(INSTALLER), str(destination)],
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_managed_runtime(self, destination):
        expected = {
            "README.md",
            "SKILL.md",
            "agents/openai.yaml",
            "adapters/README.md",
            "adapters/codex.py",
            "adapters/codex.sh",
            "adapters/examples/claude-code.sh",
            "bin/moa-call",
            "bin/moa-preflight",
            "docs/DESIGN.md",
            "moa_decision.md",
            "prompts/proposer.md",
            "roster.example.yaml",
            "scripts/bootstrap-local.sh",
        }
        missing = sorted(path for path in expected if not (destination / path).is_file())
        self.assertEqual(missing, [])

        for path in (
            "adapters/codex.py",
            "adapters/codex.sh",
            "bin/moa-call",
            "bin/moa-preflight",
            "scripts/bootstrap-local.sh",
        ):
            self.assertTrue(os.access(destination / path, os.X_OK), path)

        self.assertEqual(
            (destination / "bin/moa-call").read_bytes(),
            (ROOT / "bin/moa-call").read_bytes(),
        )
        self.assertEqual(
            (destination / "adapters/codex.py").read_bytes(),
            (ROOT / "runtimes/codex/adapters/codex.py").read_bytes(),
        )

    def test_installs_managed_files_without_creating_private_state(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "moa"
            result = self.run_installer(destination)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_managed_runtime(destination)
            self.assertFalse((destination / "roster.yaml").exists())
            self.assertFalse((destination / "runs").exists())
            self.assertIn("bootstrap-local.sh", result.stdout)
            self.assertIn("moa-preflight", result.stdout)

    def test_update_preserves_private_runtime_state(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "moa"
            (destination / "runs").mkdir(parents=True)
            (destination / "adapters").mkdir()
            roster = destination / "roster.yaml"
            run_artifact = destination / "runs" / "sentinel.txt"
            custom_adapter = destination / "adapters" / "custom.sh"
            roster.write_bytes(b"PRIVATE_ROSTER\n")
            run_artifact.write_bytes(b"PRIVATE_RUN\n")
            custom_adapter.write_bytes(b"#!/bin/sh\nprintf CUSTOM\n")

            result = self.run_installer(destination)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_managed_runtime(destination)
            self.assertEqual(roster.read_bytes(), b"PRIVATE_ROSTER\n")
            self.assertEqual(run_artifact.read_bytes(), b"PRIVATE_RUN\n")
            self.assertEqual(
                custom_adapter.read_bytes(), b"#!/bin/sh\nprintf CUSTOM\n"
            )

    def test_bootstrap_creates_preflight_valid_two_vendor_roster(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "moa"
            result = self.run_installer(destination)
            self.assertEqual(result.returncode, 0, result.stderr)

            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_claude = fake_bin / "claude"
            fake_claude.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
            fake_claude.chmod(0o755)
            bootstrap = subprocess.run(
                [str(destination / "scripts/bootstrap-local.sh")],
                text=True,
                capture_output=True,
                env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
                check=False,
            )
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            roster = destination / "roster.yaml"
            self.assertTrue(roster.is_file())
            self.assertEqual(roster.stat().st_mode & 0o777, 0o600)

            preflight = subprocess.run(
                [str(destination / "bin/moa-preflight"), str(roster)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(preflight.returncode, 0, preflight.stderr)
            self.assertIn("2 distinct vendor(s)", preflight.stdout)

    def test_rejects_a_symbolic_link_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "claude-runtime"
            target.mkdir()
            sentinel = target / "SKILL.md"
            sentinel.write_bytes(b"CLAUDE_SENTINEL\n")
            destination = root / "codex-runtime"
            destination.symlink_to(target, target_is_directory=True)

            result = self.run_installer(destination)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symbolic link", result.stderr)
            self.assertEqual(sentinel.read_bytes(), b"CLAUDE_SENTINEL\n")

    def test_rejects_installing_over_the_source_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp) / "checkout"
            shutil.copytree(
                ROOT,
                checkout,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            sentinel = (checkout / "SKILL.md").read_bytes()

            result = subprocess.run(
                [str(checkout / "scripts/install-codex.sh"), str(checkout)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source checkout", result.stderr)
            self.assertEqual((checkout / "SKILL.md").read_bytes(), sentinel)


if __name__ == "__main__":
    unittest.main()
