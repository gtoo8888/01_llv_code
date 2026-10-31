#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""01_pdf 的文本 IO 边界。

项目里所有文本读写都走这里，上层不再直接调用 `read_text` / `write_text` / `open`。
encoding 与换行符只在这一个文件里保证，规则见 README.md。

- 读：默认 `utf-8-sig`，能同时吃下带 BOM 和不带 BOM 的 UTF-8，
  不会在首字符留下 `\\ufeff`。
- 写：默认 `utf-8` + `newline="\\n"`，Windows 上不会自动变成 CRLF，
  保证同一份输入在不同平台上写出的字节一致。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

READ_ENCODING = "utf-8-sig"
WRITE_ENCODING = "utf-8"


def read_text(path: Path, encoding: str = READ_ENCODING) -> str:
    return Path(path).read_text(encoding=encoding)


def write_text(path: Path, text: str, encoding: str = WRITE_ENCODING) -> None:
    # newline="\n" 关闭 Windows 的换行翻译，写出结果与平台无关
    with open(str(path), "w", encoding=encoding, newline="\n") as handle:
        handle.write(text)


def read_json(path: Path, encoding: str = READ_ENCODING) -> Any:
    return json.loads(read_text(path, encoding=encoding))


def write_json(path: Path, data: Any, encoding: str = WRITE_ENCODING) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding=encoding)
