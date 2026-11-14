#!/system/bin/sh
# remote.sh — 手机端执行体
#
# 由主机端 xfer.py 推送到 <workdir>/remote.sh 后调用，
# 所有在手机上执行的动作都集中在这个文件里，便于审阅与手测。
#
# 用法：
#   sh remote.sh scan    <dir>                      输出 "字节数 修改时间 相对路径"
#   sh remote.sh pack    <dir> <listfile> <outfile> 打包，输出归档字节数
#   sh remote.sh df      <path>                     输出该路径所在分区可用 KB
#   sh remote.sh rm      <file>...
#   sh remote.sh cleanup <dir>
#
# 约束：Android 上是 mksh，必须 POSIX 兼容（不用 [[ ]]、数组、local）

set -u

die() {
    echo "remote.sh: $*" >&2
    exit 1
}

cmd=${1:-}
[ $# -gt 0 ] && shift

case $cmd in

scan)
    # 逐行输出 "字节数 修改时间(epoch 秒) 相对路径"
    # %Y 为整秒，与 tar 头保存的 mtime 精度一致（ustar 只存整秒）
    [ $# -eq 1 ] || die "scan 需要 1 个参数"
    cd "$1" || die "无法进入目录 $1"
    find . -type f -print0 | xargs -0 stat -c '%s %Y %n'
    ;;

pack)
    # 打包并把归档字节数打到 stdout（省掉主机端再 stat 一次）
    [ $# -eq 3 ] || die "pack 需要 3 个参数"
    dir=$1
    list=$2
    out=$3
    cd "$dir" || die "无法进入目录 $dir"
    tar -cf "$out" -T "$list" || die "tar 失败"
    rm -f "$list"
    stat -c %s "$out"
    ;;

df)
    # 输出可用空间（KB）。用于推导分片大小，避免把手机写满。
    [ $# -eq 1 ] || die "df 需要 1 个参数"
    df -k "$1" | tail -n 1 | awk '{print $4}'
    ;;

rm)
    [ $# -ge 1 ] || die "rm 需要至少 1 个参数"
    rm -f "$@"
    ;;

cleanup)
    # 整个暂存目录删掉，含残留分片与脚本自身
    [ $# -eq 1 ] || die "cleanup 需要 1 个参数"
    rm -rf "$1"
    ;;

*)
    echo "用法: sh remote.sh {scan|pack|df|rm|cleanup} ..." >&2
    exit 2
    ;;
esac
