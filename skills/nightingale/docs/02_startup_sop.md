# Nightingale 启动 SOP

> 本 SOP 描述从"启动 skill"到"进入持续运行"的完整流程：**步骤 1–4 为一次性初始化，步骤 5 进入无限循环，步骤 6 是循环内的执行单元**。Watchdog（步骤 4）当前为占位。

> **目录约定（先读）**：用户只给一个**项目目录**（已有项目或空目录，即打磨对象）。夜莺在项目目录下建 `<项目目录>/.nightingale/` 运行骨架，运行态（`queue/ state/ logs/`）全放其内；下称 **ROOT**。循环阶段（步骤 5–6）的一切读写都在 ROOT 内完成，不碰项目本体。

---

## 阶段一：一次性初始化（顺序执行）

### 1. 加载内容

- 加载 nightingale 的运行指令（`SKILL.md` + 本文档）、`scripts/` 下的确定性脚本、`references/` 下的 prompt 模板。
- 目的：让 Loop 层具备完整上下文，知道如何调度、如何读写文件、如何定义开发者/评估者的任务。

### 2. 用户交互（只收两样，其余自动）

**开口第一句就问**："这次想让我整夜打磨/开发什么项目？项目目录给我一个"。启动只向用户收**两样**：

| 输入 | 说明 |
|---|---|
| ① 任务方向（可选） | 想打磨/开发什么，一句话即可；可验收结果不要求现在给，由首轮评估者细化 |
| ② 项目目录 | 已有项目或空目录，一个路径；它就是打磨对象（**必收**） |

**模糊方向 = 默认目标，不追问**：用户若说"改动/继续打磨/优化/完善这个项目"这类方向性表达、或只给目录没提方向 → 一律按默认目标「打磨/优化该项目」处理，**不要再补问一句更具体的目标**。首条任务就 seed 这个默认目标，workflow 内开发者/评估者会读实际代码自己把活拆细。只有既没给目录、也没说"打磨哪个"时才需要提示一句。

其余项**一律默认/自动，不逐项问**：

- **运行时长**：默认无限，直到人工喊停。
- **时段策略**：按时钟自动判（读 `schedule`，缺省恒保守），用户不选。
- **危险操作边界**：固定默认——删除/覆盖/碰项目外的东西一律不自动做，确需时归为 `failed` 上报，不弹窗等用户。
- **IM 渠道**：自动自检可用渠道后开启，不逐个问。
- **工具清单**：自动按模板自检，可用的注入、不可用的降级。

**git 规则**：只看**项目目录自身**有没有 `.git`——① 自身已是 git 仓库 → 问一句「沿用这个 git 吗？」（沿用 = 复用其历史与 remote，默认沿用）；② 自身无 `.git` → **直接 `git init` 一个独立仓**，不问、也不探查上级目录是不是别的 git（submodule / 子树这类）、不读父仓 `.gitignore`/脏状态——空仓 init 无风险。ROOT 骨架目录一律 gitignore。

**骨架（点火前建好）**：在项目目录下建 `<项目目录>/.nightingale/`，写入 `state/config.json`（ROOT 的配置，字段对齐 `references/config.template.json`）、seed 首条任务到 `queue/tasks.json`。打磨产物直接落项目目录，不再建 workspace 子目录。

> **告知用户**：进入第 5 步心跳循环后，夜莺处于**无人值守**状态——任何二选一/确认弹窗都会自动选择第一个选项（默认或最保守项），不会等待人工操作。**本步是最后一次人工确认与干预的机会**；进入运行循环后想干预，只能改 `queue/tasks.json` 或杀进程。

产出：`<项目目录>/.nightingale/state/config.json` 一份结构化配置，供后续步骤与 Loop 层使用。

### 3. 环境自检

按 `state/config.json` 里 `tools.items` 的清单逐项自检，检测方式由每项 `type` 决定：

- `command`：执行 `check` 指定的最小命令，退出码 0 → ok；超时或非 0 → fail。
- `mcp`：按 `check` 描述做一次最小调用。
- `skill`：检查目录与入口文件是否存在、可读。

产出结构化自检报告写入 `state/env_check.json`：每项标 `ok / fail / skipped`（`skipped`＝本轮未检测）并附 `note`；`critical_ok` = 所有 `required: true` 项均 ok。

IM 检测紧随工具自检之后：遍历 `im.channels` 中 `enabled: true` 且有 `webhook_url` 的渠道，逐渠道真实发送一条带 `[测试]` 前缀的消息确认连通；结果也写入 `env_check.json` 的 `results`（`name` 为 `im_<渠道名>`）。IM 项无 `required`，全部失败也不终止启动。

