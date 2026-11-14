#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""common.py — prepare.py 与 android_transfer.py 的公共部分。

需要 Python 3.11+（tomllib）。
"""

import csv
import os
import shlex
import subprocess
import threading
import tomllib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.toml")
REMOTE_SCRIPT = os.path.join(BASE_DIR, "remote.sh")


def load_config():
    """读 config/config.toml。读不到就让它抛异常，不兜底。"""
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def runtime_dir(tp, kind):
    """取 runtime/<kind> 的绝对路径，顺手把目录建好。

    kind 只有三种，写死不再配置：
      state    —— 预处理状态，单次有效，删了重跑 prepare 即可
      log      —— 每次运行一份日志，可定期清
      metrics  —— 两个累积 CSV，唯一不可重建的资产
    三个子目录的生命周期完全不同，所以分开；但都属于同一个根，
    因为它们的搬动永远是同步的。
    """
    path = os.path.join(BASE_DIR, tp["runtime_dir"], kind)
    os.makedirs(path, exist_ok=True)
    return path


class Logger:
    """同时写终端与日志文件，每行带完整日期时间。线程安全。"""

    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.fh = open(path, "w", encoding="utf-8")
        self.lock = threading.Lock()

    def __call__(self, msg=""):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{stamp}] {msg}"
        with self.lock:
            print(line, flush=True)
            self.fh.write(line + "\n")
            self.fh.flush()

    def close(self):
        self.fh.close()


def _run(cmd, timeout, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"命令超时（{timeout}s）：{' '.join(cmd)}")


class Adb:
    """adb 客户端。刻意不加锁：多个 adb 进程可并发，这正是多流提速的前提。"""

    def __init__(self, timeout):
        self.timeout = timeout
        self.serial = self._auto_serial()

    def _auto_serial(self):
        out = _run(["adb", "devices"], self.timeout).stdout
        devs = [l.split()[0] for l in out.splitlines()[1:] if l.strip()]
        if len(devs) != 1:
            raise SystemExit(f"需要恰好一台设备，当前 {len(devs)} 台：{devs}")
        return devs[0]

    def __call__(self, *args, check=True):
        cmd = ["adb", "-s", self.serial] + list(args)
        r = _run(cmd, self.timeout)
        if check and r.returncode != 0:
            raise RuntimeError(f"adb {' '.join(args)} 失败：{r.stderr.strip()}")
        return r.stdout

    def shell(self, script, check=True):
        return self("shell", script, check=check)

    def remote(self, workdir, *args):
        """调用远端脚本：sh <workdir>/remote.sh <子命令> [参数...]"""
        parts = [f"{workdir}/remote.sh"] + [str(a) for a in args]
        return self.shell("sh " + " ".join(shlex.quote(p) for p in parts))


def partition(files, k):
    """按字节贪心分配到最轻的组。files 为 [(size, mtime, path)]。"""
    k = max(1, min(k, len(files)))
    groups = [[] for _ in range(k)]
    load = [0] * k
    for item in sorted(files, key=lambda x: -x[0]):
        i = load.index(min(load))
        groups[i].append(item)
        load[i] += item[0]
    return [g for g in groups if g]


def split_head(files, head_bytes):
    """切出首片。

    用「不超过首片预算的最大文件」填充，而不是最小的：
    体积仍可控（不会超过预算），但文件数少、打包快。
    用最小文件填会把 64MiB 塞成几百个碎文件，每文件开销反而让它更慢。
    塞不下的文件直接跳过、继续试更小的，保证累计体积不越过预算。
    若所有文件都超过预算，退化取最小的那个（文件不可拆）。
    """
    fits = sorted((f for f in files if f[0] <= head_bytes), key=lambda x: -x[0])
    head, acc, taken = [], 0, set()
    for f in fits:
        if acc + f[0] > head_bytes:
            continue
        head.append(f)
        acc += f[0]
        taken.add(f[2])
    if not head:
        f = min(files, key=lambda x: x[0])
        head, taken = [f], {f[2]}
    rest = [f for f in files if f[2] not in taken]
    return head, rest


def verify_archive(path, timeout):
    """只读 tar 头，返回 (文件数, 内容字节数)。约 0.03s/460MB。"""
    r = _run(["tar", "-tvf", path], timeout)
    n = total = 0
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) < 6 or not parts[0].startswith("-"):
            continue
        try:
            total += int(parts[2])
            n += 1
        except (ValueError, IndexError):
            continue
    return n, total


def append_csv(path, header, row, log):
    """追加一行到 CSV。首次写入时加 UTF-8 BOM，便于 Excel 直接打开。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    is_new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        if is_new:
            f.write("\ufeff")
            csv.writer(f).writerow(header)
        csv.writer(f).writerow(row)
    log(f"[记录] {path}")
