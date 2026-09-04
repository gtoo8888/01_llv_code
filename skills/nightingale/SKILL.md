---
name: nightingale
description: 让 agent 通宵/长时间自主迭代干活：常驻心跳循环 +「开发者→评估者」闭环（读任务队列 → 做优先级最高的一条 → git commit → 评估产出 → 落盘），直到用户喊停、次日人工收工。用于让 agent 整夜反复打磨一个独立小项目。
---

# Nightingale（夜莺）

> 本文件只是**入口**：是什么、怎么用、去哪读。完整细节按章节拆分在 `docs/` 下，**按需打开对应文件，别一次把全部内容塞进上下文**。

> **入口语义（先读）**：点名本 skill（`/nightingale` 或"用夜莺跑个任务"）= 使用者派一个项目整夜打磨，**仅此一种入口**。启动只向用户收**两样**：①**任务方向**（可选，开口第一句就问"这次想让我整夜打磨/开发什么项目？"）；②**项目目录**（已有项目或空目录，给个路径即可，它就是打磨对象）。其余（运行时长=无限直到喊停、时段=按时钟自动判、危险边界=固定默认、IM=自动、工具=自动自检）全部默认/自动，**不逐项问**。
> **模糊方向即默认目标，不许追问**：用户说"改动/继续打磨/优化/完善这个项目"这类方向性表达、甚至只给目录没提方向 → 一律按默认目标「打磨/优化该项目」处理，**不再补问一句更具体的目标**——可验收由首轮评估者读实际代码细化，首条任务就 seed 这个默认目标，workflow 内开发者/评估者会自己把活拆细。只有当用户既没给项目目录、也没说"打磨哪个"时才需要提示一句。
> **驱动者只点火不下场（主会话铁律）**：你的活 = 搭骨架 → 落配置 → seed 首条任务 → **调一次 Workflow 点火 → 注册约 15 分钟一次的循环唤起（Loop）** → 之后每轮被叫醒做一次心跳、汇报、睡去。**绝不自己读/改/测项目代码、不跑项目测试、不做任务分析、不动项目 git**——那是 workflow 内开发者/评估者的活。**点火参数不靠读源码/读模板推导**：不打开 `nightingale_cycle.js`、不手算时段、不重读 SOP——`root` 直接填 `<项目目录>/.nightingale`，`mode/pairs/dispatch/tools` 直接跑 `python3 scripts/schedule_mode.py <ROOT>` 取它输出的 `args` 段照抄进 Workflow。`.nightingale/` gitignore 这类由 workflow 内开发者兜底，驱动者不预先代办。心跳由定时器驱动、状态文件判断，**不依赖 workflow 完成通知续命**（通知随会话单轮结束会丢）。可验收结果不必启动时定义，用户一句话即可，细化交给首轮评估者。开发夜莺自身不经此入口（普通会话里直接改本 skill，受文末规范约束）。

## 一、它是什么

夜莺 = 一个"在时间中持续存在"的任务系统：启动后整晚/数小时自主地醒来、检查、派活、落盘、睡去；**没有"完成"的那一天**，只有用户喊停才收工。

核心设计：**把"活着"和"干活"分开**——Loop（心跳）永不停止，Agent 层（workflow 执行单元）有始有终、做完就退出。


## 二、三条铁律

夜莺的首要目标是**活下去**——持续地跑一个晚上、一天、两天，直到用户喊停。任务这轮做不完善可以下一轮继续，但绝不能停下；以下三条铁律都服务于这个前提。

1. **活着与干活分离**：心跳循环极简、无"完成"分支；退出的是执行单元，不是夜莺。
2. **状态只落文件**（`queue/` `state/` `logs/`）：文件是唯一真相源，不依赖对话上下文；中断可从检查点续。
3. **失败不阻塞心跳**：一次失败只重试有限次，仍败则标记 `failed` 继续下一件。

## 三、目录结构

