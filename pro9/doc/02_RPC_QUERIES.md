# OpenClaw 常见 RPC 查询接口

用于 Control UI → Debug → RPC 调用区。

## 会话与对话

| RPC 方法 | 参数示例 | 返回 |
|----------|---------|------|
| `sessions.list` | `{}` | 所有会话列表（key、消息数、时间） |
| `sessions.describe` | `{ "key": "agent:main:dashboard:xxx" }` | 单会话元信息 |
| `sessions.preview` | `{ "keys": ["agent:main:dashboard:xxx"] }` | 会话摘要预览 |
| `sessions.get` | `{ "key": "agent:main:dashboard:xxx" }` | 完整 session row |
| `sessions.usage` | `{ "key": "agent:main:dashboard:xxx" }` | 单会话 token 用量统计 |
| `chat.history` | `{ "sessionKey": "...", "limit": 1000 }` | 会话对话内容 |

## 系统状态

| RPC 方法 | 参数示例 | 返回 |
|----------|---------|------|
| `status` | `{}` | Gateway 综合状态 |
| `health` | `{}` | 健康检查快照 |
| `system-presence` | `{}` | 当前连接的设备/节点列表 |
| `models.list` | `{"view": "configured"}` | 可用模型列表 |

## 用量与费用

| RPC 方法 | 参数示例 | 返回 |
|----------|---------|------|
| `usage.status` | `{}` | Provider 用量窗口/剩余配额 |
| `usage.cost` | `{"from": "...", "to": "..."}` | 按日期范围的费用汇总 |
| `sessions.usage.timeseries` | `{"key": "..."}` | 单会话用量时序 |
| `sessions.usage.logs` | `{"key": "..."}` | 单会话用量日志条目 |

## 配置与节点

| RPC 方法 | 参数示例 | 返回 |
|----------|---------|------|
| `config.get` | `{}` | 当前完整配置 |
| `config.schema` | `{}` | 配置 JSON Schema |
| `config.schema.lookup` | `{"path": "gateway.auth"}` | 指定路径的字段说明 |
| `agents.list` | `{}` | Agent 列表 |
| `node.list` | `{}` | 远程节点列表 |
| `channels.status` | `{}` | Channel/plugin 状态 |
| `tools.catalog` | `{}` | 运行时工具目录 |

## 自动化

| RPC 方法 | 参数示例 | 返回 |
|----------|---------|------|
| `cron.list` | `{}` | 所有 cron 任务 |
| `cron.status` | `{}` | Cron 调度器状态 |
| `cron.runs` | `{"jobId": "..."}` | 某 cron 的运行历史 |
