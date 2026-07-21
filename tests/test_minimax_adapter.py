#!/usr/bin/env python3
import json
import os
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "examples" / "minimax.sh"


class MiniMaxHandler(BaseHTTPRequestHandler):
    requests = []
    response_payload = {
        "base_resp": {"status_code": 0, "status_msg": ""},
        "choices": [{"message": {"content": "MINIMAX_OK"}}],
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


class MiniMaxErrorHandler(MiniMaxHandler):
    requests = []
    response_payload = {
        "base_resp": {"status_code": 2049, "status_msg": "invalid key"},
        "choices": [],
    }


class MiniMaxAdapterTests(unittest.TestCase):
    def run_adapter(self, handler):
        handler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = subprocess.run(
                [str(ADAPTER)],
                input="committee prompt",
                text=True,
                capture_output=True,
                env={
                    **os.environ,
                    "MOA_MINIMAX_API_KEY": "test-secret",
                    "MOA_MINIMAX_API_BASE": f"http://127.0.0.1:{server.server_port}",
                    "MOA_MINIMAX_MODEL": "MiniMax-M3",
                },
                check=False,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        return result

    def test_calls_m3_without_exposing_reasoning(self):
        result = self.run_adapter(MiniMaxHandler)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "MINIMAX_OK\n")
        self.assertEqual(len(MiniMaxHandler.requests), 1)
        path, headers, body = MiniMaxHandler.requests[0]
        self.assertEqual(path, "/v1/text/chatcompletion_v2")
        self.assertEqual(headers["Authorization"], "Bearer test-secret")
        self.assertEqual(body["model"], "MiniMax-M3")
        self.assertEqual(body["messages"], [{"role": "user", "content": "committee prompt"}])

    def test_rejects_api_error_hidden_inside_http_200(self):
        result = self.run_adapter(MiniMaxErrorHandler)

        self.assertEqual(result.returncode, 70)
        self.assertEqual(result.stdout, "")
        self.assertIn("API error code 2049", result.stderr)
        self.assertNotIn("invalid key", result.stderr)


if __name__ == "__main__":
    unittest.main()
