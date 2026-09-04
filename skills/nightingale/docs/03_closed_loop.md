# 闭环协议（评估者输出 ↔ 开发者输入）

> 定义 workflow 每个周期内"开发者干活"与"评估者挑活"之间的交接协议：开发者消费什么、评估者产出什么、按什么规则推进。

## 一、评估者每轮输出的 JSON

评估者审视当前产出后，输出以下结构并**落盘**，供下一轮 workflow 的开发者读取：

```json
{
  "verdict": "continue | done | failed",
  "summary": "一句话描述当前状态",
  "actions": [
    { "priority": 1, "task": "做什么", "reason": "为什么" },
    { "priority": 2, "task": "做什么", "reason": "为什么" }
  ]
}
```

## 二、规则

### verdict 语义

| verdict | 含义 | Loop 行为 |
|---|---|---|
| `continue` | 还有值得做的事 | 继续投递下一轮 workflow |
| `done` | 当前任务已完成 | 标记任务 `done`，不再投递 |
| `failed` | 卡死或无法推进 | 任务标 `failed`；重试有限次后放弃，不阻塞心跳 |

### actions 规则

- `actions` 最多 3 条，按 `priority` **升序**排列。
- 开发者下一轮**只做 `priority` 最小的一条**，不顺手扩 scope。
- 评估者若找不到任何值得做的事 → 返回空 `actions` + `verdict: done`（不要硬凑活）。

### 优先级约定

| priority | 含义 |
|---|---|
| 1 | 阻塞性修复（不修别的做不了） |
| 2 | 重要改进（显著提升质量） |
| 3 | 可选优化（锦上添花） |

功能性缺陷 > 代码结构 > 体验 > 文档 > 琐碎优化；高优先级清空后自然降到低优先级，但**即使只剩琐碎优化，也比"停"好**。

## 三、落盘位置

- 评估结果写入任务对应的状态/结果文件，明确它是"给下一轮开发者读的输入"。
- 每次开发 → commit 形成一条审计记录，第二天靠 `git log` 复盘演化叙事。

## 四、多角色对的文件分流（激进时段）

激进时段可并行多对角色：功能对、测试对、文档对、审查对、优化对。每对遵循同一套闭环（开发者产改动 → commit → 评估者给 `verdict/actions`），但读写各自的 eval 文件：

- 功能对：`queue/eval/<task_id>.json`（主文件，沿用上文）。
- 测试/文档/审查/优化对：`queue/eval/<task_id>.<role>.json`（role ∈ `test` / `docs` / `review` / `optimize`），`round` 各自独立计数。

**写文件的最小竞争约定**：只有功能对更新 `queue/tasks.json` 与 `state/system_state.json`；其余角色对只改代码并 commit、写各自的角色 eval 文件，绝不碰全局状态文件。

- 主文件 `verdict: done` → 整个任务 `done`（关闭）。
- 角色文件 `verdict: done` → 该角色本轮停；激进时段该角色下轮可自主找活，或等下次进入激进时段由分发者重新派活。

## 五、与 prompt 模板的关系

评估者/开发者的 prompt 模板应与本协议同一口径（见 `references/prompts.md`）：开发者模板消费 `actions`，评估者模板产出 `verdict/actions`。两者若出现出入，**以本文件为唯一口径**。
