# 可观测性（心跳与汇报）

> 说明夜莺如何让用户知道"它在干嘛"，以及如何在不打扰用户的前提下汇报。

## 一、原则

- **汇报全部从 state 文件读取，不调用 LLM 生成**：快、省、不跑偏。
- **通知通道与任务通道分离**：任务走文件（`queue/ state/ logs/`），通知走 IM。消息堆积可容忍，用户掌握注意力主权。
- 固定间隔发送（`im.interval_sec`，默认 15 分钟），由独立 IM Loop 承担，与主 Loop 心跳解耦。

## 二、心跳消息固定字段

主 Loop **不直接发 IM**。心跳通知由**独立的 IM Loop 进程**（`scripts/im_loop.sh`）按 `im.interval_sec` 发送：它从 `state/system_state.json` 与 `queue/tasks.json` 读字段、拼以下固定格式（**不调 LLM 生成**），串行发到各可用渠道；发送失败/超时只降级写日志，不阻塞主 Loop。IM 为尽力而为通道，`im.enabled` 为 `false` 或渠道全关时 IM Loop 每轮跳过。

```
【夜莺心跳】
时间：<ISO 时间>
系统状态：running (N pairs) / idle
当前任务：<task_id 或 "无">
最近完成：<最近一次 commit message 或评估 summary>
本轮错误：<错误数量或 "无">
最后心跳：<距离上次心跳的时间>
```

字段取自 `state/system_state.json`（系统状态 `status` / `mode`、`active_pairs`、心跳）与 `queue/tasks.json`（当前任务、最近 commit 或评估摘要、错误计数）。

`running (N pairs)` 的 N 即 `active_pairs`（本轮实际派发的角色对数，保守为 1）；空闲无派发时状态为 `idle`，不显示 pairs。

## 三、可观测性的其余载体

| 载体 | 记录什么 |
|---|---|
| `state/system_state.json` | 系统状态、当前执行单元、最近心跳时间（单一真相源） |
| `queue/tasks.json` | 各任务状态与迭代记录 |
| `logs/` | 每轮心跳、派发、错误日志 |
| 项目目录的 git log | 每轮"有意义变化"的 commit，演化叙事 |
