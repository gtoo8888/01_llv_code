// nightingale_cycle.js —— 夜莺「一次心跳 = 一轮活」的 workflow
//
// 说明：
//  - 纯 JS（非 TS）。由 Workflow 工具运行：
//      Workflow({ scriptPath: '<本文件路径>', args: { root: '<项目目录>/.nightingale', mode, pairs, dispatch, tools } })
//  - 目录模型：ROOT = <项目目录>/.nightingale（夜莺运行骨架，只放 queue/state/logs）；
//    <项目目录> 本身是打磨对象——代码、git、测试都直接落在项目目录，不建 workspace 子目录。
//  - 脚本本身没有文件系统能力（无 fs/Date/随机数）；一切读写由它派发的子代理
//    用 Read/Write/Bash 完成，本脚本只做确定性编排与分支。
//  - 时段策略不在本脚本内判定（无 fs/时钟），由驱动方判定后经 args 传入：
//      mode   = 'conservative'（默认，只跑 1 个功能对，既有串行行为）| 'aggressive'（并行角色对）
//      pairs  = 激进时段角色对数上限（默认取 config.schedule.aggressive_max_pairs）
//      dispatch = 刚切入激进时段的那轮置 true，先跑任务分发者（重新 seed 各角色 eval 文件）
//      tools  = 环境自检 status=ok 的工具名，注入开发者 prompt（可选）
//  - 墙钟超时（agent/pair/workflow）由驱动/平台侧执行，本脚本不自行计时。
//  - 每轮只做“有界的一轮”：开一个新任务，或推进某 running 任务的一轮。激进时段这一轮
//    内部可并行多个“角色对”（开发者→评估者），每对各读各写自己的 eval 文件。
export const meta = {
  name: 'nightingale-cycle',
  description: '夜莺(nightingale)每轮心跳的调度：读任务队列，要么开跑一个新任务，要么推进一个运行中任务的开发循环(开发者→评估者→落盘，激进时段可并行多角色对)，要么仅心跳。',
  phases: [
    { title: 'Inspect', detail: '读取 queue/state，决定本轮动作与是否需要分发' },
    { title: 'Dispatch', detail: '激进时段为新角色的角色对分发初始任务' },
    { title: 'Act', detail: '开新任务或推进运行中任务（单功能对 或 多角色对并行）' },
  ],
}

const root = args && args.root ? String(args.root) : ''
if (!root) {
  throw new Error('缺少 args.root：请传入 ROOT（夜莺运行目录，即 <项目目录>/.nightingale），如 Workflow({scriptPath, args:{root:"/path/to/proj/.nightingale"}})')
}

// 项目目录 = ROOT 的上一级（ROOT 形如 <项目目录>/.nightingale）；打磨产物直接落项目目录。
// 若有人直接传了项目目录（root 不以 .nightingale 结尾），项目目录就当 root 本身用。
const project = root.replace(/\/+$/, '').replace(/\/\.nightingale$/i, '') || root

// 可用工具注入：驱动方从 state/env_check.json 读 status=ok 的工具名，经 args.tools 传入。
// 未提供（后备手工驱动模式）时，提示子代理先自读 env_check.json。
const toolsLine = args && args.tools
  ? '本轮可用工具：' + String(args.tools) + '\n'
  : '本轮可用工具：先自行读取 ' + root + '/state/env_check.json，只用 status=ok 的项。\n'

// 时段/并发参数（缺省 = 保守 1 功能对，与既有串行行为一致）
const aggressive = !!(args && args.mode === 'aggressive')
const requestedPairs = (args && Number(args.pairs)) || 1
const maxPairs = aggressive ? Math.min(Math.max(requestedPairs, 1), 5) : 1
const forceDispatch = aggressive && !!(args && args.dispatch)

const UNATTENDED =
  '夜莺是无人值守工具，运行期间用户不在电脑前。执行过程中若遇到任何二选一提示、确认弹窗、交互式询问，一律优先选择第一个选项（通常是默认/安全项），绝不弹出窗口等待用户操作；无法确定时，选择最保守、不会造成破坏的选项。\n'

