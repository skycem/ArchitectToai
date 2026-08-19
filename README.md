# Project Architect

让 Codex 每一轮都先理解当前项目结构，再写代码；写新代码前先搜索可复用实现。

## 工作方式

- `SessionStart` / `UserPromptSubmit` Hook 把最新架构摘要注入模型上下文。
- `search_reusable` MCP 工具搜索已有函数、类、脚本、场景。
- `PostToolUse` Hook 在 `Write` / `Edit` 后自动注册新代码。
- `AGENTS.md` 强制 Codex 遵守“先看架构，再搜索，后编码”。

## 快速开始

在项目根目录执行：

```bash
python plugins/project-architect/scripts/arch.py init
```

这会生成/更新：

- `.project-context/config.yaml`
- `.project-context/architecture.json`
- `.project-context/ARCHITECTURE.md`
- `AGENTS.md`

## 手动命令

```bash
python plugins/project-architect/scripts/arch.py scan
python plugins/project-architect/scripts/arch.py context
python plugins/project-architect/scripts/arch.py search "take_damage"
python plugins/project-architect/scripts/arch.py register scripts/foo.gd
python plugins/project-architect/scripts/arch.py check-duplicates scripts/foo.gd
```

## 结构

```text
project-architect/
├── .codex-plugin/plugin.json
├── .mcp.json
├── hooks.json
├── skills/architecture-first/SKILL.md
└── scripts/
    ├── arch.py
    ├── mcp_server.py
    └── hooks/
```

## 试点项目

该插件不绑定具体项目，可在任意 Godot / Python / TypeScript 项目中使用。

## MCP 使用提示

如果 MCP 工具无法自动定位项目，调用时请传入：

```json
{
  "project_root": "C:\path\to\your-project"
}
```

例如：

```text
search_reusable(query="player", project_root="C:\path\to\your-project")
```
