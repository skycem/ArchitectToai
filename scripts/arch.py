#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project Architect core: scan, search, register, summarize a Godot/project architecture."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_MARKERS = ("project.godot", "pyproject.toml", "package.json", "go.mod", "Cargo.toml")
DEFAULT_EXCLUDE_DIRS = {
    ".godot", ".git", ".import", ".gdmcp", ".tmp", "__pycache__",
    "plugins", "node_modules", "dist", "build", ".venv", "venv",
}
DEFAULT_EXCLUDE_NAME_PARTS = ()

SOURCE_EXTS = {".gd", ".py", ".ts", ".js", ".cs"}
SCENE_EXTS = {".tscn", ".scn"}


def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk upward from start (or cwd) looking for a project marker."""
    if start is None:
        start = Path.cwd()
    if start.is_file():
        start = start.parent
    for directory in (start, *start.parents):
        for marker in PROJECT_MARKERS:
            if (directory / marker).exists():
                return directory
    return None


def _read_config_text(path: Path) -> Dict[str, Any]:
    """Minimal YAML-subset reader for .project-context/config.yaml."""
    config: Dict[str, Any] = {}
    current_section: Optional[str] = None
    list_key: Optional[str] = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        section_match = re.match(r"^([a-zA-Z_][\w-]*):\s*(#.*)?$", line)
        if section_match and not line.split(":")[1].strip():
            current_section = section_match.group(1)
            config.setdefault(current_section, {})
            list_key = None
            continue
        if line.startswith("- "):
            if current_section and list_key:
                item = line[2:].strip().strip("\"'")
                config[current_section][list_key].append(item)
            continue
        kv = re.match(r"^([a-zA-Z_][\w-]*)\s*:\s*(.*)$", line)
        if kv:
            key, value = kv.group(1), kv.group(2).strip()
            value = re.sub(r"\s*#.*$", "", value).strip().strip("\"'")
            if current_section:
                if value == "":
                    config[current_section][key] = []
                    list_key = key
                else:
                    config[current_section][key] = value
                    list_key = None
            else:
                config[key] = value
                list_key = None
    return config


def default_config(project_root: Path) -> Dict[str, Any]:
    return {
        "name": project_root.name,
        "languages": ["gdscript", "python"],
        "scan": {
            "include": ["**/*.gd", "**/*.py", "**/*.tscn", "**/*.scn"],
            "exclude": [".godot", ".git", ".gdmcp", "addons", "plugins"],
        },
        "architecture": {
            "storage": ".project-context/architecture.json",
            "summary": ".project-context/ARCHITECTURE.md",
        },
    }


def load_config(project_root: Path) -> Dict[str, Any]:
    cfg_path = project_root / ".project-context" / "config.yaml"
    config = default_config(project_root)
    if cfg_path.exists():
        parsed = _read_config_text(cfg_path)
        if parsed.get("name"):
            config["name"] = parsed["name"]
        if parsed.get("languages"):
            languages = parsed["languages"]
            if isinstance(languages, list):
                config["languages"] = languages
        scan = parsed.get("scan") or {}
        if isinstance(scan, dict):
            if scan.get("include"):
                config["scan"]["include"] = scan["include"]
            if scan.get("exclude"):
                config["scan"]["exclude"] = scan["exclude"]
    return config


def is_excluded(rel_path: Path, config: Dict[str, Any]) -> bool:
    excludes = set(config.get("scan", {}).get("exclude", []))
    parts = set(rel_path.parts)
    if parts & DEFAULT_EXCLUDE_DIRS:
        return True
    for pattern in excludes:
        pattern_str = str(pattern)
        if pattern_str in rel_path.parts:
            return True
    for part in rel_path.parts:
        if any(name_part in part for name_part in DEFAULT_EXCLUDE_NAME_PARTS):
            return True
    return False


def _parse_python(path: Path, rel_path: Path, text: str) -> Dict[str, Any]:
    symbols: List[Dict[str, Any]] = []
    dependencies: List[str] = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        m = re.match(r"^(?:async\s+)?def\s+([A-Za-z_]\w*)\s*(\([^)]*\))?\s*(->\s*[^:]+)?\s*:", line)
        if m:
            symbols.append({
                "kind": "function",
                "name": m.group(1),
                "signature": line,
                "line": line_no,
            })
            continue
        m = re.match(r"^class\s+([A-Za-z_]\w*)\s*(\([^)]*\))?\s*:", line)
        if m:
            symbols.append({
                "kind": "class",
                "name": m.group(1),
                "signature": line,
                "line": line_no,
            })
            continue
        for dep in re.findall(r"^\s*(?:import|from)\s+([\w.]+)", raw):
            dependencies.append(dep)
    return {"language": "python", "symbols": symbols, "dependencies": sorted(set(dependencies))}


def _parse_gdscript(path: Path, rel_path: Path, text: str) -> Dict[str, Any]:
    symbols: List[Dict[str, Any]] = []
    dependencies: List[str] = []
    class_name: Optional[str] = None
    extends: Optional[str] = None
    summary: str = ""

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if not summary:
                summary = line.lstrip("#").strip()
            continue

        m = re.match(r"^class_name\s+([A-Za-z_]\w*)", line)
        if m:
            class_name = m.group(1)
            symbols.append({"kind": "class", "name": class_name, "signature": line, "line": line_no})
            continue

        m = re.match(r"^extends\s+([^\s#]+)", line)
        if m:
            extends = m.group(1)
            symbols.append({"kind": "extends", "name": extends, "signature": line, "line": line_no})
            continue

        m = re.match(r"^func\s+([A-Za-z_]\w*)\s*(\([^)]*\))?\s*(->\s*[^:]+)?\s*:", line)
        if m:
            symbols.append({
                "kind": "function",
                "name": m.group(1),
                "signature": line,
                "line": line_no,
            })
            continue

        m = re.match(r"^signal\s+([A-Za-z_]\w*)", line)
        if m:
            symbols.append({"kind": "signal", "name": m.group(1), "signature": line, "line": line_no})
            continue

        m = re.match(r"^const\s+([A-Za-z_]\w*)\s*=", line)
        if m:
            symbols.append({"kind": "constant", "name": m.group(1), "signature": line, "line": line_no})
            continue

        m = re.match(r"^var\s+([A-Za-z_]\w*)\s*:", line)
        if m:
            symbols.append({"kind": "member", "name": m.group(1), "signature": line, "line": line_no})
            continue

        for dep in re.findall(r"\b(?:preload|load)\((['\"])(.*?)\1\)", line):
            dependencies.append(dep[1])

    return {
        "language": "gdscript",
        "class_name": class_name,
        "extends": extends,
        "summary": summary,
        "symbols": symbols,
        "dependencies": sorted(set(dependencies)),
    }


def parse_source_file(path: Path, project_root: Path) -> Dict[str, Any]:
    rel = path.relative_to(project_root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        parsed = _parse_python(path, rel, text)
    elif path.suffix == ".gd":
        parsed = _parse_gdscript(path, rel, text)
    else:
        parsed = {"language": path.suffix.lstrip("."), "symbols": [], "dependencies": []}
    return {
        "path": "res://" + rel if rel.startswith(("scripts/", "addons/")) or path.suffix == ".gd" else rel,
        "abs_path": str(path),
        "language": parsed.get("language", path.suffix.lstrip(".")),
        "summary": parsed.get("summary", ""),
        "class_name": parsed.get("class_name"),
        "extends": parsed.get("extends"),
        "symbols": parsed.get("symbols", []),
        "dependencies": parsed.get("dependencies", []),
    }


def parse_scene_file(path: Path, project_root: Path) -> Dict[str, Any]:
    rel = path.relative_to(project_root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    ext_resources: Dict[str, tuple] = {}
    nodes: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(
            r'\[ext_resource\s+type="(Script|PackedScene)"[^\]]*path="([^"]+)"[^\]]*id="([^"]+)"\]',
            line,
        )
        if m:
            ext_resources[m.group(3)] = (m.group(1), m.group(2))
            continue
        m = re.match(
            r'\[node\s+name="([^"]+)"\s+type="([^"]+)"(.*?)\]',
            line,
        )
        if m:
            node = {
                "name": m.group(1),
                "type": m.group(2),
                "parent": ".",
                "script": None,
                "instance": None,
            }
            attrs = m.group(3)
            pm = re.search(r'parent="([^"]*)"', attrs)
            if pm:
                node["parent"] = pm.group(1) or "."
            im = re.search(r'instance=ExtResource\("([^"]+)"\)', attrs)
            if im:
                resource = ext_resources.get(im.group(1))
                if resource and resource[0] == "PackedScene":
                    node["instance"] = resource[1]
            current = node
            nodes.append(node)
            continue
        if current is not None:
            sm = re.match(r'^script\s*=\s*ExtResource\("([^"]+)"\)', line)
            if sm:
                resource = ext_resources.get(sm.group(1))
                if resource:
                    current["script"] = resource[1]

    scripts = sorted({n["script"] for n in nodes if n.get("script")})
    instances = sorted({n["instance"] for n in nodes if n.get("instance")})
    return {
        "path": "res://" + rel if rel.startswith("scenes/") else rel,
        "abs_path": str(path),
        "nodes": nodes,
        "scripts": scripts,
        "instances": instances,
    }


def _walk_files(project_root: Path, config: Dict[str, Any]) -> Iterable[Path]:
    include = config.get("scan", {}).get("include", [])
    for pattern in include:
        if pattern.startswith("**/"):
            pattern = pattern[3:]
        for path in project_root.rglob(pattern):
            if path.is_file():
                rel = path.relative_to(project_root)
                if not is_excluded(rel, config):
                    yield path


def scan_project(project_root: Path, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = config or load_config(project_root)
    scripts: List[Dict[str, Any]] = []
    scenes: List[Dict[str, Any]] = []
    for path in _walk_files(project_root, config):
        try:
            if path.suffix in SOURCE_EXTS:
                scripts.append(parse_source_file(path, project_root))
            elif path.suffix in SCENE_EXTS:
                scenes.append(parse_scene_file(path, project_root))
        except Exception as exc:  # noqa: BLE001
            print(f"[project-architect] skip {path}: {exc}", file=sys.stderr)
    scripts.sort(key=lambda x: x["path"])
    scenes.sort(key=lambda x: x["path"])
    index = {
        "schemaVersion": 1,
        "project": config.get("name", project_root.name),
        "root": str(project_root),
        "updatedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "scripts": scripts,
        "scenes": scenes,
        "symbols": _flatten_symbols(scripts),
    }
    return index


def _flatten_symbols(scripts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flat: List[Dict[str, Any]] = []
    for script in scripts:
        for sym in script.get("symbols", []):
            flat.append({
                "kind": sym.get("kind"),
                "name": sym.get("name"),
                "signature": sym.get("signature", ""),
                "file": script.get("path"),
                "abs_path": script.get("abs_path"),
                "line": sym.get("line"),
                "summary": script.get("summary", ""),
                "language": script.get("language"),
            })
    return flat


def save_index(project_root: Path, index: Dict[str, Any]) -> Path:
    ctx = project_root / ".project-context"
    ctx.mkdir(parents=True, exist_ok=True)
    out = ctx / "architecture.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    save_summary(project_root, index)
    return out


def save_summary(project_root: Path, index: Dict[str, Any]) -> Path:
    ctx = project_root / ".project-context"
    ctx.mkdir(parents=True, exist_ok=True)
    summary_path = ctx / "ARCHITECTURE.md"
    summary_path.write_text(generate_summary(index), encoding="utf-8")
    return summary_path


def load_index(project_root: Path) -> Dict[str, Any]:
    idx_path = project_root / ".project-context" / "architecture.json"
    if idx_path.exists():
        try:
            return json.loads(idx_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return scan_project(project_root)


def refresh_index(project_root: Path, index: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if index is None:
        index = scan_project(project_root)
    save_index(project_root, index)
    return index


def refresh_if_stale(project_root: Path, max_age_seconds: int = 60) -> Dict[str, Any]:
    idx_path = project_root / ".project-context" / "architecture.json"
    if idx_path.exists():
        try:
            mtime = idx_path.stat().st_mtime
            if (datetime.datetime.now().timestamp() - mtime) < max_age_seconds:
                return load_index(project_root)
        except Exception:
            pass
    return refresh_index(project_root)


def generate_summary(index: Dict[str, Any], max_scripts: int = 60, max_scenes: int = 40) -> str:
    lines: List[str] = []
    lines.append(f"# {index.get('project', 'Project')} 架构摘要")
    lines.append(f"- 更新时间：{index.get('updatedAt', 'unknown')}")
    scripts = index.get("scripts", [])
    scenes = index.get("scenes", [])
    symbols = index.get("symbols", [])
    lines.append(f"- 脚本：{len(scripts)} 个，场景：{len(scenes)} 个，符号：{len(symbols)} 个")
    lines.append("")

    groups: Dict[str, List[Dict[str, Any]]] = {}
    for script in scripts:
        path = script.get("path", "")
        parts = path.replace("res://", "").split("/")
        group = parts[0] if len(parts) > 1 else "(root)"
        groups.setdefault(group, []).append(script)
    lines.append("## 脚本模块")
    for group in sorted(groups):
        items = groups[group]
        lines.append(f"### {group} ({len(items)})")
        for script in items[:12]:
            name = script.get("path", "")
            cls = script.get("class_name")
            summary = script.get("summary", "")
            extra = f" [{cls}]" if cls else ""
            if summary:
                lines.append(f"- {name}{extra}：{summary}")
            else:
                lines.append(f"- {name}{extra}")
        if len(items) > 12:
            lines.append(f"- ... 还有 {len(items) - 12} 个")
    lines.append("")

    lines.append("## 场景结构")
    for scene in scenes[: max_scenes]:
        path = scene.get("path", "")
        scripts_used = scene.get("scripts", [])
        instances = scene.get("instances", [])
        bits = []
        if scripts_used:
            bits.append("scripts=" + ",".join(p.replace("res://", "") for p in scripts_used[:3]))
        if instances:
            bits.append("instances=" + ",".join(p.replace("res://", "") for p in instances[:3]))
        lines.append(f"- {path}" + (f" ({'; '.join(bits)})" if bits else ""))
    if len(scenes) > max_scenes:
        lines.append(f"- ... 还有 {len(scenes) - max_scenes} 个")
    lines.append("")
    lines.append("## 规则")
    lines.append("- 开发前先读取本摘要或调用 get_architecture。")
    lines.append("- 写新代码前先调用 search_reusable 搜索已有实现。")
    lines.append("- 已有实现能满足需求时，必须复用，不能重写。")
    lines.append("- 新建代码会自动注册进架构索引。")
    return "\n".join(lines)


def search_index(index: Dict[str, Any], query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return []
    scored: List[tuple] = []
    for sym in index.get("symbols", []):
        if sym.get("kind") not in ("class", "function", "signal", "constant"):
            continue
        name = str(sym.get("name", ""))
        sig = str(sym.get("signature", ""))
        path = str(sym.get("file", ""))
        summary = str(sym.get("summary", ""))
        score = 0
        if name.lower() == q:
            score += 100
        elif name.lower().startswith(q):
            score += 60
        elif q in name.lower():
            score += 40
        if q in path.lower():
            score += 20
        if q in summary.lower():
            score += 10
        if q in sig.lower():
            score += 5
        if score:
            scored.append((-score, name, path, sym))
    scored.sort(key=lambda x: (x[0], x[1], x[2]))
    results = [s[3] for s in scored[:max_results]]

    for scene in index.get("scenes", []):
        path = str(scene.get("path", ""))
        if q in path.lower():
            scene_results = {
                "kind": "scene",
                "name": Path(path).name,
                "signature": "",
                "file": path,
                "abs_path": scene.get("abs_path"),
                "line": None,
                "summary": "scene",
                "language": "tscn",
            }
            results.append(scene_results)
    return results[:max_results + 5]


def register_file(project_root: Path, file_path: Path, index: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    file_path = Path(file_path)
    if not file_path.is_absolute():
        file_path = project_root / file_path
    file_path = file_path.resolve()
    if project_root not in file_path.parents and file_path != project_root:
        raise ValueError(f"file is outside project root: {file_path}")
    index = index or load_index(project_root)
    if file_path.suffix in SOURCE_EXTS:
        parsed = parse_source_file(file_path, project_root)
        rel_key = parsed["path"]
        index["scripts"] = [s for s in index.get("scripts", []) if s.get("path") != rel_key]
        index["scripts"].append(parsed)
        index["scripts"].sort(key=lambda s: s["path"])
        index["symbols"] = _flatten_symbols(index["scripts"])
    elif file_path.suffix in SCENE_EXTS:
        parsed = parse_scene_file(file_path, project_root)
        rel_key = parsed["path"]
        index["scenes"] = [s for s in index.get("scenes", []) if s.get("path") != rel_key]
        index["scenes"].append(parsed)
        index["scenes"].sort(key=lambda s: s["path"])
    else:
        raise ValueError(f"unsupported file type: {file_path.suffix}")
    index["updatedAt"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    save_index(project_root, index)
    return index


def check_duplicates(project_root: Path, file_path: Path, index: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    file_path = Path(file_path)
    if not file_path.is_absolute():
        file_path = project_root / file_path
    file_path = file_path.resolve()
    index = index or load_index(project_root)
    if file_path.suffix not in SOURCE_EXTS:
        return []
    parsed = parse_source_file(file_path, project_root)
    new_rel = parsed["path"]
    hits: List[Dict[str, Any]] = []
    new_names = {sym["name"] for sym in parsed.get("symbols", []) if sym.get("name")}
    for sym in index.get("symbols", []):
        if sym.get("file") == new_rel:
            continue
        name = str(sym.get("name", ""))
        if name in new_names:
            hits.append(sym)
        elif name.lower() in {n.lower() for n in new_names}:
            hits.append(sym)
    return hits


def write_agents_md(project_root: Path) -> Path:
    path = project_root / "AGENTS.md"
    project_path = str(project_root).replace("\\", "\\\\")
    content = f"""# 项目开发协议