// 功能对之外的可选角色对（激进时段最多再开 N-1 个）
const AUX_ROLES = [
  {
    key: 'test',
    label: '测试对',
    scope: '给已存在的功能补单元测试与边界测试（Python 项目用 python3 -m unittest，其他语言用对应工具）；被测试暴露出的真实缺陷做最小修复使其通过；不新增未实现的功能，不 mock 掉核心逻辑以图省事。',
  },
  {
    key: 'docs',
    label: '文档对',
    scope: '补/修注释、docstring、README 与示例；不改代码逻辑；文档与代码不符时以代码为准并修正文档。',
  },
  {
    key: 'review',
    label: '审查对',
    scope: '做一次静态审查（可用 rg/readtags/ctags 等），找真实 bug、未处理的边界、代码坏味与安全隐患，直接小修确认的缺陷；不做大规模重构。',
  },
  {
    key: 'optimize',
    label: '优化对',
    scope: '做一处可验证的性能或结构小优化，说明依据与影响面；当前无明显可优化点时不要硬凑。',
  },
]
const AUX_KEYS = AUX_ROLES.map(function (r) { return r.key })

function mainEvalFile(taskId) { return root + '/queue/eval/' + taskId + '.json' }
function auxEvalFile(taskId, roleKey) { return root + '/queue/eval/' + taskId + '.' + roleKey + '.json' }

// 激进时段本心跳要跑的辅助角色对（功能对预留 1 个）
function auxRunSlice() { return AUX_ROLES.slice(0, Math.max(0, maxPairs - 1)) }

const DECISION_SCHEMA = {
  type: 'object',
  properties: {
    action: { type: 'string', enum: ['open', 'advance', 'idle'] },
    pending_task_id: { type: 'string' },
    running_task_id: { type: 'string' },
    running_goal: { type: 'string' },
    seed_aux: { type: 'boolean' },
    reason: { type: 'string' },
  },
  required: ['action'],
}

const AUX_DEV_SCHEMA = {
  type: 'object',
  properties: {
    found: { type: 'boolean', description: '本轮是否找到并做成了一件职责范围内的事' },
    summary: { type: 'string', description: '改动摘要；found=false 时写一句“为何没有值得做的”' },
    files: { type: 'array', items: { type: 'string' }, description: '本次改动的文件' },
  },
  required: ['found', 'summary'],
}

// ---------- 1. Inspect：决定本轮做什么 ----------
phase('Inspect')
const seedTargets = aggressive ? auxRunSlice() : []
const inspectModeLine = aggressive
  ? '运行模式：aggressive（激进，本轮最多并行 ' + maxPairs + ' 个角色对）\n'
  : '运行模式：conservative（保守，单功能对串行）\n'
const seedCheckLines = seedTargets.length
  ? '若 action=advance：检查该 running 任务下面这些角色 eval 文件是否存在且 verdict=continue：\n' +
    seedTargets.map(function (r) { return '  ' + auxEvalFile('<running_task_id>', r.key) + '（' + r.label + '）' }).join('\n') +
    '\n全部存在且 verdict=continue → seed_aux=false；任一缺失或 verdict 非 continue → seed_aux=true（本轮要先跑分发者）。\n'
  : 'seed_aux=false。\n'

const decision = await agent(
  '你是夜莺(夜间长跑任务系统)的调度读取者。本轮只读，不要改动任何文件。\n' +
  '读取目录 ' + root + ' 下的 queue/tasks.json（任务含 task_id/goal/status 字段，status∈pending|running|done|failed）与 state/system_state.json。\n' +
  inspectModeLine +
  '按优先级判断本轮动作，返回结构化结论：\n' +
  '- 若存在 status=pending 的任务 → action=open，填 pending_task_id\n' +
  '- 否则若存在 status=running 的任务 → action=advance，填 running_task_id、running_goal\n' +
  '- 都无 → action=idle，reason 简述\n' +
  seedCheckLines,
  { phase: 'Inspect', schema: DECISION_SCHEMA }
)

if (!decision) {
  log('决策 agent 未返回，本轮跳过')
  return { action: 'failed', reason: 'inspect 无结果' }
}

if (decision.action === 'idle') {
  log('队列空闲：无 pending/running，本轮仅心跳')
  return { action: 'idle' }
}

// ---------- 2. Act ----------

