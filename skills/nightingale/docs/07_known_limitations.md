# 已知简化与路线

> 夜莺先立规范、再逐步落地：`scripts/`、`references/` 主体已按蓝图落地（心跳调度、workflow 闭环、prompt 口径）。本文档记录**剩余简化、未落地项与未决设计点**，开发/改动前先看，知道哪些还没做。

## 一、已知简化

| 项目 | 状态 |
|---|---|
| 状态文件 schema | 已定稿：结构与样例以 `references/*.template.json` 为准 |
| 用户控制面（追加任务/调优先级） | 暂不做，粗暴杀进程即可 |
| 错误恢复 | 策略已定，实现路径未实测 |
| Watchdog 实现 | 占位，待平台能力支持（两级干预 NUDGE → KILL+RESTART） |
| 驱动方式（常驻主进程 vs 平台定时唤醒） | 待实际接线时验证 |
| 队列操作脚本 | 未实现 |
| 并发控制 | 日常单功能对串行；激进时段按 `config.schedule` 最多 N 角色对并行；无跨驱动互斥（默认单一驱动在跑） |
| 时段调度与多角色对 | 设计定稿：schema/模板/`cycle.js`/驱动接线已落地；激进并发的端到端实测与 git 冲突收敛待验证 |
| 工具接入 | 设计定稿：`tools.items` schema/模板/cycle.js 注入已同步；自检动作由启动步骤执行，无独立常驻检查进程 |
| IM 通知 | 设计 + `scripts/im_loop.sh` 已落地（独立进程、尽力而为）；多渠道实测与各平台 webhook 兼容性待验证 |

## 二、实现现状

- `scripts/nightingale_cycle.js`：每次心跳的 workflow 编排已落地——Inspect 判 `open/advance/idle`，保守时段单功能对串行（开发者做 priority 最小一条 → git commit → 评估者产 `verdict/actions` → 落盘），激进时段按 args 的 `mode/pairs/dispatch` 先按需跑分发者、再并行角色对，与本文档架构、闭环协议一致。
- `scripts/schedule_mode.py`：供驱动方按 `state/config.json` 的 `schedule` 判 `mode/pairs/dispatch`（缺省恒保守），workflow 内部不判时间。
- `references/prompts.md`：调度/开发者/评估者 prompt 均按 `verdict/actions` 口径编写；激进时段角色对遵循同一口径但读写各自角色 eval 文件。
- `scripts/loop.sh`：无 LLM 的心跳循环（醒→查队列→唤起 agent→记心跳→睡），唤起命令由外部配置。
- `scripts/im_loop.sh`：IM 通知循环（独立进程，单独启动）——读 `state/` 拼心跳消息、串行发 webhook、全败降级写日志，失败/崩溃不影响主 Loop。

尚未落地：队列操作脚本（追加/查询/状态变更）；对真实运行目录的端到端实测（含激进时段多角色对并发、git 冲突收敛、驱动侧墙钟超时执行）。

## 三、未决设计点（需讨论）

- 用户控制面要不要做（队列追加/优先级/暂停），以及以什么形式（文件控制条目 vs IM 指令）。
- Watchdog 的启用前提与两级干预的具体时序。
