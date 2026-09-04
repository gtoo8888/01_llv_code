#!/usr/bin/env python3
# schedule_mode.py —— 夜莺时段判定（确定性，无 LLM）
#
# 作用：按 state/config.json 的 schedule 与当前时间，判驱动方该用哪种运行模式。
#   夜莺的时段策略只由“驱动方”（会话内定时唤起的会话 / loop.sh 唤起的 agent）判定，
#   workflow 脚本内部不判时间——本脚本就是这份判定的确定性实现。
#
# 用法：python3 scripts/schedule_mode.py ROOT [可选 ISO 时间用于测试]
#        ROOT = <项目目录>/.nightingale（读其 state/config.json 与 state/system_state.json）
# 输出：一行 JSON：{"mode":..., "pairs":<int>, "dispatch":<bool>, "now":"<ISO>",
#                   "tools":"<status=ok 的工具名，空格分隔>",
#                   "args":{"root":ROOT,"mode":...,"pairs":...,"dispatch":...,"tools":...}}
#        args 段可直接作为 Workflow({scriptPath, args}) 的 args 原样传入，驱动方不用手拼。
#
# 判定规则：
#   - 工作日白天 [night_end, night_start) 内（如 08:30–21:30）→ conservative（保守，1 功能对）
#   - 其余（工作日夜间 21:30–次日 08:30、周末窗口 Friday 21:30 → Monday 08:30 全覆盖）→ aggressive
#   - 周几：Monday=0 … Sunday=6；窗口按 (星期, HH:MM) 解析，跨周自动环绕
#   - dispatch：刚切入 aggressive 的那一轮为 true（比较 system_state.mode 的上一值）
#   - config.json 无 schedule 字段 → 恒 conservative（即既有串行行为），不判时间
#   - timezone 缺省为机器本地时间；配了 schedule.timezone 则用该时区

import json
import sys
from datetime import datetime, timedelta

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DEFAULTS = {
    "night_start": "21:30",
    "night_end": "08:30",
    "weekend_start": "Friday 21:30",
    "weekend_end": "Monday 08:30",
    "conservative_max_pairs": 1,
    "aggressive_max_pairs": 5,
}


def parse_hhmm(text):
    """'21:30' -> 分钟数（一天内 0..1439）"""
    hh, mm = text.strip().split(":")
    return int(hh) * 60 + int(mm)


def parse_weekday_time(text):
    """'Friday 21:30' -> (weekday_index 0..6, 分钟数 0..1439)"""
    parts = text.strip().rsplit(" ", 1)
    day = WEEKDAYS.index(parts[0].strip())
    return day, parse_hhmm(parts[1])


def now_datetime(tz_name):
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_name)) if tz_name else datetime.now().astimezone()
    except Exception:
        return datetime.now().astimezone()


def inside_window(day, minute, start_day, start_min, end_day, end_min):
    """判断 (day, minute) 是否落在 [start_day@start_min, end_day@end_min) 内，跨周自动环绕。"""
    if start_day == end_day:
        # 同一天内的窗口：可能不过夜（start_min <= end_min）或过夜（start_min > end_min）
        if start_min <= end_min:
            return day == start_day and start_min <= minute < end_min
        return day == start_day and (minute >= start_min or minute < end_min)
    if start_day < end_day:
        # 同周内，如 Tuesday → Friday
        if day < start_day or day > end_day:
            return False
        if day == start_day:
            return minute >= start_min
        if day == end_day:
            return minute < end_min
        return True  # 中间整天都在窗口内
    # 跨周，如 Friday → Monday：start_day 之后 / end_day 之前（含回绕）都为整日窗口
    if start_day < end_day:  # 不可达，仅防呆
        return False
    if day == start_day:
        return minute >= start_min
    if day == end_day:
        return minute < end_min
    if day > start_day or day < end_day:  # 周六周日即 start_day 之后、end_day 之前
        return True
    return False


def ok_tools(root):
    """读 state/env_check.json，返回 status=ok 的工具名（排除 im_* 渠道项），空格分隔。

    供驱动方免读 env_check：tools 已并入 decide 的输出与 args 段。
    env_check 缺失/损坏 → 返回空串，workflow 内开发者自读 env_check 兜底。
    """
    names = []
    try:
        with open(root + "/state/env_check.json", encoding="utf-8") as f:
            env = json.load(f)
        for r in env.get("results", []):
            name = r.get("name", "")
            if name and not name.startswith("im_") and r.get("status") == "ok":
                names.append(name)
    except Exception:
        pass
    return " ".join(names)


def decide(root, now_iso=None):
    config = {}
    try:
        with open(root + "/state/config.json", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        pass  # config 缺失/损坏 → 走默认（无 schedule 即恒保守）

    tools = ok_tools(root)

    def build(mode, pairs, dispatch, now):
        # args 段 = 可直接作 Workflow 的 args 传入（root/mode/pairs/dispatch/tools 齐全）。
        return {
            "mode": mode,
            "pairs": pairs,
            "dispatch": dispatch,
            "now": now.isoformat(timespec="seconds"),
            "tools": tools,
            "args": {
                "root": root,
                "mode": mode,
                "pairs": pairs,
                "dispatch": dispatch,
                "tools": tools,
            },
        }

    sched = config.get("schedule")
    if not sched:
        now = datetime.now().astimezone()
        if now_iso:
            try:
                now = datetime.fromisoformat(now_iso)
            except Exception:
                pass
        return build("conservative", DEFAULTS["conservative_max_pairs"], False, now)

    # 上一轮 mode：取 system_state.mode，缺失视为 'conservative'
    prev_mode = "conservative"
    try:
        with open(root + "/state/system_state.json", encoding="utf-8") as f:
            st = json.load(f)
        prev_mode = st.get("mode", "conservative")
    except Exception:
        pass

    night_start = parse_hhmm(str(sched.get("night_start", DEFAULTS["night_start"])))
    night_end = parse_hhmm(str(sched.get("night_end", DEFAULTS["night_end"])))
    ws_day, ws_min = parse_weekday_time(str(sched.get("weekend_start", DEFAULTS["weekend_start"])))
    we_day, we_min = parse_weekday_time(str(sched.get("weekend_end", DEFAULTS["weekend_end"])))

    now = now_datetime(sched.get("timezone"))
    if now_iso:
        try:
            now = datetime.fromisoformat(now_iso)
        except Exception:
            pass

    day = now.weekday()  # 0=Monday
    minute = now.hour * 60 + now.minute

    # 周末窗口覆盖（跨周自动处理，如 Friday 21:30 → Monday 08:30）
    weekend_active = inside_window(day, minute, ws_day, ws_min, we_day, we_min)

    # 工作日夜间：Mon..Fri(0..4)，minute >= night_start 或 minute < night_end（跨零点）
    weekday_night_active = (
        day <= 4 and (minute >= night_start or minute < night_end)
    )

    mode = "aggressive" if (weekend_active or weekday_night_active) else "conservative"
    pairs = int(
        sched.get(
            "aggressive_max_pairs" if mode == "aggressive" else "conservative_max_pairs",
            DEFAULTS["aggressive_max_pairs" if mode == "aggressive" else "conservative_max_pairs"],
        )
    )
    dispatch = mode == "aggressive" and prev_mode != "aggressive"

    return build(mode, pairs, dispatch, now)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("用法: python3 schedule_mode.py ROOT [可选 ISO 时间]\n")
        sys.exit(2)
    root = sys.argv[1].rstrip("/")
    iso = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(decide(root, iso), ensure_ascii=False))