// ---- open：开新任务，单功能对（无论保守/激进，先引导出第一版）----
if (decision.action === 'open') {
  phase('Act')
  log('开跑新任务 ' + decision.pending_task_id)

  const devResult = await agent(
    '你是夜莺的开发者子代理。现在开跑一个新任务并完成第一轮开发。\n' +
    UNATTENDED +
    toolsLine +
    '项目目录（打磨对象，代码/git/测试都在这里）：' + project + '\n' +
    '夜莺运行目录 ROOT（仅 queue/state/logs，与项目本体隔离）：' + root + '\n' +
    '任务 ID：' + decision.pending_task_id + '\n' +
    '步骤：\n' +
    '1) 读 ' + root + '/queue/tasks.json 里 task_id=' + decision.pending_task_id + ' 的 goal；\n' +
    '2) 进入项目目录；若尚未 git init → 先 git init（已有 git 则沿用，不重复 init，无人值守不询问）；确保 .nightingale 骨架已被 .gitignore 排除、不被 git 跟踪；\n' +
    '3) 围绕 goal 在项目目录做出扎实的第一轮：空项目先搭能跑的最小骨架再补核心；已有代码则以现库为基做增量第一轮；\n' +
    '4) git add -A && git commit（message 概括本轮；新建 git 的首次 commit 可含全部初始代码）；\n' +
    '5) 更新 ' + root + '/queue/tasks.json：把该任务 status 改为 running，并在 iterations 数组中追加一个对象 {"round":1,"note":"<本轮做了什么>"}；\n' +
    '6) 更新 ' + root + '/state/system_state.json：设置 current_task 为 ' + decision.pending_task_id + '，recent_completion 为本轮 commit message 或摘要。\n' +
    '完成后返回：本轮做了什么、产物路径、遗留的明显缺口。',
    { phase: 'Act', label: 'open-dev:' + decision.pending_task_id }
  )
  log('新任务首轮开发完成')

  const evalResult = await agent(
    '你是夜莺的代码评估者（功能对）。请评估刚完成的首轮开发。\n' +
    UNATTENDED +
    '项目目录（打磨对象，代码/git 都在此）：' + project + '\n' +
    '任务 ID：' + decision.pending_task_id + '\n' +
    '步骤：\n' +
    '1) 读项目目录 ' + project + ' 的代码、最近 git log（可用 git log -1 --oneline）、以及 ' + root + '/queue/tasks.json 里该任务的 iterations（当前应为 1 条）；\n' +
    '2) 依次考虑：明显缺失的功能 / 潜在 bug 或未处理的边界 / 需重构的结构 / 体验优化 / 测试·文档·日志缺口；\n' +
    '3) 判断整体：verdict = continue（还有值得做的事）/ done（无）/ failed（卡死无法推进）；\n' +
    '4) 若 continue，给出 actions：最多 3 条、按 priority 升序，每条 {"priority":1|2|3,"task":"...","reason":"..."}；done 时 actions 为空；\n' +
    '5) 写入 ' + root + '/queue/eval/' + decision.pending_task_id + '.json，内容格式：{"task_id":"' + decision.pending_task_id + '","round":1,"verdict":"<...>","summary":"<一句话>","actions":[...]}\n' +
    '6) 更新 ' + root + '/queue/tasks.json：若 verdict=done 则将 status 改为 done，result 设为 summary；若 verdict=failed 则将 status 改为 failed，result 设为 summary；若 continue 保持 running；\n' +
    '7) 更新 ' + root + '/state/system_state.json：recent_completion 设为 summary。\n' +
    '返回：verdict + summary + 建议优先做的一条（如果有）。',
    { phase: 'Act', label: 'open-eval:' + decision.pending_task_id }
  )
  log('新任务首轮评估完成')

  return {
    action: 'open',
    task_id: decision.pending_task_id,
    mode: aggressive ? 'aggressive' : 'conservative',
    pairs_run: 1,
    dev: devResult,
    eval: evalResult,
  }
}

// ---- advance：推进一个 running 任务 ----
phase('Act')
const taskId = decision.running_task_id
log('推进运行中任务 ' + taskId)

const GIT_RACE_GUARD =
  aggressive
    ? '本轮可能与其他角色对并行修改同一仓库：git commit 前先看 git status，只 add 你自己负责的文件；若发现别人刚动过同一文件，不做手工冲突解决，以当前工作区内容为准提交，并把冲突情况写进返回。\n'
    : ''

