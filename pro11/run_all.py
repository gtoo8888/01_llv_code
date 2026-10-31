#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量入口 —— 一条命令把当前能力线都跑一遍。

用法：
    python run_all.py             # 全部阶段（默认）
    python run_all.py rates       # 只跑费率表
    python run_all.py pdf         # 只跑产品文档
    python run_all.py cashvalue   # 只跑现金价值表

设计边界
--------
- 本文件不解析任何 PDF：费率表走 02_rates，文档走 01_pdf，现金价值走
  03_cashvalue，各留唯一实现。
- 公司清单来自各自的 companies/index.json，不硬编码；加公司不用改本文件。
- 单个任务失败不中断整批，最后统一汇总；退出码：全部成功 0，有失败 1。
- 不做结果缓存。01_pdf 内部仍留着缓存，本入口显式绕过（force=True），
  保证每次运行的产物都对应本次输入。
- 现金价值阶段走独立进程：02_rates 和 03_cashvalue 各有一个 core.py，
  同一个解释器里会撞模块名；子进程也正好让这一段的长耗时互不干扰。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
RATES_DIR = PROJECT_DIR / "02_rates"
PDF_DIR = PROJECT_DIR / "01_pdf"
CASHVALUE_DIR = PROJECT_DIR / "03_cashvalue"
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "data_ouput"

# 两个模块用的是扁平 import（import core / from parse_utils import ...），
# 所以要把它们各自的目录放进 sys.path，导入顺序与手动运行时一致。
for _module_dir in (str(RATES_DIR), str(PDF_DIR)):
    if _module_dir not in sys.path:
        sys.path.insert(0, _module_dir)

import core  # noqa: E402
import parse_pdf  # noqa: E402
import parse_rates  # noqa: E402
from parse_utils import read_json  # noqa: E402


# ---------------------------------------------------------------- 费率表

def run_rates() -> list:
    """按 index.json 逐家解析，返回每个任务的结果。"""
    index = parse_rates.load_index()
    input_dir = DATA_DIR / "rate_tables"
    output_dir = OUTPUT_DIR / "rates"
    names = sorted(index)

    print(f"== 费率表（{len(names)} 家）==")
    results = []

    for number, name in enumerate(names, 1):
        started = time.perf_counter()
        try:
            module = parse_rates.load_company(name, index)
            pdf = input_dir / index[name]
            if not pdf.exists():
                raise FileNotFoundError(f"找不到 PDF：{pdf}")
            spec = module.build_spec(pdf)
            result = core.parse(pdf, spec, output_dir)
        except Exception as exc:  # 一家失败不影响其余
            result = {
                "file": index.get(name, name),
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
            }

        result["name"] = name
        result["seconds"] = time.perf_counter() - started
        results.append(result)

        print(f"[{number}/{len(names)}] {name}", flush=True)
        print(f"      {format_rates(result)}", flush=True)

    print(f"      小计：{rates_totals(results)}")
    print()
    return results


def format_rates(result: dict) -> str:
    status = result["status"]
    seconds = f"{result['seconds']:.1f}s"
    if status == "failed":
        return f"FAIL · {result.get('reason', '')} · {seconds}"
    flag = "WARN" if status == "warning" else "OK"
    return (
        f"{flag} · {result['rows']} 行 · {result['parsed_pages']} 页 · "
        f"{result['errors']} 错误 · {seconds}"
    )


def rates_totals(results: list) -> str:
    passed = sum(1 for item in results if item["status"] == "ok")
    warned = sum(1 for item in results if item["status"] == "warning")
    failed = sum(1 for item in results if item["status"] == "failed")
    rows = sum(item.get("rows", 0) for item in results)
    parsed_pages = sum(item.get("parsed_pages", 0) for item in results)
    errors = sum(item.get("errors", 0) for item in results)
    seconds = sum(item["seconds"] for item in results)
    return (
        f"{passed + warned}/{len(results)} 完成（警告 {warned}，失败 {failed}）· "
        f"{rows:,} 行 · {parsed_pages} 页 · {errors} 错误 · {seconds:.1f}s"
    )


# ---------------------------------------------------------------- 产品文档