```
nightingale/
├── SKILL.md                     # 入口（本文件）—— 是什么/怎么用/去哪读，保持轻量
├── dev/                         # DEV 变更档案 —— 按批次记修复与取舍（非设计口径，不改运行行为）
│   └── DEV_FIX_LOG.md           #   修复记录（本批 2026-09-05：pro6/pro8 实测驱动）
│
├── docs/                        # 成稿细节 —— 一章一文件，各自独立可读
│   ├── 01_architecture.md       #   架构总览：六层 + Watchdog、各层职责
│   ├── 02_startup_sop.md        #   启动 SOP：一次性初始化 + 持续运行循环
│   ├── 03_closed_loop.md        #   闭环协议：评估者 verdict/actions ↔ 开发者
│   ├── 04_directory_state.md    #   目录骨架与状态文件
│   ├── 05_observability.md      #   可观测性：IM 心跳汇报的固定字段
│   ├── 06_recovery.md           #   收工、恢复与失败边界
│   ├── 07_known_limitations.md  #   已知简化与实现路线
│   ├── 08_tool_integration.md   #   工具接入：形态/清单/自检/注入
│   ├── 09_runtime_schedule.md   #   运行时段与多角色并发：时段切换、角色对、分发者
│   └── 10_im_integration.md     #   IM 接入：渠道/自检/发送/降级（独立进程）
│
├── scripts/                     # 脚本 —— 心跳/调度 + 全貌上下文合并
│   ├── nightingale_cycle.js     #   每轮心跳的 workflow 编排（时段/角色对感知）
│   ├── schedule_mode.py         #   按 config.schedule 判 mode/pairs/dispatch
│   ├── loop.sh                  #   无 LLM 的心跳循环（唤 agent 跑 workflow）
│   ├── im_loop.sh               #   IM 通知循环（独立进程，单独启动）
│   └── build_context.py         #   合并全部文本 → NIGHTINGALE_CONTEXT.md
│
└── references/                    # 模板与样例 —— 子代理 prompt 稿 + ROOT 运行骨架文件样例
    ├── prompts.md                 #   各阶段/子代理 prompt 稿（后备手工驱动）
    ├── tasks.template.json        #   样例 → queue/tasks.json
    ├── eval.template.json         #   样例 → queue/eval/<task_id>.json
    ├── config.template.json       #   样例 → state/config.json
    ├── env_check.template.json    #   样例 → state/env_check.json
    ├── system_state.template.json #   样例 → state/system_state.json
    └── heartbeat.example.txt      #   样例 → IM 心跳汇报消息
```

> **生成全貌上下文**：运行 `python3 scripts/build_context.py`，会把全部文本合并为 `NIGHTINGALE_CONTEXT.md`，供一次性投喂给大模型。该产物自动生成，勿手改；改源文件后重跑即可。

## 四、何时用 / 何时不用

- **用**：任务需持续迭代数小时以上（整夜打磨一个独立小项目、逐步批量处理）。
- **不用**：一次性短任务；碰主线仓库或重要数据、需人工在场的场景。拿不准先问用户。

## 五、快速上手

按 `docs/02_startup_sop.md` 走。起步就两件事：

1. **与用户确认**：**项目目录**（已有项目或空目录）必收；任务方向一句话可选——若说"改动/继续打磨/优化这个项目"这类模糊表达、或只给目录没提方向，一律按默认目标「打磨/优化该项目」处理，**不再追问**。其余一律默认，不逐项问。
2. **搭骨架点火**：在项目目录下建 `<项目目录>/.nightingale/` 骨架（内含 `queue/ state/ logs/`）→ 写入配置与首条任务 → 环境自检 → **调一次 Workflow 点火** → **注册约 15 分钟一次的循环唤起（Loop）**；此后每轮被叫醒做一次心跳（见 §六），汇报一行后睡去等下一轮。会话需整夜开着（通宵的姿势），主会话不碰项目本体。

## 六、运行循环

**Loop 本体 = 一个约 15 分钟唤醒一次的循环**，靠会话的**定时唤起**（cron / 循环任务）实现；headless 后备见 `scripts/loop.sh`。**每轮唤醒 = 一次心跳**——都醒来、都汇报一行、都落盘，无活就是 idle，循环往复直到用户喊停。不依赖"一次性 workflow 跑完的通知"来续命：那个通知随会话单轮结束就会丢，所以心跳必须由定时器驱动、由状态文件判断，而不是等事件。

**每轮心跳固定四步**：

1. **时段直取**：跑 `python3 scripts/schedule_mode.py <项目目录>/.nightingale`，取输出里的 `args` 段（含 `root/mode/pairs/dispatch/tools`）。别手拼、别打开 `nightingale_cycle.js` 核对。
2. **确定性检查**：读 `queue/tasks.json`，存在 `status ∈ pending | running` → 有活；否则本轮 idle。
3. **派活（有活时）**：调一次 Workflow 跑 `scripts/nightingale_cycle.js`，args = 第 1 步的 `args` 段。**防重入**：同一时刻只跑一个 Workflow——唤醒时若上一轮尚未收尾（`tasks.json` / 评估文件未更新），只记心跳、不重复派活，宁跳一轮也不双开。
4. **同步 + 汇报**：Workflow 返回或判定 idle 后，把 `state/system_state.json`（`mode / active_pairs / current_task / status / last_heartbeat / error_count / recent_completion`）落到一致，按固定格式汇报一行心跳（系统状态、当前任务、最近完成、本轮错误），睡去等下一轮。