function advanceDevPrompt(mainExtra) {
  return (
    '你是夜莺的开发者子代理（功能对）。只做下一件最值得做的事，做扎实，不顺手扩 scope。\n' +
    UNATTENDED +
    toolsLine +
    '项目目录（打磨对象，代码/git 都在此）：' + project + '\n' +
    '任务 ID：' + taskId + '\n' +
    GIT_RACE_GUARD +
    '步骤：\n' +
    '1) 读 ' + root + '/queue/eval/' + taskId + '.json，取 actions 里 priority 最小的一条；\n' +
    '2) 实现这条 task，按完成标准自检；\n' +
    (aggressive
      ? '3) git add 你本次实际改动的文件 && git commit（message 概括改动；不要用 git add -A，避免带上并行角色对尚未提交的改动）；\n'
      : '3) git add -A && git commit（message 概括改动）；\n') +
    '4) 更新 ' + root + '/queue/tasks.json：在 iterations 数组末尾追加 {"round":<当前 iterations 长度+1>,"note":"<改动摘要>"}；\n' +
    '5) 更新 ' + root + '/state/system_state.json：recent_completion 为本轮 commit message 或摘要。\n' +
    '返回：是否达到完成标准、改动摘要。'
  )
}

function advanceEvalPrompt() {
  return (
    '你是夜莺的代码评估者（功能对）。请评估刚完成的开发。\n' +
    UNATTENDED +
    '项目目录（打磨对象，代码/git 都在此）：' + project + '\n' +
    '任务 ID：' + taskId + '\n' +
    '步骤：\n' +
    '1) 读项目目录 ' + project + ' 的代码、最近 git log，以及 ' + root + '/queue/tasks.json 里该任务的 iterations（当前长度应为 N）；\n' +
    '2) 依次考虑：明显缺失的功能 / 潜在 bug 或未处理的边界 / 需重构的结构 / 体验优化 / 测试·文档·日志缺口；\n' +
    '3) 判断整体：verdict = continue / done / failed；\n' +
    '4) 若 continue，给出 actions：最多 3 条、按 priority 升序，每条 {"priority":1|2|3,"task":"...","reason":"..."}；done 时 actions 为空；\n' +
    '5) 写入 ' + root + '/queue/eval/' + taskId + '.json，内容格式：{"task_id":"' + taskId + '","round":<当前 iterations 长度>,"verdict":"<...>","summary":"<一句话>","actions":[...]}\n' +
    '6) 更新 ' + root + '/queue/tasks.json：根据 verdict 更新 status 和 result；\n' +
    '7) 更新 ' + root + '/state/system_state.json：recent_completion 设为 summary。\n' +
    '返回：verdict + summary + 建议优先做的一条（如果有）。'
  )
}

// 保守时段：单功能对，与既有行为一致
if (!aggressive) {
  const devResult = await agent(advanceDevPrompt(false), { phase: 'Act', label: 'advance-dev:' + taskId })
  log('开发者完成')
  const evalResult = await agent(advanceEvalPrompt(), { phase: 'Act', label: 'advance-eval:' + taskId })
  log('评估完成')
  return {
    action: 'advance',
    task_id: taskId,
    mode: 'conservative',
    pairs_run: 1,
    dev: devResult,
    eval: evalResult,
  }
}

// 激进时段：需要时先分发，再并行角色对
const auxSlice = auxRunSlice()
const needDispatch = forceDispatch || !!(decision.seed_aux)

let dispatchInfo = null
if (needDispatch && auxSlice.length) {
  phase('Dispatch')
  log('激进时段分发：为 ' + auxSlice.map(function (r) { return r.key }).join(',') + ' seed 初始任务')
  const seedLines = auxSlice.map(function (r) {
    return '  ' + auxEvalFile(taskId, r.key) + '  ← ' + r.label + '，职责：' + r.scope
  }).join('\n')
  dispatchInfo = await agent(
    '你是夜莺的任务分发者。只做只读分析 + 为各角色写初始任务，不要开工实现。\n' +
    UNATTENDED +
    toolsLine +
    '项目目录（打磨对象，代码/git 都在此）：' + project + '\n' +
    '任务 ID：' + taskId + '\n' +
    '步骤：\n' +
    '1) 读项目目录 ' + project + ' 的代码、git log、' + root + '/queue/tasks.json 里该任务 goal，判断当前最该补什么；\n' +
    '2) 为下面每个角色对覆盖式写一个角色 eval 文件（每个都写，找不到值得做的也写 done）：\n' +
    seedLines + '\n' +
    '每个文件内容 JSON：{"task_id":"' + taskId + '","round":1,"verdict":"continue","summary":"分发 seed","actions":[{"priority":1,"task":"<具体到文件/函数的一件活>","reason":"<依据>"}]}\n' +
    '找不到值得做的事 → 写 {"task_id":"' + taskId + '","round":1,"verdict":"done","summary":"<为何暂无值得做>","actions":[]}。\n' +
    '分发原则：每角色只给 1 条 action、priority=1，务必具体可动手；分发者多花一两分钟没关系，不追求快。\n' +
    '返回：每个角色 seed 到的一句话（或 done）。',
    { phase: 'Dispatch', label: 'dispatch:' + taskId }
  )
}

