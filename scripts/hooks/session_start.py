#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook: refresh index and inject compact architecture context."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import arch  # noqa: E402


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
    additional = ""
    if root is not None and (root / ".project-context" / "config.yaml").exists():
        try:
            index = arch.refresh_if_stale(root, max_age_seconds=300)
            additional = arch.generate_summary(index)
        except Exception as exc:
            print(f"[project-architect] session_start error: {exc}", file=sys.stderr)

    output = {
        "continue": True,
        "suppressOutput": False,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional,
        },
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
