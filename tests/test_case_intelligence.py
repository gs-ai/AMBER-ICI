from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILES_ROOT = PROJECT_ROOT / "files"
if str(FILES_ROOT) not in sys.path:
    sys.path.insert(0, str(FILES_ROOT))

from amber_intelligence import CaseIntelligence, IntelligenceError, investigation_role_templates
from amber_intelligence.contracts import sha256_bytes
from amber_intelligence.retrieval import chunk_text


class CaseIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.service = CaseIntelligence(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_case_evidence_hash_and_duplicate_are_deterministic(self):
        self.service.create_case("Alpha Investigation", "alpha")
        raw = b"source bytes"
        first = self.service.ingest_evidence(
            case_id="alpha",
            file_id="UP_1",
            filename="source.txt",
            media_type="txt",
            raw=raw,
            extracted_text="Observed amber vehicle near the location.",
            source_type="upload",
        )
        second = self.service.ingest_evidence(
            case_id="alpha",
            file_id="UP_1",
            filename="source.txt",
            media_type="txt",
            raw=raw,
            extracted_text="Observed amber vehicle near the location.",
            source_type="upload",
        )
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["artifact"]["sha256"], sha256_bytes(raw))
        self.assertEqual(len(self.service.list_evidence("alpha")), 1)

    def test_retrieval_never_crosses_case_boundary(self):
        for case_id, phrase in (("alpha", "orchid ledger"), ("beta", "cobalt invoice")):
            self.service.create_case(case_id.title(), case_id)
            self.service.ingest_evidence(
                case_id=case_id,
                file_id=f"UP_{case_id}",
                filename=f"{case_id}.txt",
                media_type="txt",
                raw=phrase.encode(),
                extracted_text=phrase,
                source_type="upload",
            )
        alpha = self.service.search_case("alpha", "orchid", 5)
        beta = self.service.search_case("beta", "orchid", 5)
        self.assertEqual(alpha[0]["citation"]["filename"], "alpha.txt")
        self.assertEqual(beta, [])

    def test_memory_is_explicit_scoped_and_source_labeled(self):
        self.service.create_case("Alpha Investigation", "alpha")
        saved = self.service.remember(
            content="Review the signed receipt before concluding.",
            scope="case",
            case_id="alpha",
            source_kind="operator",
            importance=0.8,
            tags=["receipt", "review"],
        )
        self.assertFalse(saved["duplicate"])
        hits = self.service.recall(query="signed receipt", scope="case", case_id="alpha")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["source_kind"], "operator")
        with self.assertRaises(IntelligenceError):
            self.service.remember(content="unowned", scope="case", source_kind="operator")
        with self.assertRaises(IntelligenceError):
            self.service.remember(
                content="invalid importance",
                scope="case",
                case_id="alpha",
                source_kind="operator",
                importance=float("nan"),
            )

    def test_memory_scope_is_bounded(self):
        self.service.create_case("Alpha Investigation", "alpha")
        with patch("amber_intelligence.service.MAX_MEMORIES_PER_SCOPE", 2):
            for index in range(3):
                self.service.remember(
                    content=f"memory {index}",
                    scope="case",
                    case_id="alpha",
                    source_kind="operator",
                    importance=index / 10,
                )
        state = self.service.store.read()
        self.assertEqual(len(state["memories"]), 2)
        self.assertNotIn("memory 0", {item["content"] for item in state["memories"]})

    def test_agent_trace_is_not_evidence_or_memory(self):
        self.service.create_case("Alpha Investigation", "alpha")
        trace = self.service.record_trace(
            {"case_id": "alpha", "agent_id": "a1", "agent_name": "Analyst", "model": "local", "status": "completed"}
        )
        state = self.service.store.read()
        self.assertEqual(trace["output_kind"], "model_output")
        self.assertEqual(state["evidence"]["alpha"], [])
        self.assertEqual(state["memories"], [])
        with self.assertRaises(IntelligenceError):
            self.service.record_trace({"status": "completed", "input_refs": "not-a-list"})

    def test_corrupt_store_is_quarantined(self):
        path = self.root / "state" / "case_intelligence.json"
        path.parent.mkdir(parents=True)
        path.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.service.list_cases(), [])
        self.assertTrue(list(path.parent.glob("case_intelligence.corrupt-*.json")))

    def test_role_templates_are_optional_and_complete(self):
        templates = investigation_role_templates()
        self.assertEqual([item["name"] for item in templates], [
            "Director", "Researcher", "Investigator", "Analyst", "Documenter", "Critic"
        ])
        self.assertTrue(all("model" not in item for item in templates))

    def test_chunking_is_bounded_and_non_recursive(self):
        chunks = chunk_text("word " * 2_000, size=800, overlap=100)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(1 <= len(chunk) <= 800 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
