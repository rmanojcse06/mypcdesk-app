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

    def test_mycheats_viewer_and_dialogs(self):
        status, body = self.get("/api/tool-items?tool=mycheats")
        names = {x["name"] for x in json.loads(body)}
        self.assertTrue({"git", "windows-cmd", "powershell"} <= names)
        status, body = self.get(server.page_url("mycheats", "git").split("?")[0] + "?t=" + server.TOKEN, token=False)
        self.assertIn(b"git switch -c", body)
        req = urllib.request.Request(self.url + "api/dialogs/open", method="POST",
                                     data=json.dumps({"tool": "mycheats", "name": "git"}).encode(),
                                     headers={"X-MyDesk-Token": server.TOKEN, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            opened = json.loads(r.read())
        self.assertTrue(opened["inline"])  # no desktop window in tests -> in-page dialog
        status, body = self.get("/api/dialogs")
        self.assertEqual(len(json.loads(body)), 1)
        req = urllib.request.Request(self.url + "api/dialogs/close", method="POST", data=b'{"all": true}',
                                     headers={"X-MyDesk-Token": server.TOKEN, "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        status, body = self.get("/api/dialogs")
        self.assertEqual(json.loads(body), [])

    def test_bad_page_name_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/page/mycheats/..%2F..%2Fconfig")
        self.assertEqual(ctx.exception.code, 404)

    def test_mailbox_and_heartbeat(self):
        sys.path.insert(0, str(ROOT / "remote"))
        import ask_mydesk
        import pc_status
        from core import heartbeat
        r = ask_mydesk.ask(ROOT, {"action": "ping"}, timeout=15)
        self.assertTrue(r["ok"], r)
        r = ask_mydesk.ask(ROOT, {"action": "rm -rf /"}, timeout=15)
        self.assertFalse(r["ok"])
        self.assertIn("not allowed", r["error"])
        r = ask_mydesk.ask(ROOT, {"action": "run_tool", "tool": "nope"}, timeout=15)
        self.assertFalse(r["ok"])
        heartbeat.write_status()
        status = json.loads(heartbeat.STATUS_FILE.read_text())
        self.assertEqual(pc_status.verdict(status)[0], 0)
        self.assertEqual(pc_status.verdict(status, now=status["last_seen_epoch"] + 600)[0], 1)
        self.assertEqual(pc_status.verdict(status, now=status["last_seen_epoch"] + 7200)[0], 2)
        self.assertEqual(pc_status.verdict(None)[0], 2)

    def test_keep_awake_rules(self):
        from core.keepawake import decide
        now = 1_000_000
        self.assertFalse(decide("claude-running", False, True, True, now, now)[0])          # battery: never
        self.assertTrue(decide("claude-running", True, True, False, 0, now)[0])            # charger + Claude open
        self.assertFalse(decide("claude-running", True, False, False, 0, now)[0])          # Claude closed
        self.assertTrue(decide("claude-busy", True, True, True, now, now)[0])              # busy
        self.assertTrue(decide("claude-busy", True, True, False, now - 300, now)[0])       # grace period
        self.assertFalse(decide("claude-busy", True, True, False, now - 3600, now)[0])     # grace over
        self.assertTrue(decide("off", True, False, False, 0, now, hold_until=now + 60)[0]) # timer
        self.assertTrue(decide("off", True, False, False, 0, now, hold_alive=True)[0])     # wait for program
        self.assertFalse(decide("off", False, False, False, 0, now, hold_until=now + 60)[0])  # timer, but battery

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