本文件由 Project Architect 插件维护。

## 每轮开发前

1. 先阅读 `.project-context/ARCHITECTURE.md`，或调用 MCP `get_architecture` 获取最新项目结构。
2. 如果 MCP 工具无法自动定位项目，请传入 `project_root` 为当前项目根目录：`{project_path}`。
3. 写任何新函数、类、脚本、场景前，先调用 `search_reusable` 搜索已有实现。
4. 已有实现能满足需求时，必须复用，不能重写。
5. 只有确认没有可复用实现时，才写新代码。
6. 新建/修改代码文件后，由 Hook 自动注册进架构索引；如果未生效，手动调用 `register_new_script`。

## Godot 场景约定

- 分析场景时只关注脚本挂载、场景实例化、节点层级结构。
- 不要为了理解架构而分析坐标、颜色、贴图、动画等视觉内容。
"""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if "Project Architect" in existing:
            return path
        content = existing.rstrip() + "\n\n---\n\n" + content
    path.write_text(content, encoding="utf-8")
    return path


def write_config(project_root: Path) -> Path:
    ctx = project_root / ".project-context"
    ctx.mkdir(parents=True, exist_ok=True)
    cfg = ctx / "config.yaml"
    if not cfg.exists():
        cfg.write_text(
            f"""# Project Architect 项目配置