`required: true` 的关键工具（模板默认 git / python3 / pip）fail → 提示用户并**终止启动**；非关键工具 fail → 标记不可用、降级继续，且该工具不出现在本轮可用工具注入里。

### 4. 派发 Watchdog（占位步骤）

- 平台支持子代理监控 → 启动独立 watchdog，监控 Loop 心跳，超时执行两级干预（NUDGE → KILL+RESTART）。
- 平台暂不支持 → 跳过，并在状态记录 `watchdog_enabled = false`。
- 当前定位：**占位**，保留设计，待能力跟上后启用。

---

## 阶段二：持续运行（无限循环）

### 5. 启动 Loop（主循环）

**Loop 本体 = 一个约 15 分钟唤醒一次的循环**，用会话的**定时唤起**（cron / 循环任务）实现：到点被叫醒 → 做一次心跳 → 汇报 → 睡去。**不依赖"一次性 workflow 完成的通知"续命**——那种通知随会话单轮结束会丢，所以心跳由定时器驱动、以状态文件判断，而不是等事件。

**两种载体，取其一，不要混跑**：
- **A（默认 · 会话内定时唤起）**：交互会话就是 Loop 的家——点火后注册约 15 分钟一次的循环唤起，每轮被叫醒做下面的"固定动作"。会话上下文只留每轮心跳摘要，执行细节都在 Workflow 的子代理里。前提：会话整夜开着（通宵的姿势）；中途会话若被关闭，恢复后回来**补注册循环唤起**即可。
- **B（loop.sh 保活 / headless）**：`scripts/loop.sh <项目目录>` 以固定间隔（默认 900s）自己醒来，跑同样的"固定动作"，有活时经 `NIGHTINGALE_AGENT_CMD` 唤起 headless agent 跑 Workflow 并同步 `state/system_state.json`。无交互会话，汇报只能落 log 或走 IM，不在会话里可见。

**点火（A 载体）**：骨架、配置、首条任务就绪后，一口气做三件事——
1. **调一次 Workflow 点火**（不等下一间隔、不自己先下场做任务分析/跑测试/动项目 git，也不打开 `nightingale_cycle.js` 核对参数）；首轮由 workflow 内开发者完成第一版并把闭环跑通；
2. **注册约 15 分钟一次的循环唤起**作为 Loop（每轮 = 一次心跳，动作见下）；
3. 若启用 IM（config 有启用渠道），另行启动 `./scripts/im_loop.sh <项目目录>`。

**每轮唤醒固定动作（A 与 B 相同）**：

1. **时段判定（直取参数）**：跑 `python3 scripts/schedule_mode.py ROOT`（ROOT = `<项目目录>/.nightingale`），取输出里的 `args` 段（`{mode,pairs,dispatch,tools}` 齐全）直接作本轮 Workflow 的 args。**不要自己读时钟/读模板手推时段，也不要手拼 tools。**
2. **确定性检查**：读 `queue/tasks.json`，存在 `status ∈ pending | running` → 有活；否则 idle。
   - 无 → 本轮 idle：`system_state.json` 记本轮 mode、`active_pairs = null`、更新 `last_heartbeat`，**不调 workflow、不调 LLM**。
   - 有，但**上一轮 Workflow 尚未收尾**（投出后 `tasks.json` / 评估文件自投出时刻后未更新，说明仍有一个在跑）→ **不重复派活**，记心跳、汇报"上一轮仍在跑"，睡去——宁跳一轮也不双开。
   - 有且无在跑 → 进入步骤 6 调一次 Workflow。
3. **状态同步**：Workflow 返回后，读落盘结果（各 eval 文件、`tasks.json`、项目 git log），把 `state/system_state.json` 的 `mode / active_pairs / current_task / status / last_heartbeat / error_count / recent_completion` 更新到一致状态，写一行日志。
4. **汇报一行心跳**（在会话里可见），睡去等下一轮。

> **心跳汇报一行**，字段全从 `state/system_state.json` 与 `queue/tasks.json` 取、不调 LLM 生成：`【夜莺心跳】时间｜系统状态：running (N pairs) 或 idle｜当前任务｜最近完成｜本轮错误｜最后心跳`。

Loop 层**永不"完成"**，只有用户喊停或外部杀进程才收工。

### 6. 每轮心跳 = 调用一次 Workflow（执行单元，有始有终）

