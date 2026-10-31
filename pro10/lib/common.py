"""公共工具：HTTP 抓取、编码探测、文件名、快照、manifest。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
HTML = DATA / "html"
TEXT = DATA / "text"
LOGS = ROOT / "logs"
MANIFEST = DATA / "manifest.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

DELAY = 1.5


def ensure_dirs() -> None:
    for d in (RAW, HTML, TEXT, LOGS):
        d.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / f"{datetime.now():%Y%m%d}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get(
    url: str,
    *,
    tries: int = 2,
    timeout: int = 25,
    extra_headers: dict | None = None,
    **kw,
) -> requests.Response | None:
    """GET，带重试与限速。返回 None 表示失败。"""
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    for i in range(tries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
            log(f"HTTP {r.status_code} {url}")
        except Exception as e:  # noqa: BLE001
            log(f"ERR {type(e).__name__} {url} {str(e)[:80]}")
        if i < tries:
            time.sleep(DELAY * (i + 1))
    return None


def _cjk(s: str) -> int:
    return sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")


def decode_bytes(b: bytes) -> str:
    """按"哪个解得出的汉字多"来选编码，不信任 HTTP 头。"""
    best, best_score = None, -1
    for enc in ("utf-8", "gb18030"):
        try:
            s = b.decode(enc)
        except UnicodeDecodeError:
            continue
        score = _cjk(s[:20000])
        if score > best_score:
            best, best_score = s, score
    if best is not None:
        return best
    return b.decode("utf-8", errors="replace")


def decode(r: requests.Response) -> str:
    return decode_bytes(r.content)


def strip_tags(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def load_manifest() -> list[dict]:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return []


def add_manifest(records: list[dict]) -> None:
    data = load_manifest()
    seen = {(r.get("url"), r.get("path")) for r in data}
    for rec in records:
        if (rec.get("url"), rec.get("path")) not in seen:
            data.append(rec)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def today() -> str:
    return datetime.now().strftime("%Y%m%d")


def safe_name(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", s)
    return s.strip("_")[:80]
