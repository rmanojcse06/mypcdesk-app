"""Smoke tests: tools are discovered, the server answers with a token and refuses without one.

Run:  python -m unittest discover tests
"""
import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import registry, server  # noqa: E402
from core.config import load_sections  # noqa: E402


class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = server.start_server()

    def get(self, path, token=True):
        req = urllib.request.Request(self.url.rstrip("/") + path)
        if token:
            req.add_header("X-MyDesk-Token", server.TOKEN)
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()

    def test_every_tool_is_valid(self):
        section_ids = {s["id"] for s in load_sections()}
        tools = registry.discover_tools()
        self.assertTrue(any(t["id"] == "clip_saver" for t in tools))
        for t in tools:
            self.assertIn(t["section"], section_ids, f"{t['id']} has unknown section {t['section']}")
            self.assertTrue(Path(t["script_path"]).exists())

    def test_build_args(self):
        tool = registry.get_tool("clip_saver")
        args = registry.build_args(tool, {"url": "https://x.test/v", "no-video": True, "cookies-from-browser": ""})
        self.assertEqual(args, ["https://x.test/v", "--no-video"])
        with self.assertRaises(ValueError):
            registry.build_args(tool, {"url": ""})

    def test_state_and_health(self):
        status, body = self.get("/api/state")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(json.loads(body)["sections"]), 8)
        status, body = self.get("/api/health")
        self.assertIn("cpu", json.loads(body))

    def test_requires_token(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/api/state", token=False)
        self.assertEqual(ctx.exception.code, 403)

    def test_no_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/files/clip_saver/..%2F..%2Fconfig.example.json")
        self.assertEqual(ctx.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
