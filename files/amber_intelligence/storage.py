"""Thread-safe atomic JSON persistence for AMBER case intelligence."""

from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path
from typing import Callable, TypeVar


T = TypeVar("T")
SCHEMA_VERSION = 1


def empty_state() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "cases": {},
        "evidence": {},
        "memories": [],
        "traces": [],
    }


class AtomicJSONStore:
    """Serialize mutations and commit them with same-directory atomic replace."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()

    def _read_unlocked(self) -> dict:
        if not self.path.exists():
            return empty_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            quarantine = self.path.with_name(
                f"{self.path.stem}.corrupt-{int(time.time())}{self.path.suffix}"
            )
            try:
                self.path.replace(quarantine)
            except OSError:
                pass
            return empty_state()
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported case intelligence schema")
        base = empty_state()
        for key in ("cases", "evidence", "memories", "traces"):
            if key in data:
                base[key] = data[key]
        if not isinstance(base["cases"], dict) or not isinstance(base["evidence"], dict):
            raise ValueError("invalid case intelligence mapping")
        if not isinstance(base["memories"], list) or not isinstance(base["traces"], list):
            raise ValueError("invalid case intelligence collection")
        return base

    def read(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._read_unlocked())

    def mutate(self, fn: Callable[[dict], T]) -> T:
        with self._lock:
            state = self._read_unlocked()
            result = fn(state)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
            try:
                tmp.chmod(0o600)
            except OSError:
                pass
            tmp.replace(self.path)
            return result