**投递方式唯一**：调用 Workflow 工具运行 `scripts/nightingale_cycle.js`。**args 不手拼**——先跑 `python3 scripts/schedule_mode.py ROOT`（ROOT = `<项目目录>/.nightingale`），把它输出里的 `args` 段（含 `root/mode/pairs/dispatch/tools`）原样作 Workflow 的 args；驱动者**不必打开 `nightingale_cycle.js` 或翻模板核对参数**。调用形如：

```
# args = <python3 scripts/schedule_mode.py ROOT 输出里的 args 对象>
Workflow({ scriptPath: '<nightingale skill>/scripts/nightingale_cycle.js', args: <上面的 args 对象> })
```

（字段形状参考：`args = { root: '<项目目录>/.nightingale', mode: '<conservative|aggressive>', pairs: <1|N>, dispatch: <true|false>, tools: '<status=ok 的工具名>' }`）

- `mode`：`conservative` = 只跑 1 个功能对（既有串行行为）；`aggressive` = 并行最多 N 个角色对。
- `pairs`：激进时段的并发角色对数上限（`schedule.aggressive_max_pairs`，默认 5）。
- `dispatch`：刚切入激进时段的那轮为 `true`，workflow 先跑**任务分发者**给各角色派初始活。
- `tools`：可选，环境自检 `status=ok` 的工具名，注入开发者 prompt。

一次调用即一个完整周期，脚本内部分两段：

1. **Inspect**（脚本内只读子代理）：判本轮 `open`（有 pending）/ `advance`（有 running）/ `idle`；激进且 `advance` 时还判各角色 eval 文件是否就绪（缺则本轮要跑分发者）。
2. **Act**：开新任务或推进开发循环，内部走**闭环协议**——
   - **open（开新任务）**：单功能对——开发者做第一版实现（项目为空就从零搭骨架，已有代码则以现库为基增量实现），提交到项目 git（不重复 init），评估者评估写回主 eval 文件。
   - **advance（续轮，保守）**：单功能对——开发者读 `queue/eval/<task_id>.json` 的 `actions`、做 `priority` 最小的一条，`git commit` 并更新 `queue/tasks.json` 的 `iterations`；评估者评估写回主 eval 文件。
   - **advance（激进）**：需要时先跑**任务分发者**（为测试/文档/审查/优化四角色各 seed 一条任务到自己的角色 eval 文件），然后**并行**跑最多 N 个角色对（功能对 + 就绪的其余角色对）。每对各读各的 eval 文件、各做各的一条、各 commit；只有功能对更新 `queue/tasks.json` 与 `state/system_state.json`。
   - 落盘后 workflow 返回摘要（含实际跑的对数 `pairs_run`）并**自然退出**。

**Loop 的职责边界**：
- Workflow 返回后，Loop 只读落盘结果（各 eval 文件、`tasks.json` 状态、项目目录的 git log），据此把 `state/system_state.json` 的 `mode`（本轮判定值）、`active_pairs`（= 返回的 `pairs_run`，空转则 `null`）、`current_task / status / last_heartbeat / recent_completion` 更新到一致状态，记一行日志，再睡去等下一轮。
- 一个 workflow 已内含"开发 + 评估"整周期，**无需再另行投递评估者**；`verdict: done|failed` 的状态迁移由功能对评估者落盘、Loop 不再投新 workflow。
- **不要用 Agent 工具手搓开发者/评估者子代理**：闭环已写死在 `nightingale_cycle.js`，手搓会绕过状态机与检查点。要人工介入，直接改 `queue/tasks.json` 或杀进程收工。

**无人值守约束（自第 5 步起全局生效）**：运行循环期间用户不在电脑前。所有执行单元（开发者、评估者）执行命令或操作时，遇到任何交互式提示、二选一、确认询问，一律自动选择第一个选项（通常是默认/安全项），绝不弹出窗口等待用户；无法确定安全选项时，选最保守、不会造成破坏的选项。第 1–4 步一次性初始化阶段不受此约束，可正常与用户确认。

---

## 控制流示意

```
[步骤1-4 顺序执行]
       ↓
   ┌───────┐
   │ while │←──────────────┐
   └───┬───┘               │
       ↓ 醒来检查            │
   [有无任务？]             │
       ├── 无 → 记心跳，不调 LLM ──┤
       └── 有 → 调 Workflow：cycle.js (步骤6)
                     ↓
              workflow 执行完退出
                     ↓
              Loop 更新状态，准备下一轮
                     ↓
                回到 while 循环顶部
```
