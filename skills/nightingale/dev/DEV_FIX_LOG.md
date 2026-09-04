# Nightingale DEV 修复记录

> 用途：给夜莺维护者 / 使用者看的**开发侧变更档案**，按批次记"修了什么问题、为什么、怎么修、改了哪些文件"。设计口径仍以 `docs/`、`references/` 为准；本文件不重复设计，只讲变更来龙去脉与取舍，**不参与夜莺运行行为**。
> 记法：一批一节；症状写实测跑出来的证据，不写空话；每节末尾带一行"落点"（改了哪些文件）便于回查。
> 补充：这是一份会随时间过期的记录——新增一批就在顶部插一节（带日期），旧批不用回改。

## 2026-09-05 批次：pro6 / pro8 实测驱动的修复

这批问题几乎都不是设计稿拍脑袋改的，而是把夜莺真的开起来整夜跑（pro8、pro6 两个项目）之后，从**运行日志**里暴露出来的。核心矛盾只有一个：**设计曾假设"会话就是 Loop、workflow 完成通知能续命"，真机证明两条都站不住**。下面多数修复围绕它展开。

### 1. Loop 从来没有真正存在 —— 点火一次就死、没有 15 分钟汇报

- 症状（pro8 日志）：点火只拉起一个 workflow，主进程之后**没有**每 15 分钟的循环汇报。进程被杀后回来只见到一句 `No completion record was found for background workflow ... from the previous session`——说明"心跳靠 workflow 完成通知续命"这条，通知**随会话单轮结束就丢了**。
- 根因：把"交互会话"当成 Loop 本体（"会话即 Loop"是虚构）；心跳由 workflow 完成事件驱动，而不是由定时器驱动。
- 修复：Loop 本体 = 约 15 分钟一次的**会话内定时唤起**（cron），心跳由定时器 + 状态文件驱动，**不依赖任何完成事件**。每轮唤醒固定四步：①时段直取 `schedule_mode.py` 的 `args` → ②查队列有无活 → ③有活且无在跑才派一次 Workflow（防重入）→ ④读落盘把 `system_state.json` 同步到一致、汇报一行心跳再睡。headless 后备 = `loop.sh`，参数从 workspace 改为**项目目录**。点火 = 骨架/配置/seed + 调一次 Workflow + **注册约 15 分钟循环唤起**（三件事一口气做）。
- 落点（改了哪些文件）：`SKILL.md` §五/§六、`docs/02_startup_sop.md` 步骤 5–6、`scripts/loop.sh`、`scripts/im_loop.sh`（统一 PROJECT→ROOT 口径）。
- 验证：2026-09-05 凌晨 pro6 点火后，注册的循环唤起 02:20 如期触发并完成整轮心跳，中断后恢复正确。

### 2. 驱动者点火前读源码、想下场 —— "不能直接启动吗？"

- 症状（pro8 日志）：主 agent 点火前先读 / 理解 `nightingale_cycle.js`，才敢填参数投 Workflow。
- 根因：入口把"驱动"与"开发"职责混在一起；参数靠占位手填（必然要翻脚本）；没有任何硬性拦截。
- 修复（双管齐下）：
  - **职责铁律**：驱动者只点火不下场——搭骨架 → 落配置 → seed → 调一次 Workflow → 注册循环唤起 → 之后每轮被叫醒做心跳。绝不自己读/改/测项目代码、不做任务分析、不动项目 git、**不打开 `nightingale_cycle.js`**。
  - **参数直取**：`schedule_mode.py` 输出一段现成的 `args`（含 `root/mode/pairs/dispatch`；`tools` 从 `state/env_check.json` 并入 `status=ok` 的工具名、排除 im_* 渠道项）；驱动把该 `args` 段照抄进 Workflow 即可，不手拼、不翻模板。
- 落点：`SKILL.md` 入口「驱动者只点火不下场」、`docs/02_startup_sop.md` 步骤 5–6、`docs/08_tool_integration.md` §五、`scripts/schedule_mode.py`、`references/prompts.md` B 节说明。

