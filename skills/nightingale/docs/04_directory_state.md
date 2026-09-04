# 目录结构与状态文件

> 说明夜莺运行目录怎么组织、状态落在哪些文件、各自何时被写。每个文件的**结构与样例以 `references/*.template.json` 为准**（唯一 schema 事实源）；本文不重复字段细节，只列职责与写入时机。

## 一、目录骨架

用户只给一个**项目目录**（打磨对象：已有项目或空目录）。夜莺在项目目录下建运行骨架 `<项目目录>/.nightingale/`（下称 **ROOT**），运行态全放 ROOT、与项目本体隔离：

```
<项目目录>/.nightingale/      # ROOT：夜莺运行骨架（被项目 .gitignore 排除，不跟踪）
├── queue/       任务队列、评估结果、干预指令（待定）
├── state/       系统状态、配置、心跳、环境自检结果
└── logs/        运行日志

<项目目录>/                    # 打磨对象本体：代码/git/测试直接落这里，不建 workspace 子目录
```

git 规则在启动时定：只看**项目目录自身**有没有 `.git`——自身已是 git → 问是否沿用（复用历史与 remote，默认沿用）；自身无 `.git` → 直接 `git init` 独立仓，上级目录是不是别的 git 都不探查（空仓 init 无风险）。`.nightingale/` 骨架一律 gitignore。

## 二、文件与写入时机一览

| 目录 | 文件 | 用途 | 写入时机 |
|---|---|---|---|
| `queue/` | `tasks.json` | 任务队列：每条含 `task_id / goal / status` 等 | 加任务时；状态变更时更新 |
| `queue/` | 各任务评估结果（主） | 功能对评估者的 `verdict/actions` | 每轮 workflow 结束时 |
| `queue/` | `eval/<task_id>.<role>.json` | 测试/文档/审查/优化角色对的评估结果 | 激进时段每轮，各角色对覆盖式写 |
| `state/` | `config.json` | 运行配置（任务目标 + 项目目录 + 默认值，启动时写入） | 一次性初始化 |
| `state/` | `env_check.json` | 环境自检报告（各工具 ok/fail/skipped） | 一次性初始化 |
| `state/` | `system_state.json` | 系统状态：心跳时间、当前执行单元、IM 发送状态等（单一真相源） | 每轮心跳时；`im_last_*` 字段由 IM Loop 更新 |
| `state/` | `last_heartbeat` | 最近一次心跳时间戳 | 每轮心跳时 |
| `logs/` | `nightingale.log` | 心跳/派发/错误日志 | 持续追加 |

> 注：任务状态字段取值沿用 **pending / running / done / failed / interrupted**；中断恢复时把"running 但实际已死"的任务标为 `interrupted`，从最近一致状态续跑。

## 三、设计要点

- **文件是唯一真相源**：不依赖任何对话上下文；中断后读文件即可续。
- **控制条目可进队列**（保留能力）：如 PAUSE / STOP / PRIORITY，实现时再定。
- 打磨对象 = 项目目录本身：git 规则在启动时定（只看项目目录自身——已有则问沿用、无则直接 init，不探查上级），每轮有意义变化 = 一个 commit，直接提交到项目 git。
