#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""android_transfer.py — 只负责「拉」。

依赖 prepare.py 已经完成的状态：远端有 remote.sh、各片的 list、以及预打好的首片。
启动后只做：读状态 → 一次产物校验 → 立刻拉首片 → 并行打包其余 → 异步删分片。

需要 Python 3.11+（用到标准库 tomllib 读配置）。

设计依据（pro12/docs/usb2_transfer/20261113214329_09_baseline_measurements.md）：
  · adb exec-out 恒 15MB/s —— 禁用
  · adb pull 单流 41MB/s，2 路并发聚合 45MB/s —— 唯一可用通道

时间戳：tar 头保留整秒 mtime，解包默认恢复；切勿用 tar -m/--touch 解包。

用法：
  ./android_transfer.py                          # 全默认
  ./android_transfer.py --dataset camera
  ./android_transfer.py --dataset camera --dst /data_sdb/recv/camera

产出：
  log/transfer_<时间戳>_<数据集>.log
  log/transfer.csv   每次一行，累积
"""

import argparse
import json
import os
import queue
import shlex
import statistics
import sys
import threading
import time
from datetime import datetime

from common import (Adb, Logger, append_csv, load_config, runtime_dir,
                    verify_archive)

CSV_HEADER = [
    "time", "dataset", "files", "mib", "shards", "workers",
    "startup_s", "total_s", "mibps_content", "mibps_wire",
    "chan_util", "machine_util", "theory_util",
    "pack_sum_s", "pull_sum_s", "pull_wall_s", "idle_s",
    "queue_med", "queue_max", "balance",
    "pull_min", "pull_med", "pull_max", "ok",
]


def load_state(cfg, dataset_name):
    path = os.path.join(runtime_dir(cfg["transfer"], "state"),
                        f"{dataset_name}.json")
    if not os.path.exists(path):
        raise SystemExit(f"找不到预处理状态：{path}\n"
                         f"请先运行：./prepare.py --dataset {dataset_name}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Transferer:
    def __init__(self, adb, cfg, state, dst, log):
        self.adb = adb
        self.cfg = cfg["transfer"]
        self.baseline = cfg["baseline"]
        self.state = state
        self.dst = dst
        self.log = log

        self.dataset_name = state["dataset"]
        self.src = state["src"]
        self.workdir = state["workdir"]
        self.expect = state["shard_expect"]
        self.workers = self.cfg["workers"]

        self.done = queue.Queue()
        self.delq = queue.Queue()
        self.errors = []
        self.pull_first = None
        self.pull_last = None
        self.tlock = threading.Lock()
        self.t0 = None

        shard_mib = state["content_bytes"] / 2**20 / max(len(self.expect), 1)
        if self.cfg["keep_remote"]:
            slots = 1 << 30
        else:
            slots = max(self.workers + 2,
                        int(self.cfg["cache_budget_mib"] // max(shard_mib, 1)))
            slots = min(slots, len(self.expect))
        self.inflight = threading.Semaphore(slots)

        self.result = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "dataset": self.dataset_name,
            "device": adb.serial,
            "src": self.src,
            "dst": dst,
            "files": state["files"],
            "content_bytes": state["content_bytes"],
            "shards": len(self.expect),
            "workers": self.workers,
            "shard_mib": round(shard_mib, 1),
        }

    def fail(self, msg):
        self.log(f"[错误] {msg}")
        sys.exit(1)

    def verify_artifacts(self):
        """一次 shell 确认 prepare 的产物都在，且首片大小与状态一致。"""
        script = (
            f"cd {shlex.quote(self.workdir)} 2>/dev/null || {{ echo remote:0; exit 0; }}; "
            f"{{ [ -f remote.sh ] && echo remote:1 || echo remote:0; }}; "
            f"{{ [ -f shard.00.tar ] && echo head:$(stat -c %s shard.00.tar) "
            f"|| echo head:0; }}; "
            f"echo lists:$(ls list.* 2>/dev/null | wc -l)"
        )
        out = self.adb.shell(script)
        info = {}
        for line in out.splitlines():
            k, _, v = line.strip().partition(":")
            if k in ("remote", "head", "lists"):
                info[k] = int(v.strip() or 0)

        if info.get("remote", 0) != 1:
            self.fail(f"手机端缺少 remote.sh（{self.workdir}）——请重新运行 prepare.py")

        prepared = [e for e in self.expect if e["prepared"]]
        need_lists = len(self.expect) - len(prepared)
        if info.get("lists", 0) != need_lists:
            self.fail(f"list 文件数量不符：期望 {need_lists}，实际 {info.get('lists', 0)}"
                      f"——请重新运行 prepare.py")

        for e in prepared:
            if info.get("head", 0) != e["archive_bytes"]:
                self.fail(f"首片大小不符：期望 {e['archive_bytes']}，"
                          f"实际 {info.get('head', 0)}——请重新运行 prepare.py")

    def deleter(self):
        """异步删除已传完的分片，不占传输通道。"""
        while True:
            tarp = self.delq.get()
            if tarp is None:
                return
            try:
                self.adb.remote(self.workdir, "rm", tarp)
            except Exception:                              # noqa: BLE001
                pass

    def packer(self):
        for e in self.expect:
            if e["prepared"]:
                continue
            self.inflight.acquire()
            try:
                shard = self.pack_shard(e)
            except Exception as exc:                       # noqa: BLE001
                self.inflight.release()
                self.errors.append(f"分片 {e['idx']} 打包失败: {exc}")
                self.log(f"  [打包 {e['idx']:02d}] 失败：{exc}")
                continue
            self.log(f"  [打包 {e['idx']:02d}] {shard['content_bytes']/2**20:.0f}MiB "
                     f"in {shard['pack_s']}s → {shard['pack_mibs']} MiB/s")
            self.done.put(shard)

    def pack_shard(self, e):
        idx = e["idx"]
        tarp = f"{self.workdir}/shard.{idx:02d}.tar"
        t = time.time()
        # list 已由 prepare 推好；remote.sh 打包后会删掉它
        out = self.adb.remote(self.workdir, "pack", self.src,
                              f"{self.workdir}/list.{idx:02d}", tarp)
        elapsed = round(time.time() - t, 3)
        return {
            "idx": idx,
            "remote": tarp,
            "files": e["files"],
            "content_bytes": e["content_bytes"],
            "archive_bytes": int(out.strip().splitlines()[-1]),
            "pack_s": elapsed,
            "pack_mibs": round(e["content_bytes"] / 2**20 / elapsed, 1) if elapsed else 0,
            "pack_end": time.time(),
        }

    def enqueue_prebuilt(self):
        """把 prepare 打好的首片直接塞进队列，让第一路 pull 立刻启动。"""
        for e in self.expect:
            if not e["prepared"]:
                continue
            self.done.put({
                "idx": e["idx"],
                "remote": f"{self.workdir}/shard.{e['idx']:02d}.tar",
                "files": e["files"],
                "content_bytes": e["content_bytes"],
                "archive_bytes": e["archive_bytes"],
                "pack_s": 0,
                "pack_mibs": 0,
                "pack_end": time.time(),
                "prebuilt": True,
            })

    def puller(self):
        # 单个分片出错只记录，不终止线程——否则哨兵数量对不上会挂死
        while True:
            shard = self.done.get()
            if shard is None:
                return
            try:
                t = time.time()
                shard["wait_s"] = round(t - shard["pack_end"], 3)
                with self.tlock:
                    if self.pull_first is None:
                        self.pull_first = t
                local = os.path.join(self.dst, f"shard.{shard['idx']:02d}.tar")
                tmp = local + ".tmp"
                # 先拉到 .tmp 再改名：中断只会留下 .tmp，不会出现假完整片
                self.adb("pull", shard["remote"], tmp)
                os.replace(tmp, local)
                shard["local"] = local
                shard["pull_s"] = round(time.time() - t, 3)
                shard["pull_mibs"] = round(
                    shard["archive_bytes"] / 2**20 / shard["pull_s"], 1
                ) if shard["pull_s"] else 0

                if self.cfg["verify_tar"]:
                    n, total = verify_archive(local, self.adb.timeout)
                    shard["verified_files"] = n
                    shard["verified_bytes"] = total
                    shard["ok"] = (n == shard["files"]
                                   and total == shard["content_bytes"])
                else:
                    shard["ok"] = True
                tag = "预打" if shard.get("prebuilt") else "打包"
                self.log(f"  [传输 {shard['idx']:02d}] "
                         f"{shard['archive_bytes']/2**20:.0f}MiB "
                         f"in {shard['pull_s']}s → {shard['pull_mibs']} MiB/s"
                         f"（{tag}，排队 {shard['wait_s']}s，"
                         f"{'校验通过' if shard['ok'] else '校验失败'}）")
            except Exception as exc:                       # noqa: BLE001
                shard.setdefault("wait_s", 0)
                shard["ok"] = False
                shard["error"] = str(exc)
                self.errors.append(f"分片 {shard['idx']}: {exc}")
                self.log(f"  [传输 {shard['idx']:02d}] 失败：{exc}")
            finally:
                with self.tlock:
                    now = time.time()
                    self.pull_last = now if self.pull_last is None else max(self.pull_last, now)
                if not self.cfg["keep_remote"]:
                    self.delq.put(shard["remote"])
                self.inflight.release()
                self.result.setdefault("shard_stats", []).append(shard)

    def run(self):
        self.t0 = time.time()
        self.verify_artifacts()

        del_thread = threading.Thread(target=self.deleter, daemon=True)
        del_thread.start()

        threads = [threading.Thread(target=self.puller, daemon=True)
                   for _ in range(self.workers)]
        for th in threads:
            th.start()

        try:
            self.enqueue_prebuilt()
            self.packer()
        finally:
            for _ in threads:
                self.done.put(None)
            for th in threads:
                th.join()
            self.delq.put(None)
            del_thread.join()

        for e in self.errors:
            self.log(f"[错误] {e}")
        self.summarize()
        return self.result

    def summarize(self):
        stats = self.result["shard_stats"]
        total_s = round(time.time() - self.t0, 3)
        content_mib = self.state["content_bytes"] / 2**20
        wire_mib = sum(s["archive_bytes"] for s in stats) / 2**20
        pull_sum = sum(s["pull_s"] for s in stats)
        pack_sum = sum(s["pack_s"] for s in stats)
        startup = round((self.pull_first - self.t0), 3) if self.pull_first else 0

        pull_wall = (self.pull_last - self.pull_first) if self.pull_first and self.pull_last else 0
        content_mibs = content_mib / total_s if total_s else 0
        wire_mibs = wire_mib / total_s if total_s else 0
        chan_util = (pull_sum / (self.workers * pull_wall)) if pull_wall else 0
        machine_util = wire_mibs / self.baseline["bus_ceiling_mibs"]
        theory_util = wire_mibs / self.baseline["theoretical_mibs"]

        # 均衡度排除预打首片——它是刻意做小的
        body = [s for s in stats if not s.get("prebuilt")] or stats
        sizes = [s["content_bytes"] for s in body] or [0]
        balance = (min(sizes) / max(sizes)) if max(sizes) else 0
        rates = [s["pull_mibs"] for s in stats if s.get("pull_mibs")] or [0]
        waits = [s.get("wait_s", 0) for s in stats]

        self.result.update({
            "startup_s": startup,
            "total_s": total_s,
            "mibps_content": round(content_mibs, 2),
            "mibps_wire": round(wire_mibs, 2),
            "chan_util": round(chan_util, 4),
            "machine_util": round(machine_util, 4),
            "theory_util": round(theory_util, 4),
            "pack_total_s": round(pack_sum, 3),
            "pull_total_s": round(pull_sum, 3),
            "pull_wall_s": round(pull_wall, 3),
            "idle_s": round(max(0.0, pull_wall * self.workers - pull_sum), 3),
            "wait_med": round(statistics.median(waits), 3),
            "wait_max": round(max(waits), 3),
            "balance": round(balance, 4),
            "pull_min": min(rates),
            "pull_med": round(statistics.median(rates), 1),
            "pull_max": max(rates),
            "all_ok": (not self.errors
                       and all(s["ok"] for s in stats)
                       and len(stats) == len(self.expect)),
        })

        self.log(f"[结果] 启动 {startup}s | 总耗时 {total_s}s | "
                 f"内容 {content_mibs:.2f} MiB/s | 线上 {wire_mibs:.2f} MiB/s | "
                 f"校验 {'全部通过' if self.result['all_ok'] else '有不一致'}")
        self.log(f"[利用] 通道 {chan_util*100:.1f}% | "
                 f"实测上限 {machine_util*100:.1f}%"
                 f"（{self.baseline['bus_ceiling_mibs']} MiB/s） | "
                 f"理论上限 {theory_util*100:.1f}%"
                 f"（{self.baseline['theoretical_mibs']} MiB/s）")
        self.log(f"[分解] 打包Σ {pack_sum:.2f}s | 传输Σ {pull_sum:.2f}s | "
                 f"传输墙钟 {pull_wall:.2f}s | 通道空闲 {self.result['idle_s']}s"
                 f"（{(1-chan_util)*100:.1f}%）")
        self.log(f"[排队] 中位 {self.result['wait_med']}s / "
                 f"最大 {self.result['wait_max']}s | "
                 f"均衡度 {balance*100:.1f}%（不含首片） | "
                 f"单流 {min(rates)}/{statistics.median(rates):.1f}/{max(rates)} MiB/s")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="传输：把 prepare 备好的分片拉回来")
    ap.add_argument("--dataset", default=None, help="数据集名（默认用配置里的 default_dataset）")
    ap.add_argument("--dst", default=None, help="主机端落盘目录（默认用配置里的 default_dst）")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    cfg = load_config()
    tp = cfg["transfer"]

    dataset_name = args.dataset or tp["default_dataset"]
    dst = os.path.abspath(args.dst or tp["default_dst"])
    state = load_state(cfg, dataset_name)
    os.makedirs(dst, exist_ok=True)

    log_dir = runtime_dir(tp, "log")
    log_path = os.path.join(log_dir,
                            f"transfer_{datetime.now():%Y%m%d_%H%M%S}_{dataset_name}.log")
    log = Logger(log_path)
    log(f"[启动] transfer dataset={dataset_name} src={state['src']} dst={dst}")
    log(f"[状态] 预处理于 {state['prepared_at']}，{state['files']} 文件 / "
        f"{state['content_bytes']/2**20:.1f} MiB / {state['shards']} 片")

    try:
        adb = Adb(tp["adb_timeout_s"])
        tr = Transferer(adb, cfg, state, dst, log)
        result = tr.run()
        append_csv(
            os.path.join(runtime_dir(tp, "metrics"), "transfer.csv"), CSV_HEADER,
            [result["ts"], dataset_name, result["files"],
             round(result["content_bytes"] / 2**20, 1),
             result["shards"], result["workers"],
             result["startup_s"], result["total_s"],
             result["mibps_content"], result["mibps_wire"],
             round(result["chan_util"] * 100, 1),
             round(result["machine_util"] * 100, 1),
             round(result["theory_util"] * 100, 1),
             result["pack_total_s"], result["pull_total_s"],
             result["pull_wall_s"], result["idle_s"],
             result["wait_med"], result["wait_max"],
             round(result["balance"] * 100, 1),
             result["pull_min"], result["pull_med"], result["pull_max"],
             int(result["all_ok"])],
            log)
    finally:
        log.close()
    return 0 if result["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
