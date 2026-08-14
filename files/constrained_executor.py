#!/usr/bin/env python3
"""
Constrained backend executor for AMBER ICI.

Design goal:
- Execute only explicit user-declared actions.
- Enforce all filesystem access stays inside one allowed root directory.
- Default deny unknown tools or ambiguous payloads.
"""

from __future__ import annotations

import json
import os
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from local_endpoint import require_loopback_http_url


ALLOWED_TOOLS = {
    "list_visible_files",
    "read_file",
    "write_file",
    "append_file",
    "create_script",
    "generate_script",
}


class ContractError(Exception):
    pass


def _is_visible_parts(parts: List[str]) -> bool:
    return all(p and not p.startswith(".") for p in parts)


def _normalize_root(root_dir: str) -> Path:
    root = Path(str(root_dir or "")).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ContractError("allowed root is not a valid directory")
    return root


def _resolve_scoped_path(root: Path, raw_path: str, allow_hidden: bool = False) -> Path:
    rp = Path(str(raw_path or "").strip())
    if not str(rp):
        raise ContractError("path is required")
    target = (rp if rp.is_absolute() else (root / rp)).resolve()
    try:
        target.relative_to(root)
    except Exception:
        raise ContractError("path escapes allowed root")
    rel_parts = list(target.relative_to(root).parts)
    if rel_parts and not allow_hidden and not _is_visible_parts(rel_parts):
        raise ContractError("hidden paths are not allowed")
    return target


def _read_text(path: Path, encoding: str = "utf-8", max_bytes: int = 2 * 1024 * 1024) -> str:
    if not path.exists() or not path.is_file():
        raise ContractError(f"file not found: {path.name}")
    size = path.stat().st_size
    if size > max_bytes:
        raise ContractError(f"file too large: {path.name} ({size} bytes)")
    return path.read_text(encoding=encoding, errors="ignore")


def _write_text(path: Path, content: str, overwrite: bool, dry_run: bool) -> Dict[str, Any]:
    if path.exists() and not overwrite:
        raise ContractError(f"refusing to overwrite existing file: {path.name}")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {
        "path": str(path),
        "bytes": len(content.encode("utf-8")),
        "overwrote": bool(path.exists() and overwrite),
        "dry_run": dry_run,
    }


def _append_text(path: Path, content: str, dry_run: bool) -> Dict[str, Any]:
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(content)
    return {"path": str(path), "bytes_appended": len(content.encode("utf-8")), "dry_run": dry_run}


def _make_executable(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR)


def _post_json(url: str, payload: Dict[str, Any], timeout_sec: int = 90) -> Dict[str, Any]:
    try:
        url = require_loopback_http_url(url)
    except ValueError as error:
        raise ContractError(str(error)) from error
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        # URL is restricted to a validated loopback host immediately above.
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # nosec B310
            body = resp.read().decode("utf-8", errors="ignore")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            j = json.loads(raw)
            msg = j.get("error") or raw
        except Exception:
            msg = raw or str(e)
        raise ContractError(f"model call failed: {msg}")
    except Exception as e:
        raise ContractError(f"model call failed: {e}")


def _list_visible_files(root: Path, recursive: bool = False) -> List[Dict[str, Any]]:
    out = []
    walker = root.rglob("*") if recursive else root.iterdir()
    for p in sorted(walker, key=lambda x: str(x).lower()):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        parts = list(rel.parts)
        if not _is_visible_parts(parts):
            continue
        out.append(
            {
                "name": p.name,
                "relative_path": str(rel),
                "size": int(p.stat().st_size),
                "modified_at": int(p.stat().st_mtime),
            }
        )
    return out


def execute_contract(payload: Dict[str, Any], linked_root: Optional[Path] = None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractError("payload must be an object")
    actions = payload.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ContractError("actions[] is required and cannot be empty")
    instruction = str(payload.get("instruction", "")).strip()
    if not instruction:
        raise ContractError("instruction is required")
    root_raw = str(payload.get("root_dir", "")).strip()
    if not root_raw and linked_root is None:
        raise ContractError("root_dir is required when no linked directory exists")
    root = _normalize_root(root_raw) if root_raw else _normalize_root(str(linked_root))
    dry_run = bool(payload.get("dry_run", False))

    results = []
    started = int(time.time())
    for idx, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            raise ContractError(f"action {idx} must be an object")
        tool = str(action.get("tool", "")).strip()
        if tool not in ALLOWED_TOOLS:
            raise ContractError(f"action {idx}: unsupported tool '{tool}'")

        action_result: Dict[str, Any] = {"index": idx, "tool": tool, "ok": True, "timestamp": int(time.time())}

        if tool == "list_visible_files":
            recursive = bool(action.get("recursive", False))
            action_result["result"] = {"files": _list_visible_files(root, recursive=recursive)}

        elif tool == "read_file":
            path = _resolve_scoped_path(root, str(action.get("path", "")))
            encoding = str(action.get("encoding", "utf-8"))
            max_bytes = int(action.get("max_bytes", 2 * 1024 * 1024))
            text = _read_text(path, encoding=encoding, max_bytes=max_bytes)
            action_result["result"] = {
                "path": str(path),
                "bytes": len(text.encode("utf-8")),
                "content": text,
            }

        elif tool == "write_file":
            path = _resolve_scoped_path(root, str(action.get("path", "")))
            overwrite = bool(action.get("overwrite", False))
            content = str(action.get("content", ""))
            action_result["result"] = _write_text(path, content, overwrite=overwrite, dry_run=dry_run)

        elif tool == "append_file":
            path = _resolve_scoped_path(root, str(action.get("path", "")))
            content = str(action.get("content", ""))
            action_result["result"] = _append_text(path, content, dry_run=dry_run)

        elif tool == "create_script":
            path = _resolve_scoped_path(root, str(action.get("path", "")))
            overwrite = bool(action.get("overwrite", False))
            executable = bool(action.get("executable", True))
            content = str(action.get("content", ""))
            action_result["result"] = _write_text(path, content, overwrite=overwrite, dry_run=dry_run)
            if executable:
                _make_executable(path, dry_run=dry_run)
                action_result["result"]["executable"] = True

        elif tool == "generate_script":
            model = str(action.get("model", "")).strip()
            prompt = str(action.get("prompt", "")).strip()
            output_path = _resolve_scoped_path(root, str(action.get("output_path", "")))
            overwrite = bool(action.get("overwrite", False))
            if not model or not prompt:
                raise ContractError("generate_script requires model and prompt")
            ollama_base = str(action.get("ollama_base", "http://127.0.0.1:11434")).strip().rstrip("/")
            sys_prompt = str(
                action.get(
                    "system",
                    "You generate one complete script only. Return raw script text with no markdown fences.",
                )
            )
            model_resp = _post_json(
                f"{ollama_base}/api/chat",
                {
                    "model": model,
                    "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            script_text = str((model_resp.get("message") or {}).get("content", "")).strip()
            if not script_text:
                raise ContractError("model returned empty script content")
            wr = _write_text(output_path, script_text + "\n", overwrite=overwrite, dry_run=dry_run)
            if bool(action.get("executable", True)):
                _make_executable(output_path, dry_run=dry_run)
                wr["executable"] = True
            action_result["result"] = wr

        results.append(action_result)

    return {
        "ok": True,
        "instruction": instruction,
        "root_dir": str(root),
        "dry_run": dry_run,
        "started_at": started,
        "finished_at": int(time.time()),
        "results": results,
    }
