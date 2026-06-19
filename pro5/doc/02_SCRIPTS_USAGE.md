# 脚本使用指南

本文档汇总 `pro5/scripts/` 下所有离线工具的用途和使用方法。

---

## deepseek_parser.py — DeepSeek 对话解析工具

解析 DeepSeek 官方导出的 JSON 对话文件，将树状结构展平为可读的对话流并导出为 Markdown。

### 为什么需要这个工具？

DeepSeek 导出的对话文件是一个 **单行 JSON 数组**，每个元素代表一次完整的对话。文件结构是树状的（`mapping` 字段），无法直接用文本编辑器阅读。本工具将树状结构展平为有序的对话流。

### 前置条件

```bash
conda activate llm_chat_dashboard
```

所有命令在 `pro5/` 项目根目录下执行。

### 切换数据源

编辑脚本顶部的 `JSON_FILE` 变量：

```python
JSON_FILE = "llm_sessions/deepseek_data-merged/conversations.json"
```

输出目录名由输入文件夹名自动推导。

### 命令参考

#### `list` — 列出所有对话

```bash
python scripts/deepseek_parser.py list
```

显示：序号、对话标题、ID、时间范围、消息数量、模型。

#### `view` — 查看单个对话详情

```bash
python scripts/deepseek_parser.py view 1           # 按列表序号
python scripts/deepseek_parser.py view c26ef77a    # 按 ID 前缀
```

#### `export` — 导出对话

```bash
python scripts/deepseek_parser.py export 1           # 单个
python scripts/deepseek_parser.py export --top 10    # 前 N 条
python scripts/deepseek_parser.py export             # 全部（需确认）
```

#### `status` — 查看对话库概览

```bash
python scripts/deepseek_parser.py status
```

显示：对话总数、消息总数、时间跨度、模型分布、月度分布。

#### `help` — 查看全部子命令

```bash
python scripts/deepseek_parser.py --help
python scripts/deepseek_parser.py export --help
```

### 输出目录结构

```
llm_conversation_archives/
└── deepseek_data-merged/
    ├── _index.md                      # 根索引：全局统计 + 月度明细
    ├── 2025/
    │   ├── 01_January/
    │   │   ├── 2025-01-03_标题.md     # 人类可读的对话全文
    │   │   ├── _index.md              # 月份索引
    │   │   └── _data.json             # 结构化元数据
    │   └── ...
    └── 2026/
        └── ...
```

### 输出文件说明

| 文件 | 用途 |
|------|------|
| `_index.md`（根目录） | 全库统计总览：对话总数、消息数、模型分布、逐月明细表 |
| `YYYY/MM_Month/_index.md` | 月度统计：对话量、模型占比、每日对话量柱状图、对话清单 |
| `YYYY/MM_Month/_data.json` | 程序可读的结构化元数据 |
| `YYYY-MM-DD_标题.md` | 人类可读的对话全文 |

### 日志

屏幕输出同时写入 `scripts/deepseek_parser.log`。

---

## merge_conversations.py — 对话合并工具

将多个 DeepSeek 导出文件合并为一个，自动去重并按时间排序。

### 为什么需要这个工具？

多次导出的 DeepSeek 对话文件间存在重叠，手动切换数据源不便。本工具将它们合并成一个完整的数据集。

### 运行合并

```bash
conda activate llm_chat_dashboard
python scripts/merge_conversations.py
```

### 合并策略

| 步骤 | 说明 |
|------|------|
| 加载 | 依次读取 `SOURCE_FILES` 列表中的 JSON 文件 |
| 去重 | 同 ID 保留 `updated_at` 更新的那条 |
| 排序 | 按 `inserted_at` 升序排列 |
| 输出 | 写入 `OUTPUT_DIR/conversations.json` |

### 配置

编辑脚本顶部变量：

```python
SOURCE_FILES = [
    "llm_sessions/deepseek_data-2026-03-14/conversations.json",
    "llm_sessions/deepseek_data-2026-06-19/conversations.json",
]
OUTPUT_DIR = "llm_sessions/deepseek_data-merged"
```

### 常见流程

```
原始导出 1 ─┐
             ├── merge_conversations.py ──→ deepseek_data-merged/
原始导出 2 ─┘                                    │
                                                  └── conversations.json
                                                           │
                                              deepseek_parser.py  ← 改 JSON_FILE 指向这里
```

### 注意事项

