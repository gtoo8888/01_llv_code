#!/usr/bin/env python3
"""shot.py — 截图流水线（一次调用拿到判断一个页面所需的全部上下文）

用法:
    ./script/shot.py                 # 截图 + 缩放 0.6（原图删除）
    ./script/shot.py --scale 0.5     # 自定义缩放
    ./script/shot.py --ui            # 额外带上界面控件表（文本 + 坐标）

输出: stdout 只有一段 JSON，所有警告/错误走 stderr。
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOT_DIR = ROOT / "out" / "shots"
LAST_HASH_FILE = SHOT_DIR / ".last_hash"
DEFAULT_SCALE = 0.6
UI_MAX_NODES = 120


# ---------------------------------------------------------------- adb

def adb(*args, timeout=30):
    """执行 adb，返回 (code, stdout, stderr)。"""
    try:
        p = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError("adb not found")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"adb timeout: {' '.join(args)}")
    return p.returncode, p.stdout, p.stderr


def sh(cmd, timeout=30):
    """在设备上执行 shell 命令，返回 stdout（忽略 stderr）。"""
    code, out, err = adb("shell", cmd, timeout=timeout)
    if code != 0 and not out:
        raise RuntimeError(f"shell failed: {cmd}")
    return out


def device_ready():
    code, out, _ = adb("devices")
    devices = {}
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            devices[parts[0]] = parts[1]
    if not devices:
        raise RuntimeError("no device")
    if len(devices) > 1:
        raise RuntimeError(f"multiple devices: {', '.join(devices)}")
    serial, state = next(iter(devices.items()))
    if state != "device":
        raise RuntimeError(f"device state: {state}")
    return serial


# ---------------------------------------------------------------- 采集

def gather_live():
    """一次拿到前台页面、屏幕参数、唤醒状态、电量。"""
    info = {}

    # 前台页面 + 锁屏状态（一次 dumpsys window）
    out = sh("dumpsys window | grep -E -m2 'mCurrentFocus|isKeyguardShowing'")
    m = re.search(r"mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^}]+)\}", out)
    if m:
        pkg_act = m.group(1)
        if "/" in pkg_act:
            info["package"], info["activity"] = pkg_act.split("/", 1)
        else:
            info["package"], info["activity"] = pkg_act, ""
    m = re.search(r"isKeyguardShowing=(\w+)", out)
    info["_locked"] = (m.group(1) == "true") if m else None

    # 屏幕分辨率 / dpi / 唤醒状态（一次 shell）
    out = sh("wm size; wm density; dumpsys power | grep -m1 mWakefulness")
    m = re.search(r"Physical size:\s*(\d+)x(\d+)", out)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    m = re.search(r"Physical density:\s*(\d+)", out)
    density = int(m.group(1)) if m else None
    m = re.search(r"mWakefulness=(\w+)", out)
    wake = m.group(1) if m else None
    info["_screen"] = {"w": w, "h": h, "density": density, "wake": wake}

    # 电量
    out = sh("dumpsys battery")
    bat = {}
    m = re.search(r"level:\s*(\d+)", out)
    if m:
        bat["level"] = int(m.group(1))
    bat["charging"] = "USB powered: true" in out or "AC powered: true" in out
    m = re.search(r"temperature:\s*(\d+)", out)
    if m:
        bat["temp_c"] = round(int(m.group(1)) / 10.0, 1)
    info["_battery"] = bat
    return info


def capture(path):
    """截图到本地文件（exec-out 保证二进制不被破坏）。"""
    with open(path, "wb") as f:
        p = subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f,
                           stderr=subprocess.PIPE, timeout=30)
    if p.returncode != 0 or not path.exists() or path.stat().st_size == 0:
        if path.exists():
            path.unlink()
        raise RuntimeError("screencap failed")


def image_dims(path):
    """用 ffmpeg/ffprobe 读尺寸；失败返回 None。"""
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(path)],
            capture_output=True, text=True, timeout=15)
        m = re.match(r"(\d+)x(\d+)", p.stdout.strip())
        return f"{m.group(1)}x{m.group(2)}" if m else None
    except Exception:
        return None


def brightness(path):
    """平均亮度（0-255），用于判断画面是否接近全黑。"""
    try:
        p = subprocess.run(
            ["ffmpeg", "-i", str(path), "-vf",
             "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
            capture_output=True, text=True, timeout=30)
        m = re.search(r"signalstats\.YAVG=([0-9.]+)", p.stderr)
        return round(float(m.group(1)), 2) if m else None
    except Exception:
        return None


def scale_image(src, dst, factor):
    try:
        p = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
             "-vf", f"scale=iw*{factor}:-1", str(dst)],
            capture_output=True, text=True, timeout=30)
        return p.returncode == 0 and dst.exists() and dst.stat().st_size > 0
    except Exception:
        return False


def sha256_short(path, n=12):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def visual_fingerprint(path, n=12):
    """内容指纹：裁掉顶部状态栏（时钟每秒变）与底部导航栏，降采样成灰度后再哈希，
    避免抗锯齿噪声造成"每次都变了"的误判。"""
    try:
        p = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-vf",
             "crop=iw:ih*0.88:0:ih*0.06,scale=iw*0.5:-1,format=gray",
             "-f", "rawvideo", "-"],
            capture_output=True, timeout=30)
        if p.returncode != 0 or not p.stdout:
            return None
        return hashlib.sha256(p.stdout).hexdigest()[:n]
    except Exception:
        return None


def gather_ui():
    """dump 界面并过滤成 [{'t': 文本, 'b': [x1,y1,x2,y2]}, ...]。"""
    try:
        sh("uiautomator dump --compressed /sdcard/_shot_ui.xml >/dev/null 2>&1", timeout=30)
        code, out, _ = adb("exec-out", "cat", "/sdcard/_shot_ui.xml", timeout=30)
    except Exception:
        return None
    if code != 0 or "<hierarchy" not in out:
        return None

    items, seen = [], set()
    for m in re.finditer(r"<node\b[^>]*>", out):
        tag = m.group(0)
        t = re.search(r'text="([^"]*)"', tag)
        d = re.search(r'content-desc="([^"]*)"', tag)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        label = ((t.group(1) if t else "") or (d.group(1) if d else "")).strip()
        if not label or not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        if x2 <= x1 or y2 <= y1:
            continue  # 屏幕外的假坐标
        key = (label, (x1, y1, x2, y2))
        if key in seen:
            continue
        seen.add(key)
        items.append({"t": label, "b": [x1, y1, x2, y2]})
        if len(items) >= UI_MAX_NODES:
            break
    return items


# ---------------------------------------------------------------- 主流程

def run(args):
    SHOT_DIR.mkdir(parents=True, exist_ok=True)

    serial = device_ready()
    live = gather_live()

    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    pkg = live.get("package") or "unknown"
    safe_pkg = re.sub(r"[^a-zA-Z0-9._-]", "_", pkg)
    original = SHOT_DIR / f"{ts}_{safe_pkg}.png"

    capture(original)

    result = {
        "v": 1,
        "ok": True,
        "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "device": serial,
        "package": live.get("package"),
        "activity": live.get("activity"),
        "scale": args.scale,
    }

    final = original
    if args.scale != 1:
        scaled = SHOT_DIR / f"{ts}_{safe_pkg}_tmp.png"
        if scale_image(original, scaled, args.scale):
            dims = image_dims(scaled) or "?"
            final = SHOT_DIR / f"{ts}_{safe_pkg}_{dims.replace('x', 'x')}.png"
            scaled.rename(final)
            original.unlink()          # 原图永远删除
        else:
            result["scale_error"] = "ffmpeg scale failed; kept original"

    result["file"] = str(final.relative_to(ROOT))
    result["dims"] = image_dims(final)
    result["bytes"] = final.stat().st_size
    result["brightness"] = brightness(final)

    digest = visual_fingerprint(final) or sha256_short(final)
    prev = LAST_HASH_FILE.read_text().strip() if LAST_HASH_FILE.exists() else None
    result["fingerprint"] = digest
    result["changed"] = None if not prev else (prev != digest)
    LAST_HASH_FILE.write_text(digest)

    # 屏幕参数：横竖屏由截图尺寸推断
    screen = dict(live.get("_screen") or {})
    if result["dims"] and "x" in result["dims"]:
        iw, ih = (int(v) for v in result["dims"].split("x"))
        screen["orientation"] = "portrait" if ih >= iw else "landscape"
    screen["locked"] = live.get("_locked")
    result["screen"] = {k: v for k, v in screen.items() if v is not None}

    bat = live.get("_battery") or {}
    if bat:
        result["battery"] = bat

    if args.ui:
        ui = gather_ui()
        result["ui"] = ui

    return result


def main():
    ap = argparse.ArgumentParser(description="截图流水线：截图 + 缩放 + 上下文信息 → JSON")
    ap.add_argument("--scale", type=float, default=DEFAULT_SCALE,
                    help=f"缩放比例，默认 {DEFAULT_SCALE}；1 表示不缩放")
    ap.add_argument("--ui", action="store_true", help="额外输出界面控件表（文本 + 坐标）")
    args = ap.parse_args()

    if not (0 < args.scale <= 1):
        print(json.dumps({"v": 1, "ok": False, "error": "scale must be in (0,1]"},
                         ensure_ascii=False, separators=(",", ":")))
        return 2

    try:
        print(json.dumps(run(args), ensure_ascii=False, separators=(",", ":")))
        return 0
    except RuntimeError as exc:
        print(json.dumps({"v": 1, "ok": False, "error": str(exc)},
                         ensure_ascii=False, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
