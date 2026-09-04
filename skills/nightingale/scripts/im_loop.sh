#!/usr/bin/env bash
# nightingale —— IM 通知循环（独立进程）
#
# 作用：只负责"读状态 → 拼心跳 → 发 IM → 更新状态 → 睡"。不调用 LLM。
# 核心：IM 是尽力而为的通知，发送失败/超时都不影响主 Loop。
# 用法：./scripts/im_loop.sh <项目目录>
# 说明：传入打磨对象 <项目目录>；ROOT = <项目目录>/.nightingale（读其 state/ 拼心跳）。
# 必定单独启动，不由主 Loop 拉起。

set -euo pipefail

PROJECT="${1:?用法: im_loop.sh <项目目录>}"
ROOT="$PROJECT/.nightingale"
mkdir -p "$ROOT/logs" "$ROOT/state"

# 读取配置中的 im.interval_sec（默认 900）
read_interval() {
  python3 -c "
import json
try:
    with open('$ROOT/state/config.json') as f:
        c = json.load(f)
    im = c.get('im') or {}
    print(im.get('interval_sec', 900))
except Exception:
    print(900)
"
}

INTERVAL=$(read_interval)

while true; do
  python3 - "$ROOT" <<'PYEOF'
import sys, json, os, time, urllib.request, urllib.error

root = sys.argv[1]

def read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def log(msg):
    log_path = os.path.join(root, "logs", "nightingale.log")
    with open(log_path, "a") as f:
        f.write(f"[{time.strftime('%F %T')}] {msg}\n")

def send_webhook(url, text, timeout=3):
    """向 webhook 发送纯文本消息，根据 URL 判断平台"""
    if "feishu" in url:
        payload = json.dumps({"msg_type": "text", "content": {"text": text}}).encode()
    elif "dingtalk" in url:
        payload = json.dumps({"msgtype": "text", "text": {"content": text}}).encode()
    else:
        # 企业微信 / 其他：使用通用格式
        payload = json.dumps({"msgtype": "text", "text": {"content": text}}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.status

# ---------- 主逻辑 ----------

config = read_json(os.path.join(root, "state", "config.json"), {})
im_cfg = config.get("im") or {}

# IM 总开关
if not im_cfg.get("enabled", True):
    state = read_json(os.path.join(root, "state", "system_state.json"), {})
    state["im_last_sent"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state["im_last_status"] = "skipped"
    write_json(os.path.join(root, "state", "system_state.json"), state)
    log("IM Loop: im.enabled=false，跳过本轮")
    sys.exit(0)

channels = im_cfg.get("channels") or []
enabled_channels = [
    c for c in channels
    if c.get("enabled", False) and c.get("webhook_url")
]

if not enabled_channels:
    state = read_json(os.path.join(root, "state", "system_state.json"), {})
    state["im_last_sent"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state["im_last_status"] = "skipped"
    write_json(os.path.join(root, "state", "system_state.json"), state)
    log("IM Loop: 未配置可用渠道，跳过")
    sys.exit(0)

# 读自检结果，找 ok 的 IM 渠道
env_check = read_json(os.path.join(root, "state", "env_check.json"), {})
results = env_check.get("results") or []
ok_im_names = set()
for r in results:
    name = r.get("name", "")
    if name.startswith("im_") and r.get("status") == "ok":
        ok_im_names.add(name)

# 拼心跳消息
state = read_json(os.path.join(root, "state", "system_state.json"), {})

current_task = state.get("current_task") or "无"
recent_completion = state.get("recent_completion") or "无"
error_count = state.get("error_count", 0)
delta = state.get("last_heartbeat_delta_sec")
last_heartbeat = (f"{int(delta)} 秒前" if isinstance(delta, (int, float))
                  else (state.get("last_heartbeat") or "未知"))
status = state.get("status", "idle")

heartbeat_msg = (
    "【夜莺心跳】\n"
    f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    f"系统状态：{status}\n"
    f"当前任务：{current_task}\n"
    f"最近完成：{recent_completion}\n"
    f"本轮错误：{error_count if error_count > 0 else '无'}\n"
    f"最后心跳：{last_heartbeat}"
)

# 串行发送到 ok 的渠道
sent_ok = False
for ch in enabled_channels:
    ch_name = ch.get("name", "")
    im_check_name = f"im_{ch_name}"
    if im_check_name not in ok_im_names:
        log(f"IM Loop: 渠道 {ch_name} 自检失败，跳过")
        continue
    url = ch.get("webhook_url", "")
    if not url:
        continue
    try:
        status_code = send_webhook(url, heartbeat_msg)
        if status_code < 400:
            sent_ok = True
            log(f"IM Loop: 渠道 {ch_name} 发送成功")
        else:
            log(f"IM Loop: 渠道 {ch_name} 发送失败 HTTP {status_code}")
    except Exception as e:
        log(f"IM Loop: 渠道 {ch_name} 发送异常: {e}")

# 更新状态
state = read_json(os.path.join(root, "state", "system_state.json"), {})
state["im_last_sent"] = time.strftime("%Y-%m-%dT%H:%M:%S")
if sent_ok:
    state["im_last_status"] = "ok"
else:
    state["im_last_status"] = "degraded"
    log(f"IM Loop: 所有渠道失败，降级输出: {heartbeat_msg}")

write_json(os.path.join(root, "state", "system_state.json"), state)
PYEOF

  sleep "$INTERVAL"
done