- 源文件不会被修改
- 支持追加新文件：路径添加到 `SOURCE_FILES` 后重跑

---

## parse_conversations.py — OpenClaw JSONL 解析器

**Step 1: JSONL Parser** — 解析 OpenClaw 导出的 JSONL 对话文件，构建可读的对话结构并存入 SQLite 数据库。

### 功能

- 逐行解析 JSONL 事件流（session / message / toolCall 等）
- 提取文本内容、思考过程、工具调用、Token 用量
- 自动关联 toolCall 与 toolResult
- 输出到三种存储：SQLite 数据库、JSON 全量导出、Markdown 可读导出

### 前置条件

```bash
conda activate llm_chat_dashboard
```

### 配置（编辑脚本顶部）

```python
DB_PATH = ".../pro5/database.db"                     # SQLite 输出
JSON_OUTPUT = ".../pro5/data/parsed/all_conversations.json"   # JSON 导出
MD_OUTPUT = ".../pro5/data/parsed/all_conversations.md"      # Markdown 导出
SOURCE_FILE = ".../xxx.jsonl"                        # 输入 JSONL 文件
LIMIT = None                                         # None=全量解析
```

### 运行

```bash
python scripts/parse_conversations.py
```

### 输出

| 输出 | 格式 | 说明 |
|------|------|------|
| SQLite | `database.db` | 三张表：sessions / messages / tool_calls |
| JSON | `data/parsed/all_conversations.json` | 按 session 分组，消息按时间排序，含完整元数据 |
| Markdown | `data/parsed/all_conversations.md` | 人类可读格式，含 tool_calls 和 thinking |

---

## parse_sample.py — JSONL 解析测试脚本

**Step 0** — 在正式解析前运行，解析 JSONL 前 30 条记录并打印输出，用于确认数据格式理解是否正确。

### 运行

```bash
python scripts/parse_sample.py
```

### 输出示例

```
type: session   | id: abc...  | parent: -   | ts: 2026-03-10T13:04:06Z
  → 新会话开始 (cwd=/home/...)

type: message   | id: def...  | parent: abc... | ts: 2026-03-10T13:04:06Z
  → 角色: user
  → 模型: deepseek-chat (openai)
  → Token: input=100, output=0, total=100
  → 内容预览: 你今天的任务是什么...
```

支持的事件类型：`session`、`message`、`model_change`、`thinking_level_change`、`custom`。

---

## deepseek_conversation_topic_classifier.py — 对话批量分类

为全部 DeepSeek 对话打上主题标签（1~2 个），生成按主题分组的索引。

### 使用方式

```bash
# 全量分类
python scripts/deepseek_conversation_topic_classifier.py

# 测试：仅处理指定月份
python scripts/deepseek_conversation_topic_classifier.py --months 2026/05

# 快速验证：限制文件数
python scripts/deepseek_conversation_topic_classifier.py --max-files 20
```

### 输出物

| 文件 | 格式 | 用途 |
|------|------|------|
| `output/category_summary.csv` | CSV | 各分类对话数概览 |
| `output/topic_index.md` | Markdown | 带编号层级结构的对话列表 |
| `output/score_log.csv` | CSV | 每条对话在每个分类的得分明细 |
| `output/unmatched_words.csv` | CSV | 待分类对话的高频词，反哺映射表 |
| `output/manual_tags.json` | JSON | 手工修正标签，优先于自动分类 |

> 分类系统的完整设计见 [`03_DEVELOPMENT_HISTORY.md`](03_DEVELOPMENT_HISTORY.md) 的「对话批量分类方案」章节。

### 关键词映射表

`scripts/keyword_map.json` — 独立于脚本逻辑的配置文件，手动编辑后重跑即可生效。

---

## 脚本清单速查

| 脚本 | 输入 | 输出 | 作用 |
|------|------|------|------|
| `deepseek_parser.py` | DeepSeek JSON | Markdown 对话归档 | 展平树状结构为可读对话流 |
| `merge_conversations.py` | 多个 DeepSeek JSON | 合并后的 JSON | 去重合并多份导出 |
| `parse_conversations.py` | OpenClaw JSONL | SQLite + JSON + MD | 解析 OpenClaw 会话数据 |
| `parse_sample.py` | OpenClaw JSONL | 终端打印 | 验证数据格式的测试工具 |
| `deepseek_conversation_topic_classifier.py` | DeepSeek Markdown 归档 | CSV + Markdown 分类索引 | 自动打主题标签并生成索引 |
