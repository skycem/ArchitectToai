---
name: function-documentation
description: 为每个新写/重写的函数添加完整、规范、可执行的注释，包括作用、输入、输出、执行流程和适用场景，提升代码可读性与复用性。
---

# Function Documentation

## 核心规则

1. **每个新写的函数都必须有完整注释**。
2. **重写或大幅修改已有函数时，必须同步更新注释**。
3. 注释必须包含以下五部分：
   - 函数作用
   - 函数输入（每个参数的类型和含义）
   - 函数输出（返回值/副作用/输出内容）
   - 函数内执行的流程（关键步骤）
   - 适用场景（什么时候可以用这个函数，能做什么事）
4. 注释写在函数定义之前，使用当前语言的标准注释方式。
5. 注释要具体，不能只写“处理数据”“执行逻辑”这种空话。
6. 短小的私有辅助函数可以适当精简，但仍需说明作用、输入、输出和适用场景。

## 标准注释模板

### GDScript

```gdscript
## 作用：计算玩家受到的实际伤害。
## 输入：
## - base_damage: float，技能/攻击的基础伤害值
## - defense: float，目标防御值，不能为负数
## - is_critical: bool，是否暴击，暴击时伤害乘 1.5
## 输出：返回实际伤害值 float，最低为 1。
## 流程：
## 1. 用 defense 减免 base_damage
## 2. 如果 is_critical 为 true，伤害乘 1.5
## 3. 确保伤害至少为 1
## 适用场景：战斗系统计算伤害时调用；也可用于伤害预览和伤害统计。
func calculate_damage(base_damage: float, defense: float, is_critical: bool) -> float:
    var damage: float = maxf(base_damage - defense, 1.0)
    if is_critical:
        damage *= 1.5
    return damage
```

### Python

```python
def calculate_damage(base_damage: float, defense: float, is_critical: bool) -> float:
    """计算玩家受到的实际伤害。

    作用：
        根据基础伤害、防御和暴击状态计算最终伤害。

    输入：
        base_damage: 技能/攻击的基础伤害值
        defense: 目标防御值，不能为负数
        is_critical: 是否暴击，暴击时伤害乘 1.5

    输出：
        返回最终伤害 float，最低为 1。

    流程：
        1. 用 defense 减免 base_damage
        2. 如果 is_critical 为 true，伤害乘 1.5
        3. 确保伤害至少为 1

    适用场景：
        战斗系统计算伤害时调用；也可用于伤害预览和伤害统计。
    """
    damage = max(base_damage - defense, 1.0)
    if is_critical:
        damage *= 1.5
    return damage
```

### TypeScript / JavaScript

```typescript
/**
 * 计算玩家受到的实际伤害。
 *
 * @param base_damage - 技能/攻击的基础伤害值
 * @param defense - 目标防御值，不能为负数
 * @param is_critical - 是否暴击，暴击时伤害乘 1.5
 * @returns 最终伤害值，最低为 1
 *
 * 流程：
 * 1. 用 defense 减免 base_damage
 * 2. 如果 is_critical 为 true，伤害乘 1.5
 * 3. 确保伤害至少为 1
 *
 * 适用场景：
 * 战斗系统计算伤害时调用；也可用于伤害预览和伤害统计。
 */
export function calculateDamage(baseDamage: number, defense: number, isCritical: boolean): number {
  const damage = Math.max(baseDamage - defense, 1);
  return isCritical ? damage * 1.5 : damage;
}
```

## 何时必须写

- 新建脚本/文件中的新函数
- 在已有文件中新增函数
- 重写一个已有函数的实现
- 函数签名或行为发生重大变化

## 何时可以精简

- 一行式 getter/setter：可以只写作用、输入、输出，不写流程。
- 明显的私有辅助函数：可以写简短版，但必须包含作用和适用场景。

## 反例

```gdscript
# 处理伤害
func calculate_damage(base_damage: float, defense: float, is_critical: bool) -> float:
    pass
```

这种注释没有说明输入、输出、流程和适用场景，不合格。

## 参考

- `references/comment-examples.md`：更多语言和场景示例。
