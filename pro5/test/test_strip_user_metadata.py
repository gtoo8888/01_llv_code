#!/usr/bin/env python3
"""
单元测试：strip_user_metadata 函数
"""
import pytest
import sys

sys.path.insert(0, __file__.rsplit('/test/', 1)[0])

from app import strip_user_metadata


class TestStripUserMetadata:
    def test_timestamp_followed_by_user_message(self):
        content = """Sender (untrusted metadata):
```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui"
}
```

[Thu 2026-04-02 01:02 GMT+8] 关注珀莱雅,2026年4月22号发布年报"""
        result = strip_user_metadata(content)
        assert "System:" not in result

    def test_timestamp_followed_by_multiline_user_message(self):
        content = """Sender (untrusted metadata):
```json
{
  "label": "openclaw-control-ui",
  "id": "openclaw-control-ui"
}
```

[Thu 2026-04-02 01:02 GMT+8] 关注珀莱雅,2026年4月22号发布年报
testes"""
        result = strip_user_metadata(content)
        assert "System:" not in result
