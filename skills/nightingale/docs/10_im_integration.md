# IM 接入

> 说明夜莺如何把心跳汇报发到 IM（飞书 / 钉钉 / 企业微信）。核心原则：**IM 是"尽力而为"的通知通道，不是"必须成功"的任务**。配置了 IM、检测失败、发送超时，都不能阻塞主 Loop 心跳。

## 一、架构：主 Loop 与 IM Loop 分离

夜莺把"活着"和"通知"也分开：

```
主 Loop（调度循环，永不停止）          IM Loop（通知循环，独立存在）
      │                                      │
      │ 读队列 / 调 workflow                  │ 读状态文件
      │ 落盘 system_state.json               │ 拼心跳消息
      │                                      │ 串行发各渠道
      │                                      │ 全失败 → 降级写日志
      │                                      │ 更新 im_last_sent / im_last_status
      ▼                                      ▼
  永不停止                            独立进程，单独启动
```

- **主 Loop**：只负责调度、落盘、心跳。完全不知道 IM Loop 的存在。
- **IM Loop**：只负责读状态文件、拼心跳消息、发 IM。发送失败、超时、崩溃，都不影响主 Loop。
- 两者通过 `state/` 下的文件解耦，互不感知。

## 二、配置结构

IM 配置放在 `state/config.json` 的 `im` 字段：

```json
{
  "im": {
    "enabled": true,
    "interval_sec": 900,
    "channels": [
      {
        "name": "feishu",
        "enabled": true,
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
        "message_type": "text"
      },
      {
        "name": "dingtalk",
        "enabled": false,
        "webhook_url": null,
        "message_type": "text"
      },
      {
        "name": "wecom",
        "enabled": true,
        "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
        "message_type": "text"
      }
    ]
  }
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `enabled` | boolean | IM 总开关。`false` 则 IM Loop 直接跳过本轮 |
| `interval_sec` | integer | IM Loop 发送间隔（秒），默认 900 |
| `channels` | array | IM 渠道列表，每个渠道有独立开关 |
| `channels[].name` | string | 渠道标识：`feishu` / `dingtalk` / `wecom` |
| `channels[].enabled` | boolean | 该渠道是否启用 |
| `channels[].webhook_url` | string \| null | Webhook 地址，未配置为 null |
| `channels[].message_type` | string | 消息格式，当前统一 `text` |

## 三、自检流程

启动 SOP 的环境自检阶段，遍历 `im.channels` 中 `enabled: true` 的渠道，对每个渠道**真实发送一条带 `[测试]` 前缀的消息**，确认通道连通。

发送成功 → `ok`；失败或超时（3 秒）→ `fail`。

结果写入 `state/env_check.json` 的 `results` 数组，与工具检测并列：

```json
{
  "name": "im_feishu",
  "status": "ok",
  "note": "[测试] 消息发送成功"
}
```

- 命名规则：`im_` + 渠道名（如 `im_feishu`）。
- IM 项没有 `required` 字段，IM 永远不是关键项，全部失败也不终止启动。
- 自检结果只代表**启动时的初始状态**，运行期不更新。

## 四、运行期发送逻辑（IM Loop 每轮）

IM Loop 每轮醒来做以下事：

1. 读 `state/config.json` 的 `im.enabled` 和 `im.channels`。
2. 若 `enabled == false` 或没有 `enabled: true` 且 `webhook_url` 非空的渠道 → 更新 `im_last_status = "skipped"`，写一行日志，本轮结束。
3. 读 `state/env_check.json`，找 `name` 以 `im_` 开头且 `status == "ok"` 的渠道。
4. 读 `state/system_state.json` 和 `queue/tasks.json`，拼心跳消息。
5. **串行发送**：按 channels 数组顺序逐个尝试，每个渠道最多等 3 秒。
6. 至少一个渠道成功 → `im_last_status = "ok"`。
7. 全部失败或超时 → `im_last_status = "degraded"`，心跳消息降级写日志。
8. 更新 `state/system_state.json` 的 `im_last_sent` 和 `im_last_status`。
9. 睡 `interval_sec`，下一轮再来。

心跳消息格式：

```
【夜莺心跳】
时间：<ISO 时间>
系统状态：running / idle
当前任务：<task_id 或 "无">
最近完成：<最近 commit message 或评估 summary>
本轮错误：<错误数量或 "无">
最后心跳：<距离上次心跳的时间>
```

## 五、失败与降级策略

| 场景 | 行为 |
|---|---|
| 自检时某渠道 `fail` | 标记 `fail`，运行期跳过该渠道 |
| 运行期发送超时（3 秒） | 该渠道本轮失败，继续尝试下一个渠道 |
| 运行期发送报错 | 同上，写日志，不重试 |
| 所有渠道都失败 | `im_last_status = "degraded"`，心跳消息写 `logs/nightingale.log`（带 `[IM降级]` 前缀） |
| 未配置任何可用渠道 | `im_last_status = "skipped"`，写一行日志 |

**核心原则**：

- 不重试。
- 不更新 `env_check.json`（运行期网络抖动是临时性的，每轮都重新尝试）。
- 不累计失败次数。
- 不聪明、不优化、不自我修复。
- 每轮都是全新尝试，上一轮失败不影响这一轮。

## 六、system_state.json 新增字段

`state/system_state.json` 增加两个字段：

```json
{
  "im_last_sent": null,
  "im_last_status": "skipped"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `im_last_sent` | string \| null | IM Loop 最近一次尝试发送的时间（ISO 时间）。兼做 IM Loop 存活证明 |
| `im_last_status` | enum | `ok`（至少一个渠道成功）/ `degraded`（全失败降级）/ `skipped`（未配置或未启用） |

## 七、脚本：im_loop.sh

IM Loop 由独立脚本 `scripts/im_loop.sh` 承载，**必定单独启动**，不由主 Loop 拉起。

- 纯 bash + python3，无 LLM 调用。
- 循环：读配置 → 发消息 → 更新状态 → 睡 → 再来。
- 单渠道超时 3 秒，串行发送，不并行。
- 与 `loop.sh` 平级，各自独立运行。

> 脚本全文维护在 `scripts/im_loop.sh`（`build_context.py` 生成全貌上下文时自动并入）；本文只讲机制，不内嵌脚本重复。