def run_pdf() -> list:
    """把 data/product_docs 下的 PDF 逐份转成 Markdown。"""
    input_dir = DATA_DIR / "product_docs"
    pdfs = sorted(input_dir.glob("*.pdf"))

    print(f"== 产品文档（{len(pdfs)} 份）==")
    results = []

    for number, pdf in enumerate(pdfs, 1):
        started = time.perf_counter()
        try:
            # force=True：绕过 01_pdf 自己的缓存，保证每次都是本次输入的结果
            result = parse_pdf.parse_one(pdf, OUTPUT_DIR, force=True)
        except Exception as exc:  # 一份失败不影响其余
            result = {
                "file": pdf.name,
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
            }

        result["seconds"] = time.perf_counter() - started
        results.append(result)

        print(f"[{number}/{len(pdfs)}] {pdf.name}", flush=True)
        print(f"      {format_pdf(result)}", flush=True)

    print(f"      小计：{pdf_totals(results)}")
    print()
    return results


def format_pdf(result: dict) -> str:
    status = result["status"]
    seconds = f"{result['seconds']:.1f}s"
    if status == "failed":
        return f"FAIL · {result.get('reason', '')} · {seconds}"
    if status == "skipped":
        return f"SKIP · {result.get('reason', '')} · {seconds}"
    flag = "WARN" if status == "warning" else "OK"
    detail = (
        f"{result['doc_type']} · {result['pages']} 页 · "
        f"{result['headings']} 标题 · 覆盖率 {result['coverage']:.0%}"
    )
    if result.get("scanned_pages"):
        detail += f" · 无文字层页 {result['scanned_pages']}"
    return f"{flag} · {detail} · {seconds}"


def pdf_totals(results: list) -> str:
    passed = sum(1 for item in results if item["status"] == "ok")
    warned = sum(1 for item in results if item["status"] == "warning")
    skipped = sum(1 for item in results if item["status"] == "skipped")
    failed = sum(1 for item in results if item["status"] == "failed")
    pages = sum(item.get("pages", 0) for item in results)
    seconds = sum(item["seconds"] for item in results)
    return (
        f"{passed + warned}/{len(results)} 完成（警告 {warned}，跳过 {skipped}，失败 {failed}）· "
        f"{pages} 页 · {seconds:.1f}s"
    )


# ---------------------------------------------------------------- 现金价值

def run_cashvalue() -> list:
    """调用 03_cashvalue 的 CLI（独立进程），它自己打印逐家结果与合计。"""
    cli = CASHVALUE_DIR / "parse_cashvalue.py"
    index_path = CASHVALUE_DIR / "companies" / "index.json"
    if not cli.exists() or not index_path.exists():
        print("== 现金价值（未安装，跳过）==")
        print()
        return []

    names = sorted(read_json(index_path))
    print(f"== 现金价值（{len(names)} 份）==", flush=True)

    started = time.perf_counter()
    code = subprocess.call([sys.executable, str(cli), "--all"], cwd=str(PROJECT_DIR))
    seconds = time.perf_counter() - started
    print(f"      阶段耗时 {seconds:.1f}s")
    print()

    if code == 0:
        return [{"status": "ok", "seconds": seconds / max(len(names), 1)} for _ in names]
    return [{"status": "failed", "reason": f"03_cashvalue 退出码 {code}", "seconds": seconds}]


# ---------------------------------------------------------------- 入口

STAGES = {"rates": run_rates, "pdf": run_pdf, "cashvalue": run_cashvalue}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="全量入口：一条命令跑完所有解析")
    parser.add_argument(
        "stage",
        nargs="?",
        default="all",
        choices=["all", "rates", "pdf", "cashvalue"],
        help="要跑的阶段：all（默认）/ rates / pdf / cashvalue",
    )
    args = parser.parse_args()

    print(f"全量运行 · {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')}")
    print()

    started = time.perf_counter()
    selected = list(STAGES) if args.stage == "all" else [args.stage]
    results = []

    for stage in selected:
        try:
            results.extend(STAGES[stage]())
        except Exception as exc:  # 整个阶段崩了也要让其余阶段继续
            print(f"== {stage} 阶段失败：{type(exc).__name__}: {exc}")
            print()
            results.append({"status": "failed", "reason": str(exc), "seconds": 0.0})

    failed = sum(1 for item in results if item["status"] == "failed")
    total = time.perf_counter() - started
    verdict = "通过" if not failed else f"有 {failed} 项失败"
    print(f"全部完成 · {len(selected)} 个阶段 · {len(results)} 个任务 · {verdict} · {total:.1f}s")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
