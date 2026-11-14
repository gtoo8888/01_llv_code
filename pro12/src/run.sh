#!/usr/bin/env bash
# run.sh — 一键：预处理 + 传输
#
# 用法：
#   ./run.sh                        # 配置里的默认数据集，落盘 ./recv
#   ./run.sh camera                 # 换数据集
#   ./run.sh camera --dst /data/x   # 换落盘目录
#   ./run.sh --transfer             # 只跑传输（已经 prepare 过）

set -euo pipefail
cd "$(dirname "$0")"

dataset=""
dst=""
only_transfer=0

while [ $# -gt 0 ]; do
    case "$1" in
        --transfer) only_transfer=1; shift ;;
        --dst)      dst="${2:-}"; shift 2 ;;
        -h|--help)  sed -n '2,9p' "$0"; exit 0 ;;
        -*)         echo "未知参数：$1" >&2; exit 2 ;;
        *)          dataset="$1"; shift ;;
    esac
done

pargs=()
[ -n "$dataset" ] && pargs+=(--dataset "$dataset")
targs=("${pargs[@]}")
[ -n "$dst" ] && targs+=(--dst "$dst")

if [ "$only_transfer" -eq 0 ]; then
    echo "=== 1/2 预处理 ==="
    ./prepare.py "${pargs[@]}"
    echo
fi

echo "=== 传输 ==="
./android_transfer.py "${targs[@]}"