> **注册循环唤起的 prompt 用固定模板**：点火时把 `references/prompts.md` C 节的「循环唤起 prompt」**原样**粘进定时唤起（替换 `<项目目录>` 为实际路径、`<nightingale skill>` 为该 skill 目录）。它与上面四步一一对应，照抄即可；别每场临时另写，避免防重入守卫与心跳字段口径漂移。

调用形状：

```
Workflow({ scriptPath: '<nightingale skill>/scripts/nightingale_cycle.js',
  args: <python3 scripts/schedule_mode.py <项目目录>/.nightingale 输出里的 args 对象> })
```

字段含义：
- `mode/pairs`：保守时段只跑 1 个功能对（既有串行行为）；激进时段并行最多 `aggressive_max_pairs` 个角色对（功能/测试/文档/审查/优化），每对各读写自己的 eval 文件。
- `dispatch`：刚切入激进时段的那轮置 `true`，workflow 先跑**任务分发者**给各角色派初始活。
- `tools`：schedule_mode 已从 `state/env_check.json` 并入 `status=ok` 的工具名，注入开发者 prompt；驱动方不必单读 env_check。

一次 Workflow 调用即一个完整周期：workflow 先判 `open / advance / idle`，有活就内嵌「开发者做 priority 最小的一条 → `git commit` → 评估者给 `verdict/actions` → 落盘」；`verdict: done` 则任务标完成，workflow 返回摘要后退出。**不要用 Agent 工具手搓开发者/评估者子代理**——闭环已写死在 `nightingale_cycle.js` 里。无活则 workflow 返回 idle。时段策略见 `docs/09_runtime_schedule.md`，点火与唤醒细节见 `docs/02_startup_sop.md` 步骤 5–6。


# !!!!开发夜莺须遵循的规范!!!!

> 给接手、维护、落地这个 skill（docs、scripts、references）的人
> 夜莺的使用者不需要关心
> 本文只讲"动手开发时"的约定；它们是夜莺自身运行规范之上的元规则。
> **何时生效**：仅当本会话本身就是在开发/维护夜莺（直接改 docs/、scripts/、references/，或任务目标＝夜莺自身）时。
> **何时不生效**：通过 `/nightingale` 派项目的会话是使用者场景，本规范不适用，也**不是启动时要问的选项**——不要开头询问"使用者还是开发者"。

## 一、文档编写

1. **docs 不做交叉引用，每篇自包含**：每个文件可单独读。需要别处的概念就在本文件里讲清楚，不出现"见 xxx.md"这类指引。
2. **文档不写版本号 / 阶段**：正文一律称"夜莺"，不出现"夜莺 v2 / v1""初步开发版 v2"之类的阶段或版本表述。旧/新阶段只在人与人的沟通里区分，不落进任何文件；需要版本信息时用固定不变的单一版本号，不随迭代变化。
3. **一章一文件，SKILL.md 保持轻量**：入口（SKILL.md）只做导览与指向；任何大段细节放进 docs 对应章节，不要都堆进 SKILL.md。

## 二、落地一致性

1. **docs 是唯一口径**：动手写 scripts / prompts 前先读对应章节；prompt 模板的字段必须与闭环协议一致——评估者产出 `verdict/actions`，开发者消费 `actions`，别另起一套。
2. **字面量固定**：任务状态只用 `pending / running / done / failed / interrupted`；目录与状态文件的命名沿用既定约定，不自行发明。
3. **改动即留痕**：每轮"有意义"的改动对应一个 git commit，便于复盘与回滚。
4. **驱动形态唯一**：交互会话做 Loop 时，每轮心跳用 Workflow 工具跑 `scripts/nightingale_cycle.js`（`args.root`=ROOT，即 `<项目目录>/.nightingale`），**不要用 Agent 手搓开发者/评估者子代理**；只有没有 Workflow 工具时才走 `references/prompts.md` 的后备手工驱动。

## 三、范围与安全

1. 只开发夜莺自身或独立小项目；碰主线仓库、重要数据，或涉及删除/覆盖等操作，先问用户。
2. 拿不准的结构取舍，先在沟通里说清楚再落文件，不擅自改文档/目录结构。

## 四、开发与测试的会话边界

1. **开发会话只改不测**：对 skill 自身的开发（改 `docs/` / `scripts/` / `references/`）只发生在当前对话里，不在本会话运行、触发或端到端测试这个 skill；skill 的实际运行与测试由用户在**新开的另一个对话**里手动进行。
2. **开发会话不碰安装与生成产物**：不主动查找或比对 skill 的"已安装副本"装在哪（如工作区根 `.claude/skills/`）；不代跑 `build_context.py` 重生成 `NIGHTINGALE_CONTEXT.md`，也不重装副本。这些属于"使用侧"，等真正要用这个 skill 时由用户来做。