name: {project_root.name}
languages:
  - gdscript
  - python
scan:
  include:
    - "**/*.gd"
    - "**/*.py"
    - "**/*.tscn"
    - "**/*.scn"
  exclude:
    - ".godot"
    - "addons"
    - ".git"
    - ".gdmcp"
    - "plugins"
architecture:
  storage: ".project-context/architecture.json"
  summary: ".project-context/ARCHITECTURE.md"
""",
            encoding="utf-8",
        )
    return cfg


def cmd_init(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    if root is None:
        print("No project marker found; run inside a Godot/project directory.", file=sys.stderr)
        return 1
    write_config(root)
    write_agents_md(root)
    refresh_index(root)
    print(f"Initialized Project Architect in {root}")
    print("- .project-context/config.yaml")
    print("- .project-context/architecture.json")
    print("- .project-context/ARCHITECTURE.md")
    print("- AGENTS.md")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    if root is None:
        print("No project marker found.", file=sys.stderr)
        return 1
    index = refresh_index(root)
    print(f"Scanned {len(index['scripts'])} scripts, {len(index['scenes'])} scenes -> {root / '.project-context/architecture.json'}")
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    if root is None:
        print("No project marker found.", file=sys.stderr)
        return 1
    index = refresh_if_stale(root)
    print(generate_summary(index))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    if root is None:
        print("No project marker found.", file=sys.stderr)
        return 1
    index = load_index(root)
    results = search_index(index, args.query, args.max_results)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if not results:
            print("No reusable implementation found.")
            return 0
        for r in results:
            loc = f"{r.get('file')}:{r.get('line')}" if r.get("line") else r.get("file")
            print(f"[{r.get('kind')}] {r.get('name')}  {loc}")
            if r.get("signature"):
                print(f"    {r.get('signature')}")
            if r.get("summary"):
                print(f"    {r.get('summary')}")
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    if root is None:
        print("No project marker found.", file=sys.stderr)
        return 1
    try:
        register_file(root, Path(args.path))
    except Exception as exc:
        print(f"register failed: {exc}", file=sys.stderr)
        return 1
    print(f"Registered {args.path}")
    return 0


def cmd_check_duplicates(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd())
    if root is None:
        print("No project marker found.", file=sys.stderr)
        return 1
    hits = check_duplicates(root, Path(args.path))
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    elif hits:
        print("Potential duplicate implementations:")
        for hit in hits:
            print(f"- {hit.get('kind')} {hit.get('name')} at {hit.get('file')}:{hit.get('line')}")
    else:
        print("No duplicates found.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arch", description="Project Architect CLI")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Initialize .project-context and AGENTS.md")
    sub.add_parser("scan", help="Scan project and write architecture index")
    sub.add_parser("context", help="Print architecture summary")
    p_search = sub.add_parser("search", help="Search reusable code")
    p_search.add_argument("query")
    p_search.add_argument("--max-results", type=int, default=10)
    p_search.add_argument("--json", action="store_true")
    p_reg = sub.add_parser("register", help="Register a script/scene")
    p_reg.add_argument("path")
    p_dup = sub.add_parser("check-duplicates", help="Check new file for duplicate symbols")
    p_dup.add_argument("path")
    p_dup.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init(args)
    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "context":
        return cmd_context(args)
    if args.command == "search":
        return cmd_search(args)
    if args.command == "register":
        return cmd_register(args)
    if args.command == "check-duplicates":
        return cmd_check_duplicates(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
