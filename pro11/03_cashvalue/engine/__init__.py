# -*- coding: utf-8 -*-
"""03_cashvalue 的解析引擎。

这里刻意**不做聚合导入**（不写 `from .pipeline import parse`）：
否则 adapter 只要 `from engine.spec import Spec`，就会把 pipeline 连同
pypdfium2 一起加载，拆 spec 的意义就没了。

调用方请写全路径：
    from engine.spec import Spec
    from engine.pipeline import parse
"""
