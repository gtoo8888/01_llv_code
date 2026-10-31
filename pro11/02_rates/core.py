#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02_rates core —— 与公司无关的费率表解析。

职责边界
--------
core 只做“任何一家费率表都要做”的事：
  读 PDF → 取词 → 聚列 → 聚行 → 定位年龄列 → 映射性别/交费期 → 输出 CSV → 校验

core 不猜公司。每家公司的差异（单位、页范围、抽样答案）由 companies/*.py
构造一个 Spec 传进来。core 不认识“阳光”或“太保”。
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖：请先执行  python -m pip install pdfplumber")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "01_pdf"))
from parse_utils import write_json, write_text  # noqa: E402

PARSER_NAME = "02_rates"

# 这三个不是“版式参数”，是“这页根本不是表”的守卫，不该由 adapter 调
MIN_TEXT_CHARS = 50
MIN_NUMBERS_PER_PAGE = 20
MAX_AGE = 120

NUM_RE = re.compile(r"^\d+(?:\.\d+)?$")
TERM_RE = re.compile(r"^(\d+)\s*年交$")
ONE_TIME_TERMS = {"一次性支付", "一次性交付", "一次性交纳", "趸交", "一次性交清"}
GENDERS = {"男", "女", "男性", "女性"}

UNIT_PATTERNS = [
    re.compile(r"每\s*([\d,，]+)\s*元基本保险金额"),
    re.compile(r"每(千|万)元基本保险金额"),
    re.compile(r"以\s*([\d,，]+)\s*元基本保险金额"),
    re.compile(r"基本保险金额[：:]\s*([\d,，]+)\s*元"),
]


@dataclass
class Thresholds:
    """判定一页是不是费率网格的门限。默认服务多数公司，特例在 adapter 覆盖。"""

    min_age_values: int = 10        # 年龄列至少几个值
    min_age_span: int = 20          # 年龄跨度至少多少岁
    max_age_gap: int = 2            # 相邻年龄最多隔几岁
    min_consecutive_ratio: float = 0.85
    min_columns: int = 5            # 聚列后至少剩几列
    min_rate_columns: int = 4       # 其中至少几列是费率
    max_terms_ratio: float = 3.0    # 表头交费期数量 / 费率列数 的上限
    min_rows: int = 10              # 一页至少几行才算网格

    def __post_init__(self):
        if self.min_age_values < 1:
            raise ValueError(f"min_age_values 必须 ≥1，当前 {self.min_age_values}")
        if self.min_age_span < 0:
            raise ValueError(f"min_age_span 不能为负，当前 {self.min_age_span}")
        if self.max_age_gap < 1:
            raise ValueError(f"max_age_gap 必须 ≥1，当前 {self.max_age_gap}")
        if not 0 < self.min_consecutive_ratio <= 1:
            raise ValueError(f"min_consecutive_ratio 必须在 (0,1]，当前 {self.min_consecutive_ratio}")
        if self.min_columns < 1 or self.min_rate_columns < 1:
            raise ValueError("min_columns / min_rate_columns 必须 ≥1")
        if self.max_terms_ratio < 1:
            raise ValueError(f"max_terms_ratio 必须 ≥1，当前 {self.max_terms_ratio}")
        if self.min_rows < 1:
            raise ValueError(f"min_rows 必须 ≥1，当前 {self.min_rows}")


@dataclass
class Spec:
    """一家公司、一份费率表的描述。由 companies/*.py 构造。"""

    company: str
    product: str
    unit_amount: int = 0            # 0 表示从 PDF 识别
    pages: Optional[List[int]] = None   # 只解析这些页；None 表示全部
    sample: Optional[dict] = None   # {"age":18,"gender":"男","term":"5年交","premium":88.1}
    expected_rows: Optional[int] = None
    min_column_rows: int = 5        # 一列至少几个数字才算数
    column_tolerance: float = 8.0
    row_tolerance: float = 4.0
    thresholds: Thresholds = field(default_factory=Thresholds)
    dims: Optional[Callable[[str], dict]] = None   # 页面文字 → 维度；由 adapter 提供
    split_blocks: Optional[Callable[[dict], list]] = None   # 一页切多块；由 adapter 提供
    notes: str = ""

    def __post_init__(self):
        # 在构造时就暴露配置错误，不要等到解析时才炸
        if not self.company or not self.product:
            raise ValueError("company 和 product 不能为空")
        if self.unit_amount < 0:
            raise ValueError(f"unit_amount 不能为负，当前 {self.unit_amount}")
        if self.column_tolerance <= 0:
            raise ValueError(f"column_tolerance 必须 > 0，当前 {self.column_tolerance}")
        if self.row_tolerance <= 0:
            raise ValueError(f"row_tolerance 必须 > 0，当前 {self.row_tolerance}")
        if self.min_column_rows < 1:
            raise ValueError(f"min_column_rows 必须 ≥1，当前 {self.min_column_rows}")

        if self.pages is not None:
            if not self.pages:
                raise ValueError("pages 为空列表；表示“全部页”请用 None")
            if any(page < 1 for page in self.pages):
                raise ValueError(f"pages 必须从 1 开始，当前 {self.pages}")

        if self.sample is not None:
            missing = {"age", "term", "premium"} - set(self.sample)
            if missing:
                raise ValueError(f"sample 缺少字段：{sorted(missing)}")
            if not isinstance(self.sample["age"], int) or self.sample["age"] < 0:
                raise ValueError(f"sample.age 必须是非负整数，当前 {self.sample['age']!r}")
            if not isinstance(self.sample["premium"], (int, float)):
                raise ValueError(f"sample.premium 必须是数字，当前 {self.sample['premium']!r}")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- 读取

def read_pages(pdf_path: Path) -> list:
    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            pages.append(
                {
                    "no": number,
                    "width": round(float(page.width), 1),
                    "height": round(float(page.height), 1),
                    "words": page.extract_words(extra_attrs=["size"], keep_blank_chars=False),
                    "text": page.extract_text() or "",
                }
            )
    return pages


# ---------------------------------------------------------------- 表头

def detect_unit(text: str) -> tuple:
    for pattern in UNIT_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(1)
            if raw in ("千", "万"):
                return (1000 if raw == "千" else 10000), match.group(0)
            digits = re.sub(r"[,，]", "", raw)
            if digits.isdigit() and int(digits) > 0:
                return int(digits), match.group(0)
    return 0, ""


def find_terms(words: list) -> List[dict]:
    """交费期表头。PDF 常把 "10年交" 切成 "10" + "年交"，这里按坐标就近合并。

    合并必须双向找："年交" 有时排在数字之前（基线不完全对齐），只看后一个词会漏。
    """
    tokens = []
    year_words = [word for word in words if word["text"].strip() == "年交"]

    for word in words:
        text = word["text"].strip()
        match = TERM_RE.match(text)
        if match:
            tokens.append({"text": text, "years": int(match.group(1)), "x": (word["x0"] + word["x1"]) / 2})
            continue
        if text in ONE_TIME_TERMS:
            tokens.append({"text": text, "years": 0, "x": (word["x0"] + word["x1"]) / 2})
            continue
        if not text.isdigit():
            continue

        partner = None
        for year_word in year_words:
            if (
                abs(year_word["top"] - word["top"]) <= 8
                and -4 <= year_word["x0"] - word["x1"] <= 10
            ):
                partner = year_word
                break
        if partner:
            tokens.append(
                {"text": f"{text}年交", "years": int(text), "x": (word["x0"] + partner["x1"]) / 2}
            )

    return tokens


def find_genders(words: list) -> list:
    return [
        {"text": word["text"].strip(), "x": (word["x0"] + word["x1"]) / 2}
        for word in words
        if word["text"].strip() in GENDERS
    ]


def normalize_gender(text: str) -> str:
    return "男" if text in ("男", "男性") else "女" if text in ("女", "女性") else text


def nearest(tokens: list, x: float):
    if not tokens:
        return None
    return min(tokens, key=lambda token: abs(token["x"] - x))


# ---------------------------------------------------------------- 网格

def is_age_sequence(values: list, thresholds: Thresholds) -> bool:
    if len(values) < thresholds.min_age_values:
        return False
    if any(not value.isdigit() for value in values):
        return False
    ints = [int(value) for value in values]
    if ints[0] < 0 or ints[-1] > MAX_AGE:
        return False
    if ints[-1] - ints[0] < thresholds.min_age_span:
        return False
    diffs = [b - a for a, b in zip(ints, ints[1:])]
    if not diffs:
        return False
    good = sum(1 for diff in diffs if 1 <= diff <= thresholds.max_age_gap)
    return good / len(diffs) >= thresholds.min_consecutive_ratio


def build_rows(page: dict, terms: list, genders: list, spec: Spec):
    numbers = [w for w in page["words"] if NUM_RE.match(w["text"].strip())]
    if len(numbers) < MIN_NUMBERS_PER_PAGE:
        return [], f"数字词 {len(numbers)} < {MIN_NUMBERS_PER_PAGE}"

    columns = []
    for word in sorted(numbers, key=lambda w: (w["x0"], w["top"])):
        if columns and abs(word["x0"] - columns[-1]["x"]) <= spec.column_tolerance:
            columns[-1]["items"].append(word)
        else:
            columns.append({"x": word["x0"], "items": [word]})

    columns = [column for column in columns if len(column["items"]) >= spec.min_column_rows]
    # 列内按 y 排序：数字位数不同会让 x0 有细微差异，插入顺序可能不是阅读顺序
    for column in columns:
        column["items"].sort(key=lambda word: word["top"])
    if len(columns) < spec.thresholds.min_columns:
        return [], f"过滤后只剩 {len(columns)} 列 < {spec.thresholds.min_columns}"

    age_columns = [
        index for index, column in enumerate(columns)
        if is_age_sequence([word["text"] for word in column["items"]], spec.thresholds)
    ]
    if not age_columns:
        return [], "没有识别到年龄列"

    rate_columns = [index for index in range(len(columns)) if index not in age_columns]
    if len(rate_columns) < spec.thresholds.min_rate_columns:
        return [], f"费率列只有 {len(rate_columns)} 列 < {spec.thresholds.min_rate_columns}"
    if terms and len(terms) > spec.thresholds.max_terms_ratio * len(rate_columns):
        return [], f"表头交费期 {len(terms)} 个，与 {len(rate_columns)} 个费率列不匹配"

    entries = []
    for index, column in enumerate(columns):
        for word in column["items"]:
            entries.append((word["top"], index, word["text"]))
    entries.sort(key=lambda item: item[0])

    rows = []
    current = {}
    anchor = None
    for top, index, text in entries:
        if anchor is None or abs(top - anchor) <= spec.row_tolerance:
            current.setdefault(index, text)
            if anchor is None:
                anchor = top
        else:
            rows.append(current)
            current = {index: text}
            anchor = top
    if current:
        rows.append(current)

    built = []
    for index in rate_columns:
        left = [age_index for age_index in age_columns if age_index < index]
        age_index = max(left) if left else min(age_columns)
        gender = nearest(genders, columns[index]["x"])
        term = nearest(terms, columns[index]["x"])
        for row in rows:
            age_text = row.get(age_index)
            if age_text is None or not age_text.isdigit():
                continue
            premium = parse_number(row.get(index))
            if premium is None:
                continue
            built.append(
                {
                    "page": page["no"],
                    "age": int(age_text),
                    "gender": normalize_gender(gender["text"]) if gender else "",
                    "pay_term": term["text"] if term else "",
                    "pay_term_years": term["years"] if term else None,
                    "premium": premium,
                }
            )

    return built, ""


def parse_number(text) -> Optional[float]:
    try:
        return float(str(text).replace(",", ""))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- 校验

def validate(records: list, spec: Spec, warnings: list) -> list:
    errors = []

    seen = set()
    for record in records:
        key = (record["plan"], record["coverage"], record["rate_class"],
               record["gender"], record["pay_term"], record["age"])
        if key in seen:
            warnings.append(f"重复记录：{key}")
        seen.add(key)

    groups = {}
    for record in records:
        key = (record["plan"], record["coverage"], record["rate_class"], record["gender"], record["pay_term"])
        groups.setdefault(key, set()).add(record["age"])

    for key, ages in groups.items():
        values = sorted(ages)
        missing = (values[-1] - values[0] + 1) - len(values)
        if missing > 2:
            warnings.append(f"年龄不连续：{key} 缺 {missing} 个")

    for record in records:
        if record["premium"] <= 0:
            errors.append(f"非正数费率：第{record['page']}页 {record['age']}岁 {record['gender']}{record['term']}")

    if spec.sample:
        sample = spec.sample
        matches = [
            record for record in records
            if record["age"] == sample["age"]
            and record["gender"] == sample.get("gender", record["gender"])
            and record["pay_term"] == sample["term"]
        ]
        if not matches:
            errors.append(f"抽样断言找不到对应行：{sample}")
        elif abs(matches[0]["premium"] - sample["premium"]) > 1e-9:
            errors.append(
                f"抽样断言不符：{sample}，实际 {matches[0]['premium']}（第{matches[0]['page']}页）"
            )

    if spec.expected_rows and len(records) != spec.expected_rows:
        warnings.append(f"行数与预期不符：预期 {spec.expected_rows}，实际 {len(records)}")

    return errors


# ---------------------------------------------------------------- 输出

def write_outputs(doc_dir: Path, stem: str, pdf_path: Path, digest: str, records: list,
                  unit: int, unit_evidence: str, page_log: list, errors: list,
                  warnings: list, total_pages: int, spec: Spec):
    doc_dir.mkdir(parents=True, exist_ok=True)

    long_rows = sorted(
        records,
        key=lambda r: (r["plan"], r["coverage"], r["rate_class"], r["gender"],
                       r["pay_term_years"] if r["pay_term_years"] is not None else -1, r["age"]),
    )
    headers = ["plan", "coverage", "rate_class", "gender", "age", "pay_term", "pay_term_years",
               "premium", "unit_amount", "premium_per_10000", "page"]
    lines = [",".join(headers)]
    for record in long_rows:
        lines.append(",".join(str(record.get(key, "")) for key in headers))
    write_text(doc_dir / "rates_long.csv", "\n".join(lines) + "\n")

    wide = {}
    columns = []
    for record in records:
        label = f"{record['gender']}_{record['pay_term']}" if record["gender"] else record["pay_term"]
        if label not in columns:
            columns.append(label)
        key = (record["plan"], record["coverage"], record["rate_class"], record["age"])
        wide.setdefault(key, {})[label] = record["premium_per_10000"]

    wide_headers = ["plan", "coverage", "rate_class", "age"] + columns
    wide_lines = [",".join(wide_headers)]
    for key in sorted(wide, key=lambda item: (item[0], item[1], item[2], item[3])):
        wide_lines.append(",".join(str(value) for value in list(key) + [wide[key].get(column, "") for column in columns]))
    write_text(doc_dir / "rates_wide.csv", "\n".join(wide_lines) + "\n")

    meta = {
        "source": {"file": pdf_path.name, "sha256": digest, "bytes": pdf_path.stat().st_size, "pages": total_pages},
        "company": {"name": spec.company, "product": spec.product},
        "unit": {"amount": unit, "evidence": unit_evidence},
        "parser": {"name": PARSER_NAME,
                   "parsed_at": datetime.now().astimezone().isoformat(timespec="seconds")},
        "spec": {"notes": spec.notes, "pages": spec.pages, "sample": spec.sample},
        "stats": {
            "records": len(records),
            "parsed_pages": sum(1 for item in page_log if item["status"] == "parsed"),
            "skipped_pages": sum(1 for item in page_log if item["status"] == "skipped"),
        },
        "pages": page_log,
    }
    write_json(doc_dir / "meta.json", meta)

    lines = [f"# 校验 · {stem}", ""]
    lines.append(f"- 源文件：`{pdf_path.name}`")
    lines.append(f"- 公司/产品：{spec.company} / {spec.product}")
    lines.append(f"- 单位：每 {unit} 元基本保险金额（依据：{unit_evidence or '未识别'}）")
    lines.append(f"- 解析页：{meta['stats']['parsed_pages']}，跳过页：{meta['stats']['skipped_pages']}")
    lines.append(f"- 记录数：{len(records)}")
    if spec.notes:
        lines.append(f"- 备注：{spec.notes}")
    lines.append("")
    lines.append("## 逐页")
    lines.append("")
    lines.append("| 页 | 状态 | 说明 |")
    lines.append("|---:|---|---|")
    for item in page_log:
        lines.append(f"| {item['page']} | {item['status']} | {item.get('reason') or str(item.get('rows', '')) + ' 行'} |")
    lines.append("")
    lines.append("## 错误")
    lines.append("")
    lines.extend([f"- {item}" for item in errors] or ["- 无"])
    lines.append("")
    lines.append("## 警告")
    lines.append("")
    lines.extend([f"- {item}" for item in warnings] or ["- 无"])
    write_text(doc_dir / "validation.md", "\n".join(lines) + "\n")


# ---------------------------------------------------------------- 主流程

def parse(pdf_path: Path, spec: Spec, out_dir: Path) -> dict:
    # 不做结果缓存：每次都重新解析，产物只由本次输入决定。
    # sha256 只写进 meta 作为溯源证据，不参与任何“跳过”判断。
    digest = sha256_of(pdf_path)
    stem = pdf_path.stem
    doc_dir = out_dir / stem

    pages = read_pages(pdf_path)
    total_chars = sum(len(page["text"].strip()) for page in pages)
    if total_chars < MIN_TEXT_CHARS:
        return {"file": pdf_path.name, "status": "failed",
                "reason": f"没有文字层（全文 {total_chars} 字符 < {MIN_TEXT_CHARS}）"}

    unit, unit_evidence = detect_unit("\n".join(page["text"] for page in pages))
    if spec.unit_amount and unit and spec.unit_amount != unit:
        return {"file": pdf_path.name, "status": "failed",
                "reason": f"单位冲突：spec={spec.unit_amount}，PDF={unit}（{unit_evidence}）"}
    unit = unit or spec.unit_amount

    terms, genders = [], []
    dims = {"plan": "", "coverage": "", "rate_class": ""}
    records, page_log, warnings = [], [], []

    for page in pages:
        if spec.pages and page["no"] not in spec.pages:
            page_log.append({"page": page["no"], "status": "skipped", "reason": "不在 spec 页范围"})
            continue

        page_rows = []
        last_reason = ""

        if spec.split_blocks:
            blocks = spec.split_blocks(page)
        else:
            blocks = [{"words": page["words"], "text": page["text"]}]

        for block in blocks:
            block_terms = find_terms(block["words"])
            block_genders = find_genders(block["words"])
            if block_terms:
                terms = block_terms
            if block_genders:
                genders = block_genders

            if spec.dims:
                for key, value in spec.dims(block["text"]).items():
                    if value:
                        dims[key] = value

            if not terms or not genders:
                last_reason = "没有表头"
                continue

            rows, reason = build_rows(
                {"no": page["no"], "words": block["words"]}, terms, genders, spec
            )
            if len(rows) < spec.thresholds.min_rows:
                last_reason = reason or f"有效行 {len(rows)} < 阈值 {spec.thresholds.min_rows}"
                continue

            snapshot = {"plan": dims["plan"], "coverage": dims["coverage"], "rate_class": dims["rate_class"]}
            for row in rows:
                row.update(snapshot)
            page_rows.extend(rows)

        if not page_rows:
            page_log.append({"page": page["no"], "status": "skipped",
                             "reason": last_reason or "没有解析出费率行"})
            continue
        records.extend(page_rows)
        page_log.append({"page": page["no"], "status": "parsed", "rows": len(page_rows)})

    if not records:
        return {"file": pdf_path.name, "status": "failed", "reason": "没有解析出任何费率行"}
    if not unit:
        return {"file": pdf_path.name, "status": "failed", "reason": "识别不到保额单位"}

    for record in records:
        record["unit_amount"] = unit
        record["premium_per_10000"] = round(record["premium"] * 10000 / unit, 4)

    errors = validate(records, spec, warnings)
    write_outputs(doc_dir, stem, pdf_path, digest, records, unit, unit_evidence,
                  page_log, errors, warnings, len(pages), spec)

    return {
        "file": pdf_path.name,
        "status": "ok" if not errors else "warning",
        "rows": len(records),
        "parsed_pages": sum(1 for item in page_log if item["status"] == "parsed"),
        "skipped_pages": sum(1 for item in page_log if item["status"] == "skipped"),
        "unit": unit,
        "errors": len(errors),
    }
