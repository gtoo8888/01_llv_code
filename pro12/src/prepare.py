#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prepare.py — 把手机变成「随时可开拉」的状态。

做完全部慢活与杂活，让 android_transfer.py 启动即可拉：
  1. 清空手机工作区（含上次残留）
  2. 推送 remote.sh
  3. 扫描：大小 + mtime + 路径
  4. 检查空间与数据量下限
  5. 分组：首片用「不超预算的最大文件」填充，刻意做小
  6. 推送 list.1..list.K-1
  7. 打包首片 shard.00.tar（打包完远端自动删 list.00）
  8. 写 state/<dataset>.json

时间戳：tar 头保留整秒 mtime，解包默认恢复；切勿用 tar -m/--touch 解包。

用法：
  ./prepare.py                          # 用配置里的 default_dataset
  ./prepare.py --dataset camera
  ./prepare.py --dataset camera --shards 16
"""

import argparse
import json
import os
import sys
import tempfile
import shlex
import time
from datetime import datetime

from common import (REMOTE_SCRIPT, Adb, Logger, append_csv, load_config,
                    partition, runtime_dir, split_head)

CSV_HEADER = [
    "time", "dataset", "files", "mib", "shards",
    "wipe_s", "scan_s", "scan_ms_per_file", "free_mib", "budget_mib",
    "push_s", "pack_head_s", "head_mib", "prep_total_s",
]


class Preparer:
    def __init__(self, adb, cfg, dataset_name, dataset, log, shards=0):
        self.adb = adb
        self.cfg = cfg["transfer"]
        self.dataset_name = dataset_name
        self.dataset = dataset
        self.src = dataset["src"]
        self.log = log
        self.shards_override = shards
        self.workdir = self.cfg["remote_tmp"]

        self.files = []
        self.groups = []
        self.head = None
        self.head_archive = None
        self.state = {
            "dataset": dataset_name,
            "src": self.src,
            "prepared_at": datetime.now().isoformat(timespec="seconds"),
            "workdir": self.workdir,
            "workers": self.cfg["workers"],
        }
        self.t0 = time.time()

    def fail(self, msg):
        self.log(f"[错误] {msg}")
        sys.exit(1)

    def wipe(self):
        # 这里只能用裸 shell：remote.sh 可能已被上一次运行删掉（它就在工作区里）
        t = time.time()
        self.adb.shell(f"rm -rf {shlex.quote(self.workdir)}")
        self.state["wipe_s"] = round(time.time() - t, 3)
        self.log(f"[清理] 手机工作区已清空 ({self.state['wipe_s']}s)")

    def push_manifest(self):
        """把完整清单落到手机，纯备查用（不参与传输逻辑）。"""
        t = time.time()
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            for size, mtime, path in sorted(self.files, key=lambda x: x[2]):
                f.write(f"{size}\t{mtime}\t{path}\n")
            local = f.name
        try:
            self.adb("push", local, f"{self.workdir}/manifest.tsv")
        finally:
            os.unlink(local)
        self.log(f"[清单] manifest.tsv 已落手机 ({time.time()-t:.2f}s)")

    def deploy(self):
        if not os.path.exists(REMOTE_SCRIPT):
            self.fail(f"找不到远端脚本：{REMOTE_SCRIPT}")
        self.adb.shell(f"mkdir -p {self.workdir}")
        self.adb("push", REMOTE_SCRIPT, f"{self.workdir}/remote.sh")

    def scan(self):
        t = time.time()
        files = []
        for line in self.adb.remote(self.workdir, "scan", self.src).splitlines():
            parts = line.strip().split(" ", 2)
            if len(parts) != 3:
                continue
            try:
                files.append((int(parts[0]), int(parts[1]), parts[2]))
            except ValueError:
                continue
        if not files:
            self.fail("远端没有文件，检查配置里的 src")

        self.files = files
        scan_s = round(time.time() - t, 3)
        total_bytes = sum(f[0] for f in files)
        self.state.update({
            "scan_s": scan_s,
            "files": len(files),
            "content_bytes": total_bytes,
            "mtime_min": datetime.fromtimestamp(min(f[1] for f in files)).isoformat(),
            "mtime_max": datetime.fromtimestamp(max(f[1] for f in files)).isoformat(),
        })
        self.log(f"[扫描] {len(files)} 个文件 / {total_bytes/2**20:.1f} MiB "
                 f"({scan_s}s, {scan_s*1000/len(files):.2f}ms/文件)")

        expect = self.dataset.get("expect_files")
        if expect is not None and expect != len(files):
            self.log(f"[警告] 配置写的是 {expect} 个文件，实际 {len(files)} 个"
                     f"——数据集已变化，历史跑分不可直接比")

    def plan(self):
        workers = self.cfg["workers"]
        total_mib = self.state["content_bytes"] / 2**20

        if total_mib < self.cfg["min_total_mib"]:
            self.fail(f"数据量 {total_mib:.1f} MiB 小于 {self.cfg['min_total_mib']} MiB，"
                      f"走这套流水线不划算。直接用：adb pull {self.src} <目标目录>")

        free_kb = int(self.adb.remote(self.workdir, "df", self.workdir).strip())
        free_mib = free_kb / 1024
        budget_mib = self.cfg["cache_budget_mib"]
        if free_mib < budget_mib:
            self.fail(f"手机可用空间 {free_mib:.0f} MiB，小于缓存预算 {budget_mib} MiB。"
                      f"请清理手机空间，或把 config.toml 的 cache_budget_mib "
                      f"改到 {int(free_mib * 0.8)} 以下")

        target = budget_mib / (workers * 2)
        target = min(max(target, self.cfg["shard_min_mib"]), self.cfg["shard_max_mib"])

        if self.shards_override:
            k = self.shards_override
            self.groups = partition(self.files, k)
            self.head = None
            self.log(f"[分片] 命令行指定 {k} 片（不使用首片逻辑）")
        else:
            head_mib = min(self.cfg["first_shard_mib"], total_mib / 2)
            head, rest = split_head(self.files, head_mib * 2**20)
            rest_bytes = sum(item[0] for item in rest)
            k_rest = max(1, -(-rest_bytes // int(target * 2**20)))
            k = max(self.cfg["min_shards"], 1 + k_rest)
            self.head = head
            self.groups = [head] + partition(rest, k - 1)
            self.log(f"[分片] 首片 {sum(f[0] for f in head)/2**20:.0f} MiB"
                     f"（不超预算的最大文件）+ 其余 {k - 1} 片")

        self.state.update({
            "free_mib": round(free_mib, 0),
            "budget_mib": budget_mib,
            "target_shard_mib": round(target, 1),
            "shards": len(self.groups),
        })
        self.log(f"[预算] 手机可用 {free_mib:.0f} MiB，缓存预算 {budget_mib} MiB"
                 f" → 目标 {target:.0f} MiB/片")
        self.log(f"[分组] {len(self.groups)} 片，"
                 + " / ".join(f"{sum(s for s,_,_ in g)/2**20:.0f}MiB×{len(g)}"
                              for g in self.groups))

    def push_lists(self):
        t = time.time()
        for i, group in enumerate(self.groups):
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
                f.write("\n".join(item[2] for item in group) + "\n")
                local = f.name
            try:
                self.adb("push", local, f"{self.workdir}/list.{i:02d}")
            finally:
                os.unlink(local)
        self.state["push_s"] = round(time.time() - t, 3)
        self.log(f"[列表] {len(self.groups)} 份已推到手机 ({self.state['push_s']}s)")

    def pack_head(self):
        """预打首片。打包完 remote.sh 会自动删掉 list.00。"""
        if not self.head:
            return
        tarp = f"{self.workdir}/shard.00.tar"
        t = time.time()
        out = self.adb.remote(self.workdir, "pack", self.src,
                              f"{self.workdir}/list.00", tarp)
        elapsed = round(time.time() - t, 3)
        content = sum(item[0] for item in self.head)
        self.head_archive = int(out.strip().splitlines()[-1])
        self.state["pack_head_s"] = elapsed
        self.state["head_mib"] = round(content / 2**20, 1)
        self.log(f"[首片] {content/2**20:.0f}MiB in {elapsed}s → "
                 f"{content/2**20/elapsed:.1f} MiB/s（已备好，传输时可直接拉）")

    def save_state(self):
        checks = []
        for i, g in enumerate(self.groups):
            is_head = bool(self.head) and i == 0
            checks.append({
                "idx": i,
                "files": len(g),
                "content_bytes": sum(f[0] for f in g),
                "archive_bytes": self.head_archive if is_head else None,
                "prepared": is_head,
            })
        self.state["shard_expect"] = checks
        self.state["prep_total_s"] = round(time.time() - self.t0, 3)

        path = os.path.join(runtime_dir(self.cfg, "state"),
                            f"{self.dataset_name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        self.state["_state_path"] = path

    def run(self):
        self.wipe()
        self.deploy()
        self.scan()
        self.push_manifest()
        self.plan()
        self.push_lists()
        self.pack_head()
        self.save_state()

        self.log(f"[完成] 预处理 {self.state['prep_total_s']}s | "
                 f"{self.state['files']} 文件 / {self.state['content_bytes']/2**20:.1f} MiB "
                 f"/ {self.state['shards']} 片")
        self.log(f"[就绪] 现在可以运行 ./android_transfer.py --dataset {self.dataset_name}")
        return self.state


def main(argv=None):
    ap = argparse.ArgumentParser(description="预处理：扫描、分组、预打首片")
    ap.add_argument("--dataset", default=None, help="数据集名（默认用配置里的 default_dataset）")
    ap.add_argument("--shards", type=int, default=0,
                    help="手动指定分片数（默认 0 = 自动推导）")
    args = ap.parse_args(argv)

    cfg = load_config()
    tp = cfg["transfer"]
    dataset_name = args.dataset or tp["default_dataset"]
    dataset = cfg["datasets"][dataset_name]

    log_dir = runtime_dir(tp, "log")
    log_path = os.path.join(log_dir,
                            f"prepare_{datetime.now():%Y%m%d_%H%M%S}_{dataset_name}.log")
    log = Logger(log_path)
    log(f"[启动] prepare dataset={dataset_name} src={dataset['src']}")

    try:
        adb = Adb(tp["adb_timeout_s"])
        prep = Preparer(adb, cfg, dataset_name, dataset, log, args.shards)
        state = prep.run()
        append_csv(
            os.path.join(runtime_dir(tp, "metrics"), "prepare.csv"), CSV_HEADER,
            [state["prepared_at"], dataset_name, state["files"],
             round(state["content_bytes"] / 2**20, 1), state["shards"],
             state.get("wipe_s", 0), state["scan_s"],
             round(state["scan_s"] * 1000 / max(state["files"], 1), 2),
             state["free_mib"], state["budget_mib"],
             state.get("push_s", 0), state.get("pack_head_s", 0),
             state.get("head_mib", 0), state["prep_total_s"]],
            log)
    finally:
        log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
