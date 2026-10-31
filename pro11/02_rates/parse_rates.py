#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02_rates CLI —— 按公司选择 adapter，调用 core 解析费率表。

公司的名字与默认文件名统一放在 companies/index.json；
adapter 只负责声明“这家怎么解析”，不再重复写文件名。

用法：
    python 02_rates/parse_rates.py --list
    python 02_rates/parse_rates.py --company sunshine
    python 02_rates/parse_rates.py --company cpic
    python 02_rates/parse_rates.py --company sunshine --file "某份.pdf"

每次运行都会重新解析，没有缓存，也不需要“忽略缓存”的开关。
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import core
from parse_utils import read_json

HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent
DEFAULT_INPUT = PROJECT_DIR / "data" / "rate_tables"
DEFAULT_OUTPUT = PROJECT_DIR / "data_ouput" / "rates"
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


def format_result(result: dict) -> str:
    if result["status"] == "failed":
        return f"[FAIL] {result['file']}\n       {result.get('reason', '')}"
    flag = "[WARN]" if result["status"] == "warning" else "[ OK ]"
    return (
        f"{flag} {result['file']}\n       {result['rows']} 行，"
        f"解析 {result['parsed_pages']} 页 / 跳过 {result['skipped_pages']} 页，"
        f"单位 {result['unit']}，错误 {result['errors']}"
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="费率表 PDF → CSV（按公司选择 adapter）")
    parser.add_argument("--company", help="公司 adapter 名称，见 --list")
    parser.add_argument("--file", type=Path, help="指定 PDF；默认用 index.json 里的文件名")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="PDF 目录")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="输出目录")
    parser.add_argument("--list", action="store_true", help="列出可用的公司 adapter")
    args = parser.parse_args()

    index = load_index()

    if args.list or not args.company:
        print("可用的公司 adapter：")
        for name, file_name in sorted(index.items()):
            print(f"  {name:<10} {file_name}")
        return 0

    module = load_company(args.company, index)
    pdf = args.file or (args.input / index[args.company])
    if not pdf.exists():
        raise SystemExit(f"找不到 PDF：{pdf}")

    spec = module.build_spec(pdf)
    result = core.parse(pdf, spec, args.out)
    print(format_result(result))
    print(f"\n输出 → {args.out / pdf.stem}")
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
