# 注释示例参考

## GDScript：带副作用的函数

```gdscript
## 作用：将物品加入玩家背包，并刷新 HUD 显示。
## 输入：
## - item_id: String，物品 ID，必须在 ItemDatabase 中存在
## - amount: int，加入数量，必须大于 0
## 输出：返回 bool，true 表示加入成功，false 表示背包已满或参数无效。
## 流程：
## 1. 校验 item_id 和 amount
## 2. 检查背包剩余空间
## 3. 写入 PlayerInventory
## 4. 发送 inventory_changed 信号并刷新 HUD
## 适用场景：拾取物品、商店购买、任务奖励等需要给玩家加物品的地方。
func add_item_to_inventory(item_id: String, amount: int) -> bool:
    return true
```

## GDScript：信号回调函数

```gdscript
## 作用：当玩家点击“开始游戏”按钮时进入对应场景。
## 输入：无直接参数；通过信号绑定获取按钮按下事件。
## 输出：无返回值；副作用是切换当前场景。
## 流程：
## 1. 保存当前游戏状态
## 2. 淡出过渡动画
## 3. 切换到目标场景
## 4. 初始化新场景数据
## 适用场景：主菜单、暂停菜单、关卡结束界面中的开始/继续按钮。
func _on_start_button_pressed() -> void:
    pass
```

## Python：数据处理函数

```python
def normalize_user_name(name: str) -> str:
    """标准化用户名。

    作用：
        去除首尾空格、统一大小写，并过滤非法字符。

    输入：
        name: 原始用户名字符串

    输出：
        返回标准化后的用户名。

    流程：
        1. 去除首尾空白
        2. 转为小写
        3. 只保留字母、数字、下划线和中文字符

    适用场景：
        注册、登录、搜索匹配前统一用户输入。
    """
    return name.strip().lower()
```

## TypeScript：异步函数

```typescript
/**
 * 根据订单 ID 获取订单详情。
 *
 * @param orderId - 订单 ID
 * @returns Promise<Order | null>，订单不存在时返回 null
 *
 * 流程：
 * 1. 检查 orderId 是否合法
 * 2. 从缓存读取，命中则直接返回
 * 3. 未命中则请求 API
 * 4. 写入缓存后返回
 *
 * 适用场景：
 * 订单详情页、订单列表展开、支付结果回查。
 */
export async function fetchOrderDetail(orderId: string): Promise<Order | null> {
  return null;
}
```

## 精简版示例（允许）

```gdscript
## 作用：返回当前玩家金币数量。
## 输入：无。
## 输出：int，当前金币数量。
## 适用场景：HUD 刷新、商店购买判断。
func get_gold() -> int:
    return 0
```
