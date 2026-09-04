#!/usr/bin/env bash
# nightingale —— 心跳脚本（确定性部分，不含 LLM）
#
# 作用：只负责“醒→判时段→检查→（按需）唤起 agent→记心跳→睡”。真正的“干活”由被唤起的
#       agent 完成——这正是夜莺的第一性原则：把“活着”(此循环)和“干活”(执行单元)分开。
#
# 用法：./scripts/loop.sh <项目目录> [间隔秒数，默认 900]
# 说明：传入打磨对象 <项目目录>；ROOT = <项目目录>/.nightingale（运行骨架，queue/state/logs 在此），与项目本体隔离。
#
# 接线说明：
#   - 每轮醒来先判时段：调用 scripts/schedule_mode.py 得 mode/pairs/dispatch，
#     以环境变量 NIGHTINGALE_MODE / NIGHTINGALE_PAIRS / NIGHTINGALE_DISPATCH 传给被唤起的 agent。
#   - 推荐通过环境变量 NIGHTINGALE_AGENT_CMD 指定唤起命令，例如：
#       export NIGHTINGALE_AGENT_CMD="claude -p --allowedTools 'Read,Write,Bash,Edit' \"按 nightingale 流程处理任务队列 <ROOT>，做完一轮即退出；把 \$NIGHTINGALE_MODE/\$NIGHTINGALE_PAIRS/\$NIGHTINGALE_DISPATCH 并入 Workflow 的 args（mode/pairs/dispatch），返回后同步 state/system_state.json 的 mode/active_pairs\""
#   - 若未设置 NIGHTINGALE_AGENT_CMD，则默认使用占位提示，不会真正干活。
#   - 在支持 Workflow 工具的平台，也可不设 AGENT_CMD，改由外部调度器每轮直接触发
#     Workflow({scriptPath:'nightingale_cycle.js', args:{root,mode,pairs,dispatch,tools}})，本脚本仅保活与记心跳。
set -euo pipefail

PROJECT="${1:?用法: loop.sh <项目目录> [间隔秒数]}"
ROOT="$PROJECT/.nightingale"
INTERVAL="${2:-900}"

QUEUE="$ROOT/queue/tasks.json"
LOGS="$ROOT/logs"
STATE="$ROOT/state"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$LOGS" "$STATE"

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" >> "$LOGS/nightingale.log"; }

# 时段判定：schedule_mode.py 不可用（无 python3 / 异常）时回退保守（1 功能对，不分发）。
declare_schedule() {
  local out
  if ! command -v python3 >/dev/null 2>&1; then
    NIGHTINGALE_MODE=conservative; NIGHTINGALE_PAIRS=1; NIGHTINGALE_DISPATCH=false
    return
  fi
  if ! out="$(python3 "$SCRIPT_DIR/schedule_mode.py" "$ROOT" 2>/dev/null)"; then
    NIGHTINGALE_MODE=conservative; NIGHTINGALE_PAIRS=1; NIGHTINGALE_DISPATCH=false
    return
  fi
  NIGHTINGALE_MODE="$(printf '%s' "$out" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("mode","conservative"))' 2>/dev/null || echo conservative)"
  NIGHTINGALE_PAIRS="$(printf '%s' "$out" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("pairs",1))' 2>/dev/null || echo 1)"
  NIGHTINGALE_DISPATCH="$(printf '%s' "$out" | python3 -c 'import sys,json;print("true" if json.load(sys.stdin).get("dispatch") else "false")' 2>/dev/null || echo false)"
}

agent_entry() {
  # 每轮心跳时，如果队列有 pending/running 任务，则唤起一次 agent 干活。
  if [ -n "${NIGHTINGALE_AGENT_CMD:-}" ]; then
    log "agent_entry: 执行 NIGHTINGALE_AGENT_CMD (mode=$NIGHTINGALE_MODE pairs=$NIGHTINGALE_PAIRS dispatch=$NIGHTINGALE_DISPATCH)"
    local cmd="${NIGHTINGALE_AGENT_CMD//<ROOT>/$ROOT}"
    eval "$cmd" >> "$LOGS/nightingale.log" 2>&1
  else
    log "agent_entry: 未设置 NIGHTINGALE_AGENT_CMD，跳过本轮派发（占位）"
  fi
}

while true; do
  log "heartbeat: 醒来"
  declare_schedule
  export NIGHTINGALE_MODE NIGHTINGALE_PAIRS NIGHTINGALE_DISPATCH
  log "schedule: mode=$NIGHTINGALE_MODE pairs=$NIGHTINGALE_PAIRS dispatch=$NIGHTINGALE_DISPATCH"
  if [ -f "$QUEUE" ] && grep -qE '"(pending|running)"' "$QUEUE"; then
    agent_entry
  else
    log "heartbeat: 队列无 pending/running 任务，跳过派发"
  fi
  date '+%F %T' > "$STATE/last_heartbeat"
  log "heartbeat: 睡 ${INTERVAL}s"
  sleep "$INTERVAL"
done
