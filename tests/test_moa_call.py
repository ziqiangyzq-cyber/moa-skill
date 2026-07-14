#!/usr/bin/env python3
import os
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOA_CALL = ROOT / "bin" / "moa-call"


class MoaCallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_adapter(self, body):
        path = self.root / "adapter.sh"
        path.write_text("#!/bin/sh\nset -eu\n" + body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_success_returns_adapter_output(self):
        adapter = self.make_adapter("cat >/dev/null\nprintf WRAPPER_OK\n")
        result = subprocess.run(
            [str(MOA_CALL), str(adapter)],
            input="prompt",
            text=True,
            capture_output=True,
            env={**os.environ, "MOA_TIMEOUT": "5"},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "WRAPPER_OK")

    def test_timeout_allows_exit_trap_to_remove_prompt_file(self):
        leak = self.root / "prompt.txt"
        adapter = self.make_adapter(
            "trap 'rm -f \"$LEAK_FILE\"' EXIT TERM INT\n"
            "cat > \"$LEAK_FILE\"\n"
            "sleep 5\n"
        )
        start = time.monotonic()
        result = subprocess.run(
            [str(MOA_CALL), str(adapter)],
            input="confidential prompt",
            text=True,
            capture_output=True,
            env={**os.environ, "MOA_TIMEOUT": "0.3", "LEAK_FILE": str(leak)},
            timeout=3,
            check=False,
        )
        elapsed = time.monotonic() - start
        self.assertEqual(result.returncode, 124, result.stdout + result.stderr)
        self.assertLess(elapsed, 2.0)
        self.assertFalse(leak.exists(), "timeout left the prompt file on disk")

    def test_sigterm_stops_adapter_process_group(self):
        heartbeat = self.root / "heartbeat.txt"
        pid_file = self.root / "adapter.pid"
        adapter = self.make_adapter(
            'printf "%s" "$$" > "$ADAPTER_PID_FILE"\n'
            'while :; do printf x >> "$HEARTBEAT_FILE"; sleep 0.05; done\n'
        )
        process = subprocess.Popen(
            [str(MOA_CALL), str(adapter)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **os.environ,
                "MOA_TIMEOUT": "30",
                "HEARTBEAT_FILE": str(heartbeat),
                "ADAPTER_PID_FILE": str(pid_file),
            },
            start_new_session=True,
        )
        adapter_pid = None
        adapter_pgid = None
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if pid_file.exists() and heartbeat.exists() and heartbeat.stat().st_size >= 2:
                    adapter_pid = int(pid_file.read_text())
                    adapter_pgid = os.getpgid(adapter_pid)
                    break
                time.sleep(0.05)
            self.assertIsNotNone(adapter_pid, "adapter did not start")

            os.kill(process.pid, signal.SIGTERM)
            returncode = process.wait(timeout=3)
            diagnostic = ""
            if returncode != 143 and process.stderr is not None:
                os.set_blocking(process.stderr.fileno(), False)
                diagnostic = os.read(process.stderr.fileno(), 65536).decode(
                    errors="replace"
                )
            self.assertEqual(returncode, 143, diagnostic)

            stopped_size = heartbeat.stat().st_size
            time.sleep(0.3)
            self.assertEqual(heartbeat.stat().st_size, stopped_size)
            with self.assertRaises(ProcessLookupError):
                os.killpg(adapter_pgid, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)
            if adapter_pgid is not None:
                try:
                    os.killpg(adapter_pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
