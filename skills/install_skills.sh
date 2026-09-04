#!/usr/bin/env bash
#
# install_skills.sh — 把 skill 库中的 skill 自动拷贝/安装到目标项目的 .claude/skills/
#
# 约定：skill 库 = 本脚本所在目录。库中每个"含 SKILL.md 的子目录"视为一个 skill，
#       整目录拷贝（会带上 references/、脚本等附属文件）。
# 目标：默认 = 本脚本所属工作区根的 .claude/skills（即 /data_sdb/openclaw/KnowledgeWorkspace/.claude/skills），可用 -p 覆盖。
#
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_LIB="$SCRIPT_DIR"

# ---- 默认目标项目：本脚本所属的工作区根 ----
# skills 库固定位于 <工作区>/02_llv_generated/01_llv_code/skills，
# 脚本位置向上三级即工作区根；不随当前运行目录变化。
WORKSPACE_ROOT="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"
PROJECT="$WORKSPACE_ROOT"

LIST_ONLY=0
DRY_RUN=0
NAMES=()

usage() {
  cat <<'EOF'
用法: install_skills.sh [选项] [skill名...]

把 skill 库（本脚本所在目录）中含 SKILL.md 的子目录作为一个 skill，
整目录安装到 目标项目/.claude/skills/<名>/。

参数:
  skill名...   只安装指定的 skill（可多个）；缺省 = 全部
  -p <目录>    目标项目根目录（默认 = 本脚本所属工作区根，安装到其 .claude/skills）
  -l           只列出可用 skill，不安装
  -n           干跑：只打印将执行的动作，不真正改动
  -h           显示帮助
EOF
}

while getopts ":p:lhn" opt; do
  case "$opt" in
    p) PROJECT="$OPTARG" ;;
    l) LIST_ONLY=1 ;;
    n) DRY_RUN=1 ;;
    h) usage; exit 0 ;;
    \?) echo "未知选项: -$OPTARG" >&2; usage; exit 1 ;;
  esac
done
shift $((OPTIND - 1))
NAMES=("$@")

DEST="$PROJECT/.claude/skills"

echo "skill 库 : $SKILLS_LIB"
echo "目标目录 : $DEST"
echo

# 列出库中所有可用 skill（含 SKILL.md 的子目录名）
list_skills() {
  local d name
  for d in "$SKILLS_LIB"/*/; do
    [ -d "$d" ] || continue
    [ -f "$d/SKILL.md" ] || continue
    name="$(basename "$d")"
    printf '%s\n' "$name"
  done
}

available=()
mapfile -t available < <(list_skills)

if [ "${#available[@]}" -eq 0 ]; then
  echo "错误：skill 库中没有任何含 SKILL.md 的子目录。" >&2
  exit 1
fi

if [ "$LIST_ONLY" -eq 1 ]; then
  echo "可用 skills:"
  printf '  %s\n' "${available[@]}"
  exit 0
fi

# 决定要安装哪些
if [ "${#NAMES[@]}" -gt 0 ]; then
  install=()
  for want in "${NAMES[@]}"; do
    if printf '%s\n' "${available[@]}" | grep -qx "$want"; then
      install+=("$want")
    else
      echo "跳过: $want 不是可用 skill（用 -l 查看）" >&2
    fi
  done
  if [ "${#install[@]}" -eq 0 ]; then
    echo "没有可安装的 skill。" >&2
    exit 1
  fi
else
  install=("${available[@]}")
fi

mkdir -p "$DEST"

for name in "${install[@]}"; do
  echo "安装 skill: $name"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  (dry-run) rm -rf $DEST/$name"
    echo "  (dry-run) cp -R $SKILLS_LIB/$name $DEST/"
    continue
  fi
  # 先清空目标里旧的同名目录，避免残留过期文件（替换式安装）
  rm -rf -- "$DEST/$name"
  cp -R -- "$SKILLS_LIB/$name" "$DEST/"
  echo "  完成 -> $DEST/$name/"
done

echo
echo "全部完成。提示：若在 Claude Code 会话中途，新装的 skill 可能要重启会话后才会出现在技能列表。"
