# Godot 场景解析规则

## 需要记录

```text
[ext_resource type="Script" path="res://scripts/...gd" id="..."]
[node name="Player" type="CharacterBody2D"]
script = ExtResource("...")
[node name="Player" parent="." instance=ExtResource("...")]
```

- ext_resource 中 `Script` 表示脚本挂载
- ext_resource 中 `PackedScene` 表示可实例化场景
- node 的 `script = ExtResource(...)` 表示节点挂载脚本
- node 行内的 `instance=ExtResource(...)` 表示实例化子场景

## 需要忽略

- `position`, `rotation`, `scale`
- `modulate`, `self_modulate`
- `texture`, `sprite_frames`, `animation`
- `region`, `frame`, `offset`
- 所有视觉、布局、动画、物理形状细节（除非架构上需要，例如碰撞层分组）
