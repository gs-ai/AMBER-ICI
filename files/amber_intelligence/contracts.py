"""Canonical AMBER case, artifact, memory, and trace contracts."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def normalize_case_id(value: str) -> str:
    normalized = SAFE_ID_RE.sub("-", str(value or "").strip()).strip("-._").lower()
    if not normalized:
        raise ValueError("case id is required")
    if len(normalized) > 80:
        raise ValueError("case id exceeds 80 characters")
    return normalized


def sha256_bytes(raw: bytes) -> str:
    hasher = hashlib.sha256()
    view = memoryview(raw)
    for offset in range(0, len(view), 64 * 1024):
        hasher.update(view[offset : offset + 64 * 1024])
    return hasher.hexdigest()


def sha256_file(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    byte_size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            byte_size += len(chunk)
            hasher.update(chunk)
    return hasher.hexdigest(), byte_size


def artifact_identity(raw: bytes) -> tuple[str, str]:
    digest = sha256_bytes(raw)
    return f"sha256:{digest}", digest


def artifact_identity_file(path: Path) -> tuple[str, str, int]:
    digest, byte_size = sha256_file(path)
    return f"sha256:{digest}", digest, byte_size


def source_contract(*, source_id: str, label: str, source_type: str, captured_at: str) -> dict[str, Any]:
    return {
        "id": source_id,
        "label": label,
        "type": source_type,
        "captured_at": captured_at,
    }


def artifact_contract(
    *,
    artifact_id: str,
    sha256: str,
    filename: str,
    media_type: str,
    byte_size: int,
    source_id: str,
    ingested_at: str,
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "sha256": sha256,
        "filename": filename,
        "media_type": media_type,
        "byte_size": max(0, int(byte_size)),
        "source_id": source_id,
        "ingested_at": ingested_at,
    }
