#!/usr/bin/env bash
# =============================================================================
# mob.sh — 极简版设备配置脚本（执行器）
#
# 定位：一行一条设置，设下去、校验一下、报结果。没有花活。
# 本脚本是设备设置的【期望值权威来源】，要改值就改这里。
#
# 用法：
#   ./script/mob.sh          设置 + 校验（默认）
#   ./script/mob.sh check    只比对，不改动
# =============================================================================
#
# ---- 原始 adb 命令速查（想手工执行/抄写，直接复制下面任意一行）---------------
#
#   adb shell settings put global window_animation_scale      0
#   adb shell settings put global transition_animation_scale  0
#   adb shell settings put global animator_duration_scale     0
#   adb shell settings put system pointer_location            0
#   adb shell settings put system show_touches                0
#   adb shell settings put global stay_on_while_plugged_in    7
#   adb shell settings put system screen_off_timeout          600000
#
#   查询当前值：把 put 换成 get，例如
#   adb shell settings get global window_animation_scale
#
# =============================================================================

set -uo pipefail   # 注意：故意不用 -e。某项失败不该中断整个脚本

MODE="${1:-apply}"
pass=0
fixed=0
fail=0

# -----------------------------------------------------------------------------
# 唯一的函数：读当前值 → 与期望比对 → 不一致就写 → 再读一次确认
# -----------------------------------------------------------------------------
set_setting() {
  local scope="$1"   # global / system / secure
  local key="$2"
  local want="$3"
  local label="$4"
  local now

  now=$(adb shell settings get "$scope" "$key" 2>/dev/null | tr -d '\r')

  if [ "$now" = "$want" ]; then
    printf '  [OK]    %-16s %s\n' "$label" "$now"
    pass=$((pass + 1))
    return 0
  fi

  if [ "$MODE" = "check" ]; then
    printf '  [DIFF]  %-16s %s -> 应为 %s\n' "$label" "$now" "$want"
    fixed=$((fixed + 1))
    return 0
  fi

  adb shell settings put "$scope" "$key" "$want" >/dev/null 2>&1
  now=$(adb shell settings get "$scope" "$key" 2>/dev/null | tr -d '\r')

  if [ "$now" = "$want" ]; then
    printf '  [SET]   %-16s -> %s\n' "$label" "$now"
    fixed=$((fixed + 1))
  else
    printf '  [FAIL]  %-16s 现值 %s（期望 %s）\n' "$label" "$now" "$want"
    fail=$((fail + 1))
  fi
}

# -----------------------------------------------------------------------------
# 前置检查
# -----------------------------------------------------------------------------
if ! command -v adb >/dev/null 2>&1; then
  echo "错误：未找到 adb（sudo apt install adb）" >&2
  exit 2
fi

serial=$(adb devices | awk 'NR>1 && $2=="device" {print $1}')
if [ -z "$serial" ]; then
  echo "错误：没有在线设备，检查 USB 连接与 USB 调试授权" >&2
  exit 2
fi

if [ "$MODE" = "check" ]; then
  echo "设备: $serial"
  echo "模式: check（只比对，不修改）"
else
  echo "设备: $serial"
  echo "模式: apply（设置 + 校验）"
fi
echo

# -----------------------------------------------------------------------------
# 设置项：一行一条
# -----------------------------------------------------------------------------
set_setting global window_animation_scale      0.0      "窗口动画缩放"
set_setting global transition_animation_scale  0.0      "过渡动画缩放"
set_setting global animator_duration_scale     0.0      "动画程序时长缩放"
set_setting system pointer_location            0        "指针位置浮层"
set_setting system show_touches                0        "显示触摸操作"
set_setting global stay_on_while_plugged_in    7        "充电时保持唤醒"
set_setting system screen_off_timeout          600000   "屏幕超时(ms)"
set_setting global hw_system_update_auto_download 0     "系统更新自动下载"
set_setting secure adb_install_need_confirm    0        "监控ADB安装应用"
set_setting global allow_charging_adb          1        "仅充电模式允许ADB"

# -----------------------------------------------------------------------------
# 汇总
# -----------------------------------------------------------------------------
echo
if [ "$MODE" = "check" ]; then
  echo "汇总: 达标 $pass 项 / 差异 $fixed 项 / 失败 $fail 项"
  [ "$fixed" -eq 0 ] && echo "结论: 全部达标" || echo "结论: 有差异，运行 ./script/mob.sh 修正"
else
  echo "汇总: 达标 $pass 项 / 修正 $fixed 项 / 失败 $fail 项"
  [ "$fail" -eq 0 ] && echo "结论: 全部到位"
fi

# -----------------------------------------------------------------------------
# 只读项（adb 改不了，仅打印实际值）
# -----------------------------------------------------------------------------
echo
echo '【只读项】'
echo "  日志缓冲区: $(adb shell logcat -g 2>/dev/null | awk '/^main:/ {print $5" "$6}')"
echo "  USB 配置:   $(adb shell getprop persist.sys.usb.config 2>/dev/null | tr -d '\r')"

exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
