#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "runtimes" / "codex" / "adapters" / "codex.py"


class ResponsesHandler(BaseHTTPRequestHandler):
    requests = []
    response_payload = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "HTTP_ADAPTER_OK"}],
            }
        ],
    }

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.__class__.requests.append((self.path, dict(self.headers), body))
        raw = json.dumps(self.__class__.response_payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


class IncompleteResponsesHandler(ResponsesHandler):
    requests = []
    response_payload = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "PARTIAL_RESULT"}],
            }
        ],
    }


class CodexResponsesAdapterTests(unittest.TestCase):
    @staticmethod
    def clean_env():
        env = os.environ.copy()
        for name in list(env):
            if name.startswith("MOA_OPENAI_") or name in {
                "MOA_CODEX_MODEL",
                "MOA_CODEX_EFFORT",
                "CODEX_CONFIG_PATH",
            }:
                env.pop(name)
        return env

    def run_adapter(self, handler):
        self.assertTrue(ADAPTER.exists(), "Codex Responses adapter is not published")
        handler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                config = Path(temp) / "config.toml"
                config.write_text(
                    'model = "gpt-test"\n'
                    'model_provider = "test"\n'
                    '[model_providers.test]\n'
                    f'base_url = "http://127.0.0.1:{server.server_port}/v1"\n'
                    'env_key = "TEST_API_KEY"\n'
                    'wire_api = "responses"\n',
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [str(ADAPTER)],
                    input="committee prompt",
                    text=True,
                    capture_output=True,
                    env={
                        **self.clean_env(),
                        "CODEX_CONFIG_PATH": str(config),
                        "TEST_API_KEY": "test-secret",
                    },
                    check=False,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        return result

    def test_uses_tool_free_responses_request(self):
        result = self.run_adapter(ResponsesHandler)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "HTTP_ADAPTER_OK")
        self.assertEqual(len(ResponsesHandler.requests), 1)
        path, headers, body = ResponsesHandler.requests[0]
        self.assertEqual(path, "/v1/responses")
        self.assertEqual(headers["Authorization"], "Bearer test-secret")
        self.assertEqual(body["model"], "gpt-test")
        self.assertEqual(body["input"][0]["content"][0]["text"], "committee prompt")
        self.assertNotIn("tools", body)
        self.assertIs(body["store"], False)
        self.assertIs(body["stream"], False)

    def test_base_override_requires_matching_key_override(self):
        self.assertTrue(ADAPTER.exists(), "Codex Responses adapter is not published")
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.toml"
            config.write_text(
                'model = "gpt-test"\n'
                'model_provider = "test"\n'
                '[model_providers.test]\n'
                'base_url = "http://127.0.0.1:9/v1"\n'
                'env_key = "TEST_API_KEY"\n'
                'wire_api = "responses"\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(ADAPTER)],
                input="committee prompt",
                text=True,
                capture_output=True,
                env={
                    **self.clean_env(),
                    "CODEX_CONFIG_PATH": str(config),
                    "TEST_API_KEY": "provider-secret",
                    "MOA_OPENAI_BASE": "http://127.0.0.1:8/v1",
                },
                check=False,
            )

        self.assertEqual(result.returncode, 3)
        self.assertIn("MOA_OPENAI_API_KEY", result.stderr)

    def test_rejects_incomplete_response_with_partial_text(self):
        result = self.run_adapter(IncompleteResponsesHandler)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("incomplete", result.stderr)
        self.assertIn("max_output_tokens", result.stderr)


if __name__ == "__main__":
    unittest.main()
