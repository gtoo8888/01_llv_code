#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03_cashvalue CLI —— 按公司选择 adapter，调用 engine.pipeline 解析现金价值表。

公司的名字与默认文件名统一放在 companies/index.json；
adapter 只负责声明“这家怎么解析”，不再重复写文件名。

用法：
    python 03_cashvalue/parse_cashvalue.py --list
    python 03_cashvalue/parse_cashvalue.py --company sunshine --pages 1-5
    python 03_cashvalue/parse_cashvalue.py --company xinhua
    python 03_cashvalue/parse_cashvalue.py --all

每次运行都会重新解析，没有缓存，也不需要“忽略缓存”的开关。
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from engine.pipeline import Result, parse
from parse_utils import read_json

HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent
DEFAULT_INPUT = PROJECT_DIR / "data" / "cashvalue"
DEFAULT_OUTPUT = PROJECT_DIR / "data_ouput" / "cashvalue"
INDEX_PATH = HERE / "companies" / "index.json"


def load_index() -> dict:
    """读公司索引，并确认它和 companies/*.py 一一对应。"""
    index = read_json(INDEX_PATH)
    adapters = {
        path.stem
        for path in (HERE / "companies").glob("*.py")
        if not path.stem.startswith("_")
    }
    missing_adapter = sorted(set(index) - adapters)
    missing_config = sorted(adapters - set(index))
    if missing_adapter or missing_config:
        raise SystemExit(
            "companies/index.json 与 adapter 不一致："
            f"缺 adapter {missing_adapter}，缺配置 {missing_config}"
        )
    return index


def load_company(name: str, index: dict):
    if name not in index:
        raise SystemExit(f"没有这家公司的 adapter：{name}\n可选：{', '.join(sorted(index))}")
    return importlib.import_module(f"companies.{name}")


def parse_pages_arg(text: str) -> list:
    """`1-5` / `7` / `1-3,9,20-22` → [1,2,3,4,5,7,...]"""
    pages = set()
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, end = chunk.split("-", 1)
            try:
                first, last = int(start), int(end)
            except ValueError:
                raise SystemExit(f"--pages 格式不对：{chunk!r}（示例：1-5,9,20-22）")
            if first < 1 or last < first:
                raise SystemExit(f"--pages 区间不对：{chunk!r}")
            pages.update(range(first, last + 1))
        else:
            try:
                page = int(chunk)
            except ValueError:
                raise SystemExit(f"--pages 格式不对：{chunk!r}（示例：1-5,9,20-22）")
            if page < 1:
                raise SystemExit(f"--pages 必须从 1 开始：{chunk!r}")
            pages.add(page)
    if not pages:
        raise SystemExit("--pages 没有解析出任何页码")
    return sorted(pages)


def format_result(result: Result) -> str:
    if result.status == "failed":
        return f"[FAIL] {result.file}\n       {result.reason}"
    flag = "[WARN]" if result.status == "warning" else "[ OK ]"
    return (
        f"{flag} {result.file}\n       {result.rows} 行，"
        f"解析 {result.parsed_pages} 页 / 跳过 {result.skipped_pages} 页，"
        f"单位 {result.unit}，错误 {len(result.errors)}，警告 {len(result.warnings)}"
    )


def run_one(name: str, index: dict, args) -> Result:
    module = load_company(name, index)
    pdf = args.file or (args.input / index[name])
    if not pdf.exists():
        return Result(file=index.get(name, name), status="failed",
                      reason=f"找不到 PDF：{pdf}")
    try:
        spec = module.build_spec(pdf)
        if args.pages is not None:
            spec.pages = args.pages
        return parse(pdf, spec, args.out)
    except Exception as exc:  # 一家失败不影响其余
        return Result(file=index.get(name, name), status="failed",
                      reason=f"{type(exc).__name__}: {exc}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="现金价值表 PDF → CSV（按公司选择 adapter）")
    parser.add_argument("--company", help="公司 adapter 名称，见 --list")
    parser.add_argument("--all", action="store_true", help="跑 index.json 里的全部公司")
    parser.add_argument("--file", type=Path, help="指定 PDF；默认用 index.json 里的文件名")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="PDF 目录")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="输出目录")
    parser.add_argument("--pages", help="只解析这些页，如 1-5 或 1-3,9,20-22")
    parser.add_argument("--list", action="store_true", help="列出可用的公司 adapter")
    args = parser.parse_args()

    index = load_index()

    if args.list or (not args.company and not args.all):
        print("可用的公司 adapter：")
        for name, file_name in sorted(index.items()):
            print(f"  {name:<10} {file_name}")
        return 0

    args.pages = parse_pages_arg(args.pages) if args.pages else None
    if args.pages is not None:
        print(f"只解析 {len(args.pages)} 页：{args.pages[:12]}{'…' if len(args.pages) > 12 else ''}")

    names = sorted(index) if args.all else [args.company]
    results = []
    for number, name in enumerate(names, 1):
        if args.all:
            print(f"[{number}/{len(names)}] {name}", flush=True)
        result = run_one(name, index, args)
        results.append(result)
        if args.all:
            line = format_result(result).split("\n", 1)
            print(f"      {line[0].strip()}", flush=True)
            if len(line) > 1 and result.status == "failed":
                print(f"      {line[1].strip()}", flush=True)
        else:
            print(format_result(result))
            print(f"\n输出 → {args.out / Path(result.file).stem}")

    failed = sum(1 for item in results if item.status == "failed")
    if args.all:
        rows = sum(item.rows for item in results)
        parsed_pages = sum(item.parsed_pages for item in results)
        errors = sum(len(item.errors) for item in results)
        print(f"\n小计：{len(results) - failed}/{len(results)} 完成 · "
              f"{rows:,} 行 · {parsed_pages} 页 · {errors} 错误")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
