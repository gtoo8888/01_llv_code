# DeepSeek 对话合并工具

## 概述

`scripts/merge_conversations.py` 是一个离线工具，用于将多个 DeepSeek 导出的 JSON 对话文件合并为一个文件，自动去重并按时间排序。

### 为什么需要这个工具？

当你从不同时间点导出了多份 DeepSeek 对话文件时（例如 `deepseek_data-2026-03-14` 和 `deepseek_data-2026-06-19`），它们之间存在重叠的对话。解析工具 `deepseek_parser.py` 一次只能指向一个数据源，手动切换不便。本工具将这些文件合并成一个完整的数据集，方便统一管理和解析。

---

## 使用方法

### 前置条件

脚本仅使用 Python 标准库，无额外依赖：

```bash
conda activate llm_chat_dashboard
```

在 `pro5/` 项目根目录下执行。

### 运行合并

```bash
python scripts/merge_conversations.py
```

### 输出示例

```
============================================================
  DeepSeek 对话合并工具
============================================================

  📂 加载: conversations.json  (33.0 MB)  → 512 个对话
  📂 加载: conversations.json  (35.2 MB)  → 487 个对话

  📊 合并前总数: 999
  🔁 去重移除: 23 条重复
  ✅ 合并后总数: 976
  📅 时间范围: 2025-01-03 → 2026-06-19

  💾 写入: llm_sessions/deepseek_data-merged/conversations.json  (62.8 MB)
  ⏱  耗时: 4.2 秒

  💡 在 deepseek_parser.py 中将 JSON_FILE 改为:
     JSON_FILE = "llm_sessions/deepseek_data-merged/conversations.json"
```

---

## 合并策略

### 1. 加载

依次读取 `SOURCE_FILES` 列表中的所有 JSON 文件，逐个输出加载进度。

### 2. 去重

以对话 `id` 字段为唯一标识：

- 同 ID 出现多次 → 保留 `updated_at` **更新**的那条
- 不同 ID → 全部保留

### 3. 排序

按 `inserted_at`（创建时间）**升序**排列，确保合并后的文件从头到尾是时间顺序。

### 4. 输出

写入 `OUTPUT_DIR/conversations.json`，末尾会打印提示告知如何修改 `deepseek_parser.py` 中的 `JSON_FILE` 配置。

---

## 配置

编辑脚本顶部的 `SOURCE_FILES` 和 `OUTPUT_DIR` 变量：

```python
SOURCE_FILES = [
    "llm_sessions/deepseek_data-2026-03-14/conversations.json",
    "llm_sessions/deepseek_data-2026-06-19/conversations.json",
]
OUTPUT_DIR = "llm_sessions/deepseek_data-merged"
```

| 配置项 | 说明 |
|--------|------|
| `SOURCE_FILES` | 需要合并的 JSON 文件列表，相对于 `pro5/` 根目录 |
| `OUTPUT_DIR` | 合并后的输出目录，自动创建 `conversations.json` |

---

## 常见流程

```
原始导出 1 ─┐
             ├── merge_conversations.py ──→ deepseek_data-merged/
原始导出 2 ─┘                                    │
                                                  └── conversations.json
                                                           │
                                              deepseek_parser.py  ← 改 JSON_FILE 指向这里
```

合并完成后，更新 `deepseek_parser.py` 顶部的 `JSON_FILE` 指向合并后的文件，即可用 `list` / `view` / `export` / `status` 统一管理全部对话。

---

## 注意事项

1. **源文件不会被修改**：合并过程只读取不写入原始文件。
2. **重复条数取决于重叠程度**：如果两份导出时间接近，去重的重复数会较多。
3. **输出文件可能变大**：合并后的文件是两份数据之和减去重复，体积约等于两者之和。
4. **支持追加新文件**：要加入第三份数据，只需将其路径添加到 `SOURCE_FILES` 列表后重新运行。
