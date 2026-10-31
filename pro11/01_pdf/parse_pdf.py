#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""01_pdf v0.1.0 —— 把保险产品文档（条款 / 说明书）解析成可读 Markdown。

输入：data/product_docs/*.pdf
输出：data/parsed/<name>.md
      data/parsed/<name>.outline.md
      data/parsed/<name>.meta.json

设计边界
--------
- 只处理以正文为主的产品文档；费率表、现金价值表识别后跳过。
- 表格不做专门修复：能顺着文字流读出来多少算多少，坏了就坏了。
- 不做 OCR：没有文字层直接报错，不猜。

用法
----
    python 01_pdf/parse_pdf.py
    python 01_pdf/parse_pdf.py --input data/product_docs --out data/parsed
    python 01_pdf/parse_pdf.py --file "data/product_docs/xxx.pdf" --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖：请先执行  python -m pip install pdfplumber")

from parse_utils import read_json, write_json, write_text

VERSION = "0.1.0"
PARSER_NAME = "01_pdf"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_DIR / "data" / "product_docs"
DEFAULT_OUTPUT = PROJECT_DIR / "data_ouput"

# ---------------------------------------------------------------- 正则

CN_NUM = "一二三四五六七八九十百零〇"

RE_CHAPTER = re.compile(rf"^第\s*[{CN_NUM}]+\s*章")
RE_ARTICLE = re.compile(rf"^第\s*[{CN_NUM}]+\s*条")
RE_ITEM_CN = re.compile(rf"^[{CN_NUM}]+\s*、")
RE_ITEM_PAREN = re.compile(rf"^[（(]\s*[{CN_NUM}]+\s*[)）]")
# 1. / 1、 / 1.1 之类；后面不能紧跟数字，避免把 "1.7×1.3cm" 当编号
RE_NUM_ITEM = re.compile(r"^\d{1,2}\s*[、.．]\s*(?!\d)")
# 行中间又冒出一个编号（如附录 "… 96.脊髓空洞症"），说明这是多栏内容挤在一行，不是标题
RE_SECOND_NUM = re.compile(r"\s\d{1,3}\s*[.、]")

# 备案号，如 "中国人寿〔2026〕疾病保险26号"
RE_FILING = re.compile(
    r"[\u4e00-\u9fa5A-Za-z]{2,20}[〔\[【(]\s*20\d{2}\s*[〕\]】)]"
    r"[\u4e00-\u9fa5A-Za-z0-9（）()]{0,30}?\d+\s*号"
)

RE_PUA = re.compile(r"[\ue000-\uf8ff]")
RE_SPACES = re.compile(r"[ \t\u00a0]{2,}")

PAGE_NO_PATTERNS = [
    re.compile(r"^第\s*\d+\s*页(?:\s*[，,、/]?\s*共\s*\d+\s*页)?$"),
    re.compile(r"^共\s*\d+\s*页\s*第\s*\d+\s*页$"),
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^[-—–_]\s*\d+\s*[-—–_]$"),
    re.compile(r"^\d{1,3}$"),
]


# ---------------------------------------------------------------- 基础工具

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_text(text: str) -> str:
    """去掉私有区字符、压缩空格；不做全角/半角归一化，保持原样。"""
    text = RE_PUA.sub("", text)
    text = text.replace("\u3000", " ")
    text = RE_SPACES.sub(" ", text)
    return text.strip()


def norm_for_repeat(text: str) -> str:
    """页眉页脚比对用的归一化：数字统一替换，去空格。"""
    text = re.sub(r"\d+", "#", text)
    return re.sub(r"\s+", "", text)


def is_page_number(text: str) -> bool:
    t = text.strip()
    return any(p.match(t) for p in PAGE_NO_PATTERNS)


def is_tableish(text: str) -> bool:
    """粗判表格行：数字占比高，或空格分段多。只用来决定要不要合并成段。"""
    if not text:
        return False
    digits = sum(ch.isdigit() for ch in text)
    if len(text) >= 6 and digits / len(text) > 0.28:
        return True
    return text.count(" ") >= 8


# ---------------------------------------------------------------- 提取

def group_lines(words: list) -> list:
    """把 pdfplumber 的 words 按 y 坐标聚成行，保留字号。"""
    if not words:
        return []

    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows = []
    current = [words[0]]
    current_top = words[0]["top"]

    for word in words[1:]:
        # 行内 y 抖动容忍 3pt；用行首 top 比较，避免逐行漂移
        if abs(word["top"] - current_top) <= 3.0:
            current.append(word)
        else:
            rows.append(current)
            current = [word]
            current_top = word["top"]
    rows.append(current)

    lines = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        parts = []
        prev = None
        for word in row:
            if prev is not None:
                gap = word["x0"] - prev["x1"]
                size = max(prev.get("size") or 0, word.get("size") or 0)
                # 中文一般无空格；只有明显间隙才补空格，保留英文/数字之间的间隔
                if gap > size * 0.35:
                    parts.append(" ")
            parts.append(word["text"])
            prev = word

        text = clean_text("".join(parts))
        if not text:
            continue

        sizes = [w.get("size") or 0 for w in row]
        lines.append(
            {
                "text": text,
                "size": round(max(sizes), 1),
                "top": min(w["top"] for w in row),
            }
        )

    return lines


def read_pages(pdf_path: Path) -> list:
    """逐页取行。返回 [{no, lines, chars, width, height}, ...]"""
    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(extra_attrs=["size"], keep_blank_chars=False)
            lines = group_lines(words)
            pages.append(
                {
                    "no": page_no,
                    "lines": lines,
                    "chars": sum(len(line["text"]) for line in lines),
                    "width": round(float(page.width), 1),
                    "height": round(float(page.height), 1),
                }
            )
    return pages


# ---------------------------------------------------------------- 清洗

def strip_headers_footers(pages: list) -> int:
    """按“跨页重复”识别页眉页脚，只删页边 2 行内的重复行。首页不动。"""
    if len(pages) < 3:
        return 0

    counter = Counter()
    for page in pages:
        if page["no"] == 1:
            continue
        lines = page["lines"]
        for line in lines[:2] + lines[-2:]:
            key = norm_for_repeat(line["text"])
            if key:
                counter[key] += 1

    threshold = max(3, int(len(pages) * 0.4) + 1)
    repeated = {key for key, hits in counter.items() if hits >= threshold}

    removed = 0
    for page in pages:
        if page["no"] == 1:
            continue
        lines = page["lines"]
        kept = []
        for index, line in enumerate(lines):
            near_edge = index < 2 or index >= len(lines) - 2
            if near_edge and (
                norm_for_repeat(line["text"]) in repeated or is_page_number(line["text"])
            ):
                removed += 1
                continue
            kept.append(line)
        page["lines"] = kept
        page["chars"] = sum(len(line["text"]) for line in kept)

    return removed


def body_size_of(pages: list) -> float:
    """按字符数加权，取出现最多的字号，作为正文字号。"""
    counter = Counter()
    for page in pages:
        for line in page["lines"]:
            counter[round(line["size"] * 2) / 2] += len(line["text"])
    if not counter:
        return 0.0
    return counter.most_common(1)[0][0]


# ---------------------------------------------------------------- 结构化

def heading_level(text: str, size: float, body_size: float) -> int | None:
    """返回 2..5 的标题级别；不是标题返回 None。"""
    t = text.strip()
    if not t:
        return None
    if RE_FILING.search(t):
        return None

    if RE_CHAPTER.match(t):
        return 2
    if RE_ARTICLE.match(t):
        return 3
    # 章条之下的一、二、只在短行上算小标题；"一、恶性肿瘤——重度：指……" 是正文。
    if RE_ITEM_CN.match(t) and len(t) <= 20:
        return 4
    if RE_ITEM_PAREN.match(t) and len(t) <= 30:
        return 5
    # 纯数字编号只在“短行”上算标题。附录里的疾病清单同样是 "1." 开头，
    # 但行很长或中间又出现编号，不应进入目录。
    if (
        RE_NUM_ITEM.match(t)
        and len(t) <= 40
        and not RE_SECOND_NUM.search(t)
        and not is_tableish(t)
        and not t.endswith(("。", "；", "，", ",", ";"))
    ):
        return 5

    # 说明书常见：无编号、字号变大。要求是短行且不带句末标点。
    if body_size and size >= body_size + 1.0:
        if len(t) <= 40 and not t.endswith(("。", "；", "，", ",", ";")):
            return 2 if size >= body_size + 2.5 else 3

    return None


def joinable(prev_text: str, text: str) -> bool:
    if not prev_text:
        return False
    if prev_text.endswith(("。", "！", "？", "；", "：", "”", "》", "）", ")", "】")):
        return False
    if is_tableish(prev_text) or is_tableish(text):
        return False
    return True


def render(pages: list, title: str, body_size: float):
    """返回 (markdown 正文行列表, 目录条目列表)"""
    md = []
    outline = []
    buffer = []

    def flush():
        if buffer:
            md.append("".join(buffer).strip())
            md.append("")
            buffer.clear()

    for page in pages:
        lines = page["lines"]
        if not lines:
            continue

        # 目录页本身就是“标题的堆叠”，再生成标题只会污染 outline。
        toc_like = any("目录" in line["text"] for line in lines[:4])

        flush()
        md.append(f"<!-- page: {page['no']} -->")
        md.append("")

        for line in lines:
            text = line["text"]
            level = None if toc_like else heading_level(text, line["size"], body_size)
            if level is not None:
                flush()
                md.append("#" * level + " " + text)
                md.append("")
                outline.append((level, text, page["no"]))
                continue

            if not buffer:
                buffer.append(text)
            elif joinable(buffer[-1], text):
                buffer.append(text)
            else:
                # 不合并：先把上一段收尾，当前行作为新段的第一行继续累积，
                # 这样下一行仍有合并机会，不会把句子拆成两段。
                flush()
                buffer.append(text)

    flush()
    return md, outline


# ---------------------------------------------------------------- 文档信息

def detect_type(pdf_path: Path, pages: list) -> str:
    name = pdf_path.stem
    if "费率表" in name:
        return "费率表"
    if "现金价值" in name:
        return "现金价值表"
    if "条款" in name:
        return "条款"
    if "说明书" in name or "产品说明" in name:
        return "说明书"

    head = " ".join(
        line["text"] for page in pages[:2] for line in page["lines"]
    )[:800]
    if "保险条款" in head:
        return "条款"
    if "产品说明书" in head:
        return "说明书"
    return "其他"


def find_filing_no(pages: list) -> str:
    for page in pages[:2]:
        for line in page["lines"]:
            match = RE_FILING.search(line["text"])
            if match:
                return match.group(0).strip()
    return ""


def title_from_filename(pdf_path: Path) -> str:
    name = re.sub(r"^\d{8}_", "", pdf_path.stem)
    return name.replace("_", " · ")


def make_front_matter(info: dict) -> list:
    def q(value):
        return json.dumps(value, ensure_ascii=False)

    return [
        "---",
        f"title: {q(info['title'])}",
        f"source_file: {q(info['source_file'])}",
        f"pages: {info['pages']}",
        f"doc_type: {q(info['doc_type'])}",
        f"filing_no: {q(info['filing_no'])}",
        f"sha256: {info['sha256']}",
        f"parser: {PARSER_NAME} v{VERSION}",
        f"parsed_at: {info['parsed_at']}",
        "---",
        "",
    ]


def make_outline(title: str, outline: list) -> str:
    lines = [f"# 目录 · {title}", ""]
    if not outline:
        lines.append("（未识别到章条标题，可能是纯段落文档）")
        return "\n".join(lines) + "\n"

    for level, text, page_no in outline:
        indent = "  " * max(level - 2, 0)
        lines.append(f"{indent}- {text}　· p.{page_no}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 单份处理

def parse_one(pdf_path: Path, out_dir: Path, force: bool) -> dict:
    source_file = pdf_path.name
    digest = sha256_of(pdf_path)
    stem = pdf_path.stem
    # 一份 PDF 的三个产物放进以文件名命名的子目录
    doc_dir = out_dir / stem
    md_path = doc_dir / f"{stem}.md"
    outline_path = doc_dir / f"{stem}.outline.md"
    meta_path = doc_dir / f"{stem}.meta.json"

    if not force and meta_path.exists() and md_path.exists():
        try:
            old = read_json(meta_path)
            if old.get("source", {}).get("sha256") == digest:
                return {"file": source_file, "status": "skipped", "reason": "哈希一致，已解析"}
        except (json.JSONDecodeError, OSError):
            pass

    pages = read_pages(pdf_path)

    total_chars = sum(page["chars"] for page in pages)
    if total_chars < 50:
        return {
            "file": source_file,
            "status": "failed",
            "reason": "没有文字层（可能是扫描件），本轮不做 OCR",
        }

    doc_type = detect_type(pdf_path, pages)
    if doc_type in ("费率表", "现金价值表"):
        return {
            "file": source_file,
            "status": "skipped",
            "reason": f"非产品文档（{doc_type}），不归 01_pdf 处理",
        }

    removed = strip_headers_footers(pages)
    body_size = body_size_of(pages)
    filing_no = find_filing_no(pages)
    title = title_from_filename(pdf_path)
    parsed_at = datetime.now().astimezone().isoformat(timespec="seconds")

    md_body, outline = render(pages, title, body_size)

    chars_raw = total_chars
    chars_clean = sum(len(line["text"]) for page in pages for line in page["lines"])
    scanned_pages = [page["no"] for page in pages if page["chars"] < 20]

    first = pages[0]
    info = {
        "title": title,
        "source_file": source_file,
        "pages": len(pages),
        "doc_type": doc_type,
        "filing_no": filing_no,
        "sha256": digest,
        "parsed_at": parsed_at,
    }

    parts = make_front_matter(info)
    parts.append(f"# {title}")
    parts.append("")
    parts.extend(md_body)
    doc_dir.mkdir(parents=True, exist_ok=True)
    write_text(md_path, "\n".join(parts).rstrip() + "\n")
    write_text(outline_path, make_outline(title, outline))

    meta = {
        "source": {
            "file": source_file,
            "path": str(pdf_path),
            "sha256": digest,
            "bytes": pdf_path.stat().st_size,
            "pages": len(pages),
            "page_size": [first["width"], first["height"]],
        },
        "document": {
            "type": doc_type,
            "title": title,
            "filing_no": filing_no,
        },
        "parser": {
            "name": PARSER_NAME,
            "version": VERSION,
            "parsed_at": parsed_at,
        },
        "stats": {
            "chars_raw": chars_raw,
            "chars_clean": chars_clean,
            "coverage": round(chars_clean / chars_raw, 3) if chars_raw else 0,
            "headings": len(outline),
            "body_size": body_size,
            "removed_header_footer_lines": removed,
            "scanned_pages": scanned_pages,
        },
        "outputs": {
            "markdown": md_path.name,
            "outline": outline_path.name,
        },
    }
    write_json(meta_path, meta)

    status = "ok"
    if scanned_pages or meta["stats"]["coverage"] < 0.6:
        status = "warning"

    return {
        "file": source_file,
        "status": status,
        "doc_type": doc_type,
        "pages": len(pages),
        "headings": len(outline),
        "coverage": meta["stats"]["coverage"],
        "scanned_pages": scanned_pages,
    }


# ---------------------------------------------------------------- 入口

def iter_pdfs(input_path: Path, single: Path | None) -> list:
    if single is not None:
        return [single]
    return sorted(input_path.glob("*.pdf"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="把产品文档 PDF 解析成 Markdown")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="PDF 目录")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="输出目录")
    parser.add_argument("--file", type=Path, default=None, help="只处理单个 PDF")
    parser.add_argument("--force", action="store_true", help="忽略缓存，强制重解析")
    parser.add_argument("--quiet", action="store_true", help="只打印汇总")
    args = parser.parse_args()

    pdfs = iter_pdfs(args.input, args.file)
    if not pdfs:
        print(f"没有找到 PDF：{args.input}")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    results = []
    for pdf in pdfs:
        try:
            result = parse_one(pdf, args.out, args.force)
        except Exception as exc:  # 单份失败不中断整批
            result = {"file": pdf.name, "status": "failed", "reason": repr(exc)}
        results.append(result)
        if not args.quiet:
            print(format_result(result))

    ok = sum(1 for r in results if r["status"] in ("ok", "warning"))
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\n完成：成功 {ok}，跳过 {skipped}，失败 {failed}，输出 → {args.out}")
    return 0 if failed == 0 else 1


def format_result(result: dict) -> str:
    name = result["file"]
    status = result["status"]
    if status == "failed":
        return f"[FAIL] {name}\n       {result.get('reason', '')}"
    if status == "skipped":
        return f"[SKIP] {name}\n       {result.get('reason', '')}"

    flag = "[WARN]" if status == "warning" else "[ OK ]"
    detail = (
        f"{result['doc_type']}，{result['pages']} 页，"
        f"{result['headings']} 个标题，覆盖率 {result['coverage']:.0%}"
    )
    if result.get("scanned_pages"):
        detail += f"，无文字层页 {result['scanned_pages']}"
    return f"{flag} {name}\n       {detail}"


if __name__ == "__main__":
    sys.exit(main())
