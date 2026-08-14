"""AMBER-owned case, evidence, memory, retrieval, and trace service."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

from .contracts import (
    artifact_contract,
    artifact_identity,
    artifact_identity_file,
    new_id,
    normalize_case_id,
    source_contract,
    utc_now,
)
from .retrieval import build_chunks, search_chunks, tokenize
from .storage import AtomicJSONStore


MAX_EXTRACTED_CHARS = 5_000_000
MAX_CASE_SUMMARY_CHARS = 10_000
MAX_MEMORIES_PER_SCOPE = 500
MAX_TRACES = 2_000
MEMORY_SCOPES = {"session", "investigator", "case", "agent", "reasoning"}
MEMORY_SOURCE_KINDS = {"operator", "model_output", "evidence_summary"}


class IntelligenceError(ValueError):
    pass


class CaseIntelligence:
    """Facade used by the existing AMBER HTTP handler."""

    def __init__(self, project_root: Path):
        root = Path(project_root).resolve()
        self.store = AtomicJSONStore(root / "state" / "case_intelligence.json")

    def create_case(self, title: str, case_id: str = "", summary: str = "") -> dict:
        clean_title = str(title or "").strip()
        if len(clean_title) < 3 or len(clean_title) > 160:
            raise IntelligenceError("case title must be between 3 and 160 characters")
        clean_summary = str(summary or "").strip()
        if len(clean_summary) > MAX_CASE_SUMMARY_CHARS:
            raise IntelligenceError("case summary exceeds 10,000 characters")
        normalized = normalize_case_id(case_id or clean_title)
        now = utc_now()

        def mutate(state: dict) -> dict:
            if normalized in state["cases"]:
                raise IntelligenceError(f"case already exists: {normalized}")
            case = {
                "id": normalized,
                "title": clean_title,
                "summary": clean_summary,
                "created_at": now,
                "updated_at": now,
            }
            state["cases"][normalized] = case
            state["evidence"][normalized] = []
            return dict(case)

        return self.store.mutate(mutate)

    def ensure_case(self, case_id: str, title: str = "") -> dict:
        normalized = normalize_case_id(case_id)
        state = self.store.read()
        if normalized in state["cases"]:
            return dict(state["cases"][normalized])
        return self.create_case(title or normalized.replace("-", " ").title(), normalized)

    def list_cases(self) -> list[dict]:
        cases = list(self.store.read()["cases"].values())
        return sorted(cases, key=lambda case: case.get("updated_at", ""), reverse=True)

    def get_case(self, case_id: str) -> dict:
        normalized = normalize_case_id(case_id)
        state = self.store.read()
        case = state["cases"].get(normalized)
        if not case:
            raise IntelligenceError(f"unknown case: {normalized}")
        evidence = state["evidence"].get(normalized, [])
        return {**case, "evidence_count": len(evidence)}

    def ingest_evidence(
        self,
        *,
        case_id: str,
        file_id: str,
        filename: str,
        media_type: str,
        raw: bytes | None = None,
        raw_path: Path | None = None,
        extracted_text: str,
        source_type: str,
        captured_at: str = "",
    ) -> dict:
        normalized = normalize_case_id(case_id)
        if raw_path is not None:
            try:
                artifact_id, digest, byte_size = artifact_identity_file(Path(raw_path))
            except OSError as error:
                raise IntelligenceError(f"raw artifact is unavailable: {error}") from error
        else:
            raw = raw or b""
            if not raw:
                raise IntelligenceError("raw artifact is empty")
            artifact_id, digest = artifact_identity(raw)
            byte_size = len(raw)
        if byte_size <= 0:
            raise IntelligenceError("raw artifact is empty")
        now = utc_now()
        source_id = f"amber-file:{str(file_id or '').strip()}"
        source = source_contract(
            source_id=source_id,
            label=str(filename or "UNKNOWN"),
            source_type=str(source_type or "file"),
            captured_at=captured_at or now,
        )
        artifact = artifact_contract(
            artifact_id=artifact_id,
            sha256=digest,
            filename=str(filename or "UNKNOWN"),
            media_type=str(media_type or "unknown"),
            byte_size=byte_size,
            source_id=source_id,
            ingested_at=now,
        )
        text = str(extracted_text or "")
        truncated = len(text) > MAX_EXTRACTED_CHARS
        indexed_text = text[:MAX_EXTRACTED_CHARS]
        chunks = build_chunks(artifact_id, indexed_text)

        def mutate(state: dict) -> dict:
            if normalized not in state["cases"]:
                raise IntelligenceError(f"unknown case: {normalized}")
            evidence = state["evidence"].setdefault(normalized, [])
            duplicate = next((item for item in evidence if item["artifact"]["id"] == artifact_id), None)
            if duplicate:
                return {"duplicate": True, **duplicate}
            record = {
                "id": new_id("evidence"),
                "case_id": normalized,
                "kind": "source_artifact",
                "source": source,
                "artifact": artifact,
                "chunks": chunks,
                "processing": [
                    {
                        "id": new_id("event"),
                        "type": "ingest",
                        "at": now,
                        "input_artifact_id": artifact_id,
                        "output_kind": "observation_chunks",
                        "details": {
                            "chunk_count": len(chunks),
                            "text_truncated": truncated,
                            "original_text_chars": len(text),
                        },
                    }
                ],
            }
            evidence.append(record)
            state["cases"][normalized]["updated_at"] = now
            return {"duplicate": False, **record}

        return self.store.mutate(mutate)

    def list_evidence(self, case_id: str) -> list[dict]:
        normalized = normalize_case_id(case_id)
        state = self.store.read()
        if normalized not in state["cases"]:
            raise IntelligenceError(f"unknown case: {normalized}")
        return [self.public_evidence(item) for item in state["evidence"].get(normalized, [])]

    @staticmethod
    def public_evidence(record: dict) -> dict:
        public = {key: value for key, value in record.items() if key != "chunks"}
        public["chunk_count"] = len(record.get("chunks", []))
        return public

    def search_case(self, case_id: str, query: str, top_k: int = 8) -> list[dict]:
        normalized = normalize_case_id(case_id)
        clean_query = str(query or "").strip()
        if len(clean_query) < 2:
            raise IntelligenceError("search query must contain at least 2 characters")
        state = self.store.read()
        if normalized not in state["cases"]:
            raise IntelligenceError(f"unknown case: {normalized}")
        artifacts: dict[str, dict] = {}
        chunks: list[dict] = []
        for evidence in state["evidence"].get(normalized, []):
            artifact = evidence["artifact"]
            artifacts[artifact["id"]] = artifact
            chunks.extend(evidence.get("chunks", []))
        results = search_chunks(chunks, clean_query, top_k)
        for result in results:
            artifact = artifacts.get(result["artifact_id"], {})
            result["citation"] = {
                "case_id": normalized,
                "artifact_id": result["artifact_id"],
                "filename": artifact.get("filename", "UNKNOWN"),
                "sha256": artifact.get("sha256", ""),
                "chunk_id": result["id"],
            }
            result["excerpt"] = result.pop("text", "")[:900]
        return results

    def remember(
        self,
        *,
        content: str,
        scope: str,
        source_kind: str,
        case_id: str = "",
        agent_id: str = "",
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> dict:
        clean_content = str(content or "").strip()
        if not clean_content:
            raise IntelligenceError("memory content is required")
        if len(clean_content) > 20_000:
            raise IntelligenceError("memory content exceeds 20,000 characters")
        clean_scope = str(scope or "").strip().lower()
        if clean_scope not in MEMORY_SCOPES:
            raise IntelligenceError("unsupported memory scope")
        clean_source = str(source_kind or "").strip().lower()
        if clean_source not in MEMORY_SOURCE_KINDS:
            raise IntelligenceError("unsupported memory source kind")
        normalized_case = normalize_case_id(case_id) if case_id else ""
        if clean_scope == "case" and not normalized_case:
            raise IntelligenceError("case memory requires a case id")
        clean_agent_id = str(agent_id or "").strip()[:160]
        if clean_scope == "agent" and not clean_agent_id:
            raise IntelligenceError("agent memory requires an agent id")
        try:
            numeric_importance = float(importance)
        except (TypeError, ValueError) as error:
            raise IntelligenceError("memory importance must be a finite number") from error
        if not math.isfinite(numeric_importance):
            raise IntelligenceError("memory importance must be a finite number")
        bounded_importance = max(0.0, min(1.0, numeric_importance))
        if tags is not None and not isinstance(tags, list):
            raise IntelligenceError("memory tags must be a list")
        clean_tags = sorted({str(tag).strip().lower()[:80] for tag in (tags or []) if str(tag).strip()})[:20]
        now = utc_now()

        def mutate(state: dict) -> dict:
            if normalized_case and normalized_case not in state["cases"]:
                raise IntelligenceError(f"unknown case: {normalized_case}")
            duplicate = next(
                (
                    item
                    for item in state["memories"]
                    if item.get("scope") == clean_scope
                    and item.get("case_id", "") == normalized_case
                    and item.get("agent_id", "") == clean_agent_id
                    and item.get("content") == clean_content
                ),
                None,
            )
            if duplicate:
                return {"duplicate": True, **duplicate}
            memory = {
                "id": new_id("memory"),
                "scope": clean_scope,
                "case_id": normalized_case,
                "agent_id": clean_agent_id,
                "content": clean_content,
                "source_kind": clean_source,
                "importance": bounded_importance,
                "tags": clean_tags,
                "created_at": now,
                "last_accessed_at": None,
                "access_count": 0,
            }
            state["memories"].append(memory)
            matching = [
                item
                for item in state["memories"]
                if item.get("scope") == clean_scope
                and item.get("case_id", "") == normalized_case
                and item.get("agent_id", "") == clean_agent_id
            ]
            if len(matching) > MAX_MEMORIES_PER_SCOPE:
                keep_ids = {
                    item["id"]
                    for item in sorted(
                        matching,
                        key=lambda item: (item.get("importance", 0), item.get("created_at", "")),
                        reverse=True,
                    )[:MAX_MEMORIES_PER_SCOPE]
                }
                matching_ids = {item["id"] for item in matching}
                state["memories"] = [
                    item for item in state["memories"] if item["id"] not in matching_ids or item["id"] in keep_ids
                ]
            return {"duplicate": False, **memory}

        return self.store.mutate(mutate)

    def recall(
        self,
        *,
        query: str,
        scope: str,
        case_id: str = "",
        agent_id: str = "",
        top_k: int = 8,
    ) -> list[dict]:
        clean_scope = str(scope or "").strip().lower()
        if clean_scope not in MEMORY_SCOPES:
            raise IntelligenceError("unsupported memory scope")
        normalized_case = normalize_case_id(case_id) if case_id else ""
        query_terms = Counter(tokenize(query))
        state = self.store.read()
        candidates = [
            item
            for item in state["memories"]
            if item.get("scope") == clean_scope
            and (not normalized_case or item.get("case_id") == normalized_case)
            and (not agent_id or item.get("agent_id") == agent_id)
        ]
        scored = []
        for memory in candidates:
            terms = Counter(tokenize(memory.get("content", "")))
            overlap = sum(min(count, terms.get(term, 0)) for term, count in query_terms.items())
            score = overlap + float(memory.get("importance", 0))
            if not query_terms or score > float(memory.get("importance", 0)):
                scored.append((score, memory.get("created_at", ""), memory))
        limit = max(1, min(int(top_k), 50))
        results = [
            dict(item)
            for _, _, item in sorted(scored, key=lambda row: (row[0], row[1], row[2]["id"]), reverse=True)[:limit]
        ]
        if results:
            ids = {item["id"] for item in results}
            now = utc_now()

            def mark_accessed(current: dict) -> None:
                for item in current["memories"]:
                    if item.get("id") in ids:
                        item["last_accessed_at"] = now
                        item["access_count"] = int(item.get("access_count", 0)) + 1

            self.store.mutate(mark_accessed)
        return results

    def record_trace(self, payload: dict[str, Any]) -> dict:
        allowed_status = {"started", "completed", "failed", "stopped"}
        status = str(payload.get("status", "completed")).strip().lower()
        if status not in allowed_status:
            raise IntelligenceError("unsupported trace status")
        input_refs = payload.get("input_refs", [])
        if not isinstance(input_refs, list):
            raise IntelligenceError("trace input_refs must be a list")
        trace = {
            "id": new_id("trace"),
            "case_id": normalize_case_id(payload["case_id"]) if payload.get("case_id") else "",
            "agent_id": str(payload.get("agent_id", "")).strip()[:160],
            "agent_name": str(payload.get("agent_name", "")).strip()[:160],
            "model": str(payload.get("model", "")).strip()[:240],
            "status": status,
            "input_refs": [str(value)[:500] for value in input_refs][:100],
            "output_kind": str(payload.get("output_kind", "model_output")).strip()[:80],
            "error": str(payload.get("error", "")).strip()[:1000],
            "created_at": utc_now(),
        }

        def mutate(state: dict) -> dict:
            if trace["case_id"] and trace["case_id"] not in state["cases"]:
                raise IntelligenceError(f"unknown case: {trace['case_id']}")
            state["traces"].append(trace)
            if len(state["traces"]) > MAX_TRACES:
                state["traces"] = state["traces"][-MAX_TRACES:]
            return dict(trace)

        return self.store.mutate(mutate)
