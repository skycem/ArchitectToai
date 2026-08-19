#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook: automatically register new/edited scripts and scenes."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import arch  # noqa: E402

CODE_EXTS = arch.SOURCE_EXTS | arch.SCENE_EXTS


def extract_file_paths(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and value.endswith(tuple(CODE_EXTS)):
                yield value
            if key in ("path", "file_path", "filePath") and isinstance(value, str):
                yield value
            yield from extract_file_paths(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from extract_file_paths(item)


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        raw = "{}"
    try:
        event = json.loads(raw)
    except Exception:
        event = {}

    cwd = event.get("cwd") or os.getcwd()
    root = arch.find_project_root(Path(cwd))
    if root is None or not (root / ".project-context" / "config.yaml").exists():
        return 0

    tool_input = event.get("tool_input") or event.get("input") or {}
    paths = []
    for p in extract_file_paths(tool_input):
        p = p.replace("\\", "/")
        if p not in paths:
            paths.append(p)
    if not paths:
        return 0

    try:
        index = arch.load_index(root)
        for rel in paths:
            candidate = Path(rel)
            if not candidate.is_absolute():
                candidate = root / candidate
            if not candidate.exists():
                continue
            try:
                arch.register_file(root, candidate, index)
            except Exception as exc:
                print(f"[project-architect] register failed for {rel}: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"[project-architect] post_write error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