const thunks = []
// 功能对恒跑
thunks.push(function () {
  return (async function () {
    const d = await agent(advanceDevPrompt(true), { phase: 'Act', label: 'advance-dev:' + taskId })
    const e = await agent(advanceEvalPrompt(), { phase: 'Act', label: 'advance-eval:' + taskId })
    return { role: 'functional', dev: d, eval: e }
  })()
})
// 辅助角色对（各自读各自 eval 文件）
auxSlice.forEach(function (role) {
  thunks.push(function () {
    return (async function () {
      const devPrompt =
        '你是夜莺的' + role.label + '开发者（角色对 ' + role.key + '）。只做职责范围内下一件最值得做的事，做扎实，不顺手扩 scope。\n' +
        UNATTENDED +
        toolsLine +
        '项目目录（打磨对象，代码/git 都在此）：' + project + '\n' +
        '任务 ID：' + taskId + '\n' +
        '你的角色 eval 文件：' + auxEvalFile(taskId, role.key) + '\n' +
        '职责：' + role.scope + '\n' +
        '只读写你自己的角色 eval 文件；绝不改 queue/tasks.json、state/system_state.json 或别人的 eval 文件（那是功能对的职责）。\n' +
        GIT_RACE_GUARD +
        '步骤：\n' +
        '1) 读你的角色 eval 文件：verdict=continue → 执行 actions 里 priority 最小的一条；文件不存在或 verdict=done/failed → 在职责范围内自主找一件值得做的事；确实没有 → 返回 {"found":false,...} 并退出；\n' +
        '2) 完成那件事，按完成标准自检（测试/审查类先跑一遍确认）；\n' +
        '3) git add 你本次改动的文件 && git commit（message 以 [' + role.key + '] 开头概括改动）；\n' +
        '返回（结构化 JSON）：{"found":true,"summary":"<改动摘要>","files":[...]} 或 {"found":false,"summary":"<为何没有值得做>"}'
      const d = await agent(devPrompt, { phase: 'Act', label: 'advance-' + role.key + '-dev:' + taskId, schema: AUX_DEV_SCHEMA })
      const devObj = (d && typeof d === 'object') ? d : { found: true, summary: String(d) }
      if (!devObj.found) {
        return { role: role.key, skipped: 'no-work', note: devObj.summary }
      }
      const evalPrompt =
        '你是夜莺的' + role.label + '评估者（角色对 ' + role.key + '）。评估刚完成的' + role.label + '改动，判断该角色是否还有值得做的事。\n' +
        UNATTENDED +
        '项目目录（打磨对象，代码/git 都在此）：' + project + '\n' +
        '任务 ID：' + taskId + '\n' +
        '角色 eval 文件：' + auxEvalFile(taskId, role.key) + '\n' +
        '职责范围：' + role.scope + '\n' +
        '步骤：\n' +
        '1) 读项目目录 ' + project + ' 的代码、git log 最近几条、以及你的角色 eval 文件里现有的 round；\n' +
        '2) 围绕刚才的开发改动，按本角色职责评估：还有值得做的 → verdict=continue 并给出最多 3 条 actions（priority 升序）；没有 → verdict=done，actions=[]；推进不了 → verdict=failed；\n' +
        '3) 覆盖式写回你的角色 eval 文件：{"task_id":"' + taskId + '","round":<现有 round+1>,"verdict":"<...>","summary":"<一句话>","actions":[...]}\n' +
        '只写你自己的角色 eval 文件，绝不改 tasks.json / system_state.json / 别人 eval 文件。\n' +
        '返回：verdict + summary。'
      const e = await agent(evalPrompt, { phase: 'Act', label: 'advance-' + role.key + '-eval:' + taskId })
      return { role: role.key, dev: devObj, eval: e }
    })()
  })
})

const pairResults = await parallel(thunks)

const ranPairs = 1 + pairResults.filter(function (x) {
  return x && x.role !== 'functional' && !(x.skipped === 'no-work')
}).length

log('激进轮次完成：功能对 + ' + (ranPairs - 1) + ' 个辅助角色对')

return {
  action: 'advance',
  task_id: taskId,
  mode: 'aggressive',
  pairs_run: ranPairs,
  dispatch: dispatchInfo || null,
  roles: pairResults,
}
