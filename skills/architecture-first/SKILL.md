---
name: architecture-first
description: Project Architect 核心工作流。在任何开发/编码/实现任务开始时使用，要求先读取当前项目架构、搜索可复用实现、优先复用已有代码，并把新代码自动注册进架构索引。
---

# Architecture First

## 核心原则

1. **先理解，再编码**：每轮开始先获取当前项目架构，不凭记忆猜测项目结构。
2. **先搜索，再新建**：写任何新函数、类、脚本、场景前，必须调用 `search_reusable`。
3. **有就复用**：已有实现能满足需求时，必须复用，不能重写。
4. **新代码自动学习**：新建/修改代码后，由 PostToolUse Hook 自动注册；若未生效，调用 `register_new_script` 或 `update_architecture`。
5. **Godot 只看结构**：分析场景时只提取脚本挂载、场景实例化、节点层级关系；不分析坐标、颜色、贴图、动画等视觉内容。

## 每轮开始

```text
1. 读取项目根目录 AGENTS.md 中的开发协议。
2. 调用 MCP get_architecture 或读取 .project-context/ARCHITECTURE.md。
3. 如果 MCP 工具无法自动定位项目，请传入 project_root 参数为当前项目根目录。
4. 如果架构索引缺失/过期，调用 refresh_architecture（同样可传 project_root）。
```

## 写代码前

```text
1. 用自然语言描述你要实现的能力。
2. 调用 search_reusable：
   - query 使用功能关键词、类名、函数名、文件名
   - 例如：search_reusable(query="移动"), search_reusable(query="player")
3. 如果有候选：
   - 阅读候选文件/签名/摘要
   - 满足需求则直接复用或扩展，不新写重复实现
4. 如果没有候选：
   - 才写新代码
```

## 写完后

```text
1. 新脚本/新场景会被 PostToolUse Hook 自动注册。
2. 若没有 Hook 或注册失败：
   - 调用 register_new_script(path="res://...")
   - 或调用 update_architecture(paths=[...])
3. 如果创建的是新脚本，可调用 check_duplicates 确认没有重复实现。
```

## Godot 场景结构提取规则

只保留：

- 场景文件路径
- 节点名、节点类型、父节点
- 节点挂载的 `Script` 路径
- 实例化的子场景 `PackedScene` 路径

不保留：

- `position` / `rotation` / `scale`
- `modulate` / `self_modulate`
- `texture` / `sprite_frames`
- `animation` / 动画属性
- 任何视觉、表现、布局类属性

## 参考

- `references/reuse-rules.md`：复用判定与反例
- `references/godot-scene-parsing.md`：Godot 场景解析规则