### 3. 模糊目标被二次追问

- 症状（pro6 日志）：用户已说"想改动这个项目 / 继续打磨"，驱动者仍补问一句更具体的目标。
- 根因：把任务方向当必收项，且对"方向性模糊表达"没兜底语义。
- 修复：方向**可选**——用户给"改动/继续打磨/优化这个项目"这类方向性表达、或只给目录没提方向 → 一律按默认目标「打磨/优化该项目」处理，**不许追问**；可验收结果不必启动时定义，由首轮评估者读实际代码细化。只有既没给目录、又没说"打磨哪个"时才提示一句。
- 落点：`SKILL.md` 入口语义 + §五、`docs/02_startup_sop.md` 步骤 2、`references/config.template.json`（goal 占位）、`references/prompts.md` A1。

### 4. git 规则过度设计 —— 探查上级仓库、问继承、读父仓脏状态

- 症状（pro6 日志）：pro6 自身无 git，驱动者却一路探查上级 `01_llv_code`（submodule 根）的 git、读父仓 `.gitignore`/脏状态、纠结要不要沿用父仓，还为此打断用户。
- 根因：把夜莺要部署的"多层 submodule 工作区"误当成一般项目场景，为不存在的问题过度设计；正常项目没这么绕。
- 修复：只看**项目目录自身**有没有 `.git`——① 有 → 问一句「沿用这个 git 吗？」（沿用 = 复用历史与 remote，默认沿用）；② 无 → **直接 `git init` 一个独立仓**，不问、不探查上级目录是不是别的 git（submodule/子树）、不读父仓 `.gitignore`/脏状态（空仓 init 无风险）。`.nightingale/` 骨架一律 gitignore。
- 落点：`docs/02_startup_sop.md` 步骤 2、`docs/04_directory_state.md`（骨架段 + 设计要点，两处）、`references/prompts.md` A1 —— 四处同口径。
- 验证：2026-09-05 pro6 点火即此行为——独立 init + `.gitignore` 隔离 `.nightingale/` 与数据文件，不碰外层共享仓。

### 5. 循环唤起 prompt 缺固定模板（行为可能各场漂移）

- 背景：第 1 条定下"会话内定时唤起 = Loop"后，每场点火注册循环唤起时的措辞都是临场写的，防重入守卫与心跳字段口径容易漂移。
- 修复：`references/prompts.md` 新增 C 节「循环唤起 prompt」——把固定四步 + 防重入守卫 + 一行心跳字段格式焊成一段**可原样注册**的模板（点火注册 cron 时只替换 `<项目目录>`、`<nightingale skill>` 两个占位）；原 IM 心跳格式节顺延为 D。`SKILL.md` §六补一行使用指针，保证照抄即用、口径不漂。
- 落点：`references/prompts.md`（新增 C 节 / 原 C 顺延 D）、`SKILL.md` §六。

### 顺带澄清（是设计，不是 bug，别当缺陷修）

- **激进时段 `pairs=5` 首轮只跑一个功能对**：open 分支永远是单功能对先出第一版，并行（dispatch + 测试/文档/审查/优化角色对）从 advance 轮次开始。属有意为之。

### 讨论过、明确暂不采纳

- **防重入守卫分不清"慢但活着"和"悄悄死掉"**：2026-09-05 pro6 恢复日志暴露——守卫只判"文件没更新 → 跳过"，无法区分正常慢速轮次与静默死亡；那一次能恢复，靠的是 harness 的 `No completion record` 死亡通知 + 驱动者翻 workflow journal，两者都不在固定四步模板里。已提出把 `docs/09` §六的 90 分钟兜底并进固定四步、并给 `system_state.json` 加 in-flight 时间锚（`in_flight_workflow_id` / `in_flight_since`），评估后认为优先级不高，**暂不改**。将来若出现"workflow 静默死掉、夜莺永久停摆"的实证再回来补。
