"""阶段 2：抽取——把快照里的字段解析成结构化 JSON。

只做"抄录 + 定位"，不做推断。抽不到的字段留 null 并记录到 gaps。

用法：
    python 04_extract.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import DATA, HTML, TEXT, decode_bytes, log, strip_tags, today  # noqa: E402

NUM = r"([\d.]+)\s*%"


def pick(text: str, pattern: str, flags: int = 0) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def parse_jbgk(text: str) -> dict:
    """基本概况页。"""
    d: dict = {}
    d["full_name"] = pick(text, r"基金全称\s*(.+?)\s*基金简称")
    d["short_name"] = pick(text, r"基金简称\s*(.+?)\s*基金代码")
    d["code"] = pick(text, r"基金代码\s*(\d{6})")
    d["fund_type"] = pick(text, r"基金类型\s*(.+?)\s*发行日期")
    d["inception"] = pick(text, r"成立日期/规模\s*(\d{4}年\d{2}月\d{2}日)")
    d["inception_shares"] = pick(text, r"成立日期/规模\s*\d{4}年\d{2}月\d{2}日\s*/\s*([\d.]+亿份)")
    d["net_assets"] = pick(text, r"净资产规模\s*([\d.]+亿元)")
    d["net_assets_asof"] = pick(text, r"净资产规模.*?截止至[：:]\s*(\d{4}年\d{2}月\d{2}日)")
    d["shares"] = pick(text, r"份额规模\s*([\d.]+亿份)")
    d["manager_company"] = pick(text, r"基金管理人\s*(.+?)\s*基金托管人")
    d["custodian"] = pick(text, r"基金托管人\s*(.+?)\s*基金经理")
    d["fund_manager"] = pick(text, r"基金经理人\s*(.+?)\s*成立来分红")
    d["mgmt_fee"] = pick(text, r"管理费率\s*" + NUM)
    d["custody_fee"] = pick(text, r"托管费率\s*" + NUM)
    svc = pick(text, r"销售服务费率\s*(---|[\d.]+%)")
    d["sales_service_fee"] = None if svc in (None, "---") else svc
    d["benchmark"] = pick(text, r"业绩比较基准\s*(.+?)\s*跟踪标的")
    d["track_index"] = pick(text, r"跟踪标的\s*(\S+?)\s*◆")
    d["investment_scope"] = pick(text, r"投资范围\s*(.+?)\s*投资策略")
    d["investment_strategy"] = pick(text, r"投资策略\s*(.+?)\s*风险收益特征|投资策略\s*(.+?)$", re.S)
    if isinstance(d["investment_strategy"], tuple):
        d["investment_strategy"] = None
    return d


def parse_ladder(text: str, start: str, end: str) -> list[dict]:
    """解析费率阶梯表（从 start 到 end 之间的纯文本）。"""
    i = text.find(start)
    if i < 0:
        return []
    j = text.find(end, i + len(start))
    block = text[i + len(start) : j if j > 0 else i + 800]
    rows = []
    for m in re.finditer(
        r"((?:小于|大于等于)[^ ]+?[元天年](?:，[^ ]+?[元天年])?|每笔[^ ]+?元)"
        r"\s+([\d.]+%|每笔[\d]+元)"
        r"(?:\s*\|\s*([\d.]+%))?",
        block,
    ):
        rows.append(
            {
                "range": m.group(1),
                "rate": m.group(2),
                "discounted": m.group(3),
            }
        )
    return rows


def parse_jjfl(text: str) -> dict:
    d = {}
    d["purchase_ladder"] = parse_ladder(text, "申购费率", "赎回费率")
    d["redeem_ladder"] = parse_ladder(text, "赎回费率", "友情提示")
    if not d["redeem_ladder"]:
        d["redeem_ladder"] = parse_ladder(text, "赎回费率", "注：")
    d["no_data"] = "暂无数据" in text[:4000]
    return d


def main() -> None:
    src = sorted(HTML.glob(f"{today()}_*.html"))
    if not src:
        log("no snapshots found; run 01_discover.py first")
        return

    out: dict[str, dict] = {}
    for p in src:
        m = re.match(r"(\d{8})_(\d{6})_(\w+)\.html", p.name)
        if not m:
            continue
        _, code, page = m.groups()
        text = strip_tags(decode_bytes(p.read_bytes()))
        (TEXT / f"{code}_{page}.txt").write_text(text, encoding="utf-8")
        rec = out.setdefault(code, {"code": code})
        if page == "jbgk":
            rec.update(parse_jbgk(text))
        elif page == "jjfl":
            rec.update(parse_jjfl(text))

    path = DATA / "extracted.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    for code, r in out.items():
        log(
            f"{code} {r.get('short_name','?'):<22} "
            f"管理{r.get('mgmt_fee') or '-':>6} 托管{r.get('custody_fee') or '-':>6} "
            f"销售{r.get('sales_service_fee') or '-':>6} 申购档{len(r.get('purchase_ladder',[]))} "
            f"赎回档{len(r.get('redeem_ladder',[]))}"
        )
    log(f"extracted {len(out)} funds -> {path}")


if __name__ == "__main__":
    main()
