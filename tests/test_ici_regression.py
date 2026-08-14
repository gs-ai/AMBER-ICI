from __future__ import annotations

import sys
import base64
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILES_ROOT = PROJECT_ROOT / "files"
if str(FILES_ROOT) not in sys.path:
    sys.path.insert(0, str(FILES_ROOT))

import launch_amber_ici_gui as launcher
from autogen_builder import AutoGenError, _post_json as autogen_post_json
from constrained_executor import ContractError, _post_json as executor_post_json


class ICIRegressionTests(unittest.TestCase):
    def test_release_identity_is_v5(self):
        package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(launcher.AMBER_VERSION, "5.0.0")
        self.assertEqual(launcher.AMBER_RELEASE, "AMBER ICI v5")
        self.assertEqual(package["version"], "5.0.0")

    def test_protected_ui_identity_and_controls_remain(self):
        ui = (FILES_ROOT / "amber_ui.html").read_text(encoding="utf-8")
        required = [
            "AMBER", "INVESTIGATIVE COMMAND INTERFACE v5", "ANALYST CONSOLE",
            "PARALLEL", "ARCHIVE", "MODELS", "FILES", "AGENTS", "SEND",
            "STOP", "PING", "GRAPH", "TIMELINE", "VECTORS", "WEB",
            "GENERATE FROM PROMPT", "ADD TO ARCHIVE", "SEARCH ARCHIVE",
        ]
        for label in required:
            self.assertIn(label, ui)

    def test_existing_storage_and_network_defaults_remain(self):
        self.assertEqual(launcher.STORE_DIR, "state")
        self.assertEqual(launcher.MAX_UPLOAD_BYTES, 100 * 1024 * 1024)
        ui = (FILES_ROOT / "amber_ui.html").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:11434", ui)
        self.assertIn("LOCAL_ONLY_HOSTS", ui)

    def test_backend_model_helpers_reject_non_loopback_urls(self):
        with self.assertRaises(AutoGenError):
            autogen_post_json("https://example.com/api/chat", {})
        with self.assertRaises(ContractError):
            executor_post_json("https://example.com/api/chat", {})
        with self.assertRaises(AutoGenError):
            autogen_post_json("http://user:secret@127.0.0.1:11434/api/chat", {})

    def test_new_routes_are_additive(self):
        source = (FILES_ROOT / "launch_amber_ici_gui.py").read_text(encoding="utf-8")
        for route in ("agent-templates", "cases", "evidence", "memory", "trace"):
            self.assertIn(route, source)
        for old_route in ("files", "vectors", "metrics", "web", "task", "autogen"):
            self.assertIn(old_route, source)

    def test_first_party_presentations_have_no_known_emoji(self):
        presentation_files = [
            FILES_ROOT / "amber_ui.html",
            FILES_ROOT / "amber_graph.html",
            FILES_ROOT / "amber_timeline.html",
            FILES_ROOT / "amber_vectorstore.html",
            FILES_ROOT / "launch_amber_ici_gui.py",
        ]
        disallowed = {"⚡", "⚠", "🤖", "🚀", "📄", "📝", "📕", "📘", "⏹", "✕", "✅", "❌"}
        for path in presentation_files:
            text = path.read_text(encoding="utf-8")
            found = sorted(disallowed.intersection(text))
            self.assertEqual(found, [], f"emoji remains in {path.name}: {found}")


class ICIHTTPIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        launcher.STORAGE_ROOT = cls.temp_dir.name
        launcher._CASE_INTELLIGENCE = None
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), launcher.SilentHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp_dir.cleanup()
        launcher._CASE_INTELLIGENCE = None

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())

    def test_case_memory_and_template_routes(self):
        status, created = self.request("/api/cases", {"id": "http-case", "title": "HTTP Case"})
        self.assertEqual(status, 201)
        self.assertEqual(created["case"]["id"], "http-case")
        status, listed = self.request("/api/cases")
        self.assertEqual(status, 200)
        self.assertIn("http-case", {case["id"] for case in listed["cases"]})
        status, saved = self.request(
            "/api/memory",
            {"case_id": "http-case", "scope": "case", "source_kind": "operator", "content": "Preserve this note."},
        )
        self.assertEqual(status, 201)
        self.assertEqual(saved["memory"]["scope"], "case")
        status, templates = self.request("/api/agent-templates")
        self.assertEqual(status, 200)
        self.assertEqual(len(templates["templates"]), 6)

    def test_existing_upload_flows_into_case_evidence_and_search(self):
        self.request("/api/cases", {"id": "evidence-case", "title": "Evidence Case"})
        status, uploaded = self.request(
            "/api/files/upload",
            {"name": "receipt.txt", "data_b64": base64.b64encode(b"signed orchid receipt").decode("ascii")},
        )
        self.assertEqual(status, 200)
        file_id = uploaded["entry"]["id"]
        status, ingested = self.request(
            "/api/cases/evidence", {"case_id": "evidence-case", "file_ids": [file_id]}
        )
        self.assertEqual(status, 200)
        self.assertEqual(ingested["results"][0]["chunk_count"], 1)
        self.assertNotIn("chunks", ingested["results"][0])
        status, found = self.request(
            "/api/cases/search", {"case_id": "evidence-case", "query": "orchid", "top_k": 5}
        )
        self.assertEqual(status, 200)
        self.assertEqual(found["results"][0]["citation"]["filename"], "receipt.txt")


if __name__ == "__main__":
    unittest.main()
