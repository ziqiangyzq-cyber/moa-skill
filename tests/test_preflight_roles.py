#!/usr/bin/env python3
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHTS = (
    ROOT / "bin" / "moa-preflight",
    ROOT / "runtimes" / "codex" / "bin" / "moa-preflight",
)


class PreflightRoleTests(unittest.TestCase):
    def run_preflight(self, preflight, roster_text, adapter_count=2):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapters = root / "adapters"
            adapters.mkdir()
            for index in range(adapter_count):
                adapter = adapters / f"{index}.sh"
                adapter.write_text("#!/bin/sh\n", encoding="utf-8")
                adapter.chmod(0o755)
            roster = root / "roster.yaml"
            roster.write_text(textwrap.dedent(roster_text), encoding="utf-8")
            return subprocess.run(
                [str(preflight), str(roster)],
                text=True,
                capture_output=True,
                check=False,
            )

    def assert_all_preflights_pass(self, roster_text):
        for preflight in PREFLIGHTS:
            with self.subTest(preflight=preflight):
                result = self.run_preflight(preflight, roster_text)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_all_preflights_reject(self, roster_text, message, adapter_count=2):
        for preflight in PREFLIGHTS:
            with self.subTest(preflight=preflight):
                result = self.run_preflight(preflight, roster_text, adapter_count)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stdout + result.stderr)

    def test_positive_worker_timeout_is_accepted(self):
        self.assert_all_preflights_pass("""
            workers:
              - name: aggregator
                vendor: openai
                adapter: adapters/0.sh
                timeout_seconds: 600
                role: [propose, aggregate]
              - name: reviewer
                vendor: anthropic
                adapter: adapters/1.sh
                role: [critique, final_review]
            aggregator: aggregator
            final_review: reviewer
        """)

    def test_invalid_worker_timeout_is_rejected(self):
        self.assert_all_preflights_reject("""
            workers:
              - name: aggregator
                vendor: openai
                adapter: adapters/0.sh
                timeout_seconds: 0
                role: [propose, aggregate]
              - name: reviewer
                vendor: anthropic
                adapter: adapters/1.sh
                role: [critique, final_review]
            aggregator: aggregator
            final_review: reviewer
        """, "timeout_seconds must be a positive number")

    def test_roster_requires_a_proposer(self):
        self.assert_all_preflights_reject("""
            workers:
              - name: aggregator
                vendor: openai
                adapter: adapters/0.sh
                role: [critique, aggregate]
              - name: reviewer
                vendor: anthropic
                adapter: adapters/1.sh
                role: [critique, final_review]
            aggregator: aggregator
            final_review: reviewer
        """, "required `propose` role")

    def test_roster_requires_a_critic(self):
        self.assert_all_preflights_reject("""
            workers:
              - name: aggregator
                vendor: openai
                adapter: adapters/0.sh
                role: [propose, aggregate]
              - name: reviewer
                vendor: anthropic
                adapter: adapters/1.sh
                role: [propose, final_review]
            aggregator: aggregator
            final_review: reviewer
        """, "required `critique` role")

    def test_final_review_vendor_comparison_normalizes_case(self):
        self.assert_all_preflights_reject("""
            workers:
              - name: aggregator
                vendor: OpenAI
                adapter: adapters/0.sh
                role: [propose, aggregate]
              - name: critic
                vendor: anthropic
                adapter: adapters/1.sh
                role: [critique]
              - name: reviewer
                vendor: openai
                adapter: adapters/2.sh
                role: [final_review]
            aggregator: aggregator
            final_review: reviewer
        """, "cross-vendor review", adapter_count=3)


if __name__ == "__main__":
    unittest.main()
