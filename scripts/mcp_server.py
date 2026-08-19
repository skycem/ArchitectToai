#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal MCP stdio server for Project Architect."""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import arch  # noqa: E402

SERVER_NAME = "project-architect"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "get_architecture",
        "description": "返回当前项目最新架构摘要（脚本模块、场景结构、规则）。建议传入 project_root 以定位项目。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string", "description": "项目根目录，默认自动检测"}
            },
        },
    },
    {
        "name": "refresh_architecture",
        "description": "全量重新扫描项目并更新 architecture.json 与 ARCHITECTURE.md。建议传入 project_root 以定位项目。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_root": {"type": "string"}
            },
        },
    },
    {
        "name": "search_reusable",
        "description": "搜索已有函数/类/脚本/场景，优先返回可复用实现。写新代码前必须调用。建议传入 project_root 以定位项目。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
                "project_root": {"type": "string"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "register_new_script",
        "description": "把新脚本或场景注册进架构索引。建议传入 project_root 以定位项目。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "project_root": {"type": "string"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "update_architecture",
        "description": "更新指定文件（或全项目）的架构索引。建议传入 project_root 以定位项目。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}},
                "project_root": {"type": "string"}
            },
        },
    },
    {
        "name": "check_duplicates",
        "description": "检查新文件中的符号是否与已有实现重复。建议传入 project_root 以定位项目。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "project_root": {"type": "string"}
            },
            "required": ["path"],
        },
    },
]


def resolve_root(project_root: Optional[str]) -> Optional[Path]:
    if project_root:
        return arch.find_project_root(Path(project_root))
    for env_name in ("PROJECT_ROOT", "PWD", "INIT_CWD"):
        env_val = os.environ.get(env_name)
        if env_val:
            root = arch.find_project_root(Path(env_val))
            if root is not None:
                return root
    return arch.find_project_root(Path.cwd())


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    root = resolve_root(arguments.get("project_root"))
    if root is None:
        return {
            "content": [{"type": "text", "text": "未找到项目根目录。请在 Godot/项目目录中运行，或传入 project_root。"}],
            "isError": True,
        }

    if name == "get_architecture":
        index = arch.refresh_if_stale(root)
        text = arch.generate_summary(index)
        return {"content": [{"type": "text", "text": text}], "isError": False}

    if name == "refresh_architecture":
        index = arch.refresh_index(root)
        text = f"已刷新：{len(index['scripts'])} 个脚本，{len(index['scenes'])} 个场景。"
        return {"content": [{"type": "text", "text": text}], "isError": False}

    if name == "search_reusable":
        query = arguments.get("query", "")
        max_results = int(arguments.get("max_results", 10))
        index = arch.load_index(root)
        results = arch.search_index(index, query, max_results)
        text = json.dumps(results, ensure_ascii=False, indent=2)
        return {"content": [{"type": "text", "text": text}], "isError": False}

    if name == "register_new_script":
        path = arguments.get("path")
        if not path:
            return {"content": [{"type": "text", "text": "缺少 path 参数。"}], "isError": True}
        try:
            arch.register_file(root, Path(path))
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"注册失败：{exc}"}], "isError": True}
        return {"content": [{"type": "text", "text": f"已注册：{path}"}], "isError": False}

    if name == "update_architecture":
        paths = arguments.get("paths") or []
        if not paths:
            arch.refresh_index(root)
            return {"content": [{"type": "text", "text": "已全量更新架构索引。"}], "isError": False}
        index = arch.load_index(root)
        for p in paths:
            try:
                arch.register_file(root, Path(p), index)
            except Exception as exc:
                return {"content": [{"type": "text", "text": f"更新失败 {p}: {exc}"}], "isError": True}
        return {"content": [{"type": "text", "text": f"已更新 {len(paths)} 个文件。"}], "isError": False}

    if name == "check_duplicates":
        path = arguments.get("path")
        if not path:
            return {"content": [{"type": "text", "text": "缺少 path 参数。"}], "isError": True}
        hits = arch.check_duplicates(root, Path(path))
        text = json.dumps(hits, ensure_ascii=False, indent=2)
        return {"content": [{"type": "text", "text": text}], "isError": False}

    return {"content": [{"type": "text", "text": f"未知工具: {name}"}], "isError": True}


def handle_request(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = call_tool(name, arguments)
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}
    if method in ("notifications/initialized", "initialized"):
        return None
    if method in ("shutdown", "exit"):
        if msg_id is not None:
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}
        return None
    if msg_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        response = handle_request(msg)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
