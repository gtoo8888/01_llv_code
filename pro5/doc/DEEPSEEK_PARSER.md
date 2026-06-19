# DeepSeek 对话解析工具

## 概述

`scripts/deepseek_parser.py` 是一个离线解析工具，用于读取 DeepSeek 官方导出的 JSON 对话文件，将其解析为可读的对话记录和结构化数据。

### 为什么需要这个工具？

DeepSeek 导出的对话文件是一个 **单行 JSON 数组**，每个元素代表一次完整的对话。文件结构是树状的（`mapping` 字段），并非线性排列，无法直接用文本编辑器或普通 JSON 查看器有效阅读。本工具的核心工作就是 **将树状结构展平为有序的对话流**。

---

## 快速入门

### 前置条件

激活 Conda 环境（脚本仅使用 Python 标准库，无额外依赖）：

```bash
conda activate llm_chat_dashboard
```

所有命令都在 `pro5/` 项目根目录下执行。

### 切换数据源

编辑脚本顶部的 `JSON_FILE` 变量：

```python
JSON_FILE = "llm_sessions/deepseek_data-merged/conversations.json"
```

输出目录名由输入文件夹名自动推导，无需额外配置。

### 查看帮助

```bash
python scripts/deepseek_parser.py --help         # 总帮助
python scripts/deepseek_parser.py export --help   # 子命令帮助
```

---

## 命令参考

### `list` — 列出所有对话

```bash
python scripts/deepseek_parser.py list
```

```
  [  1] Python类拆分与模块化设计
        ID: c26ef77a-ae7c-4759-814c-af01efd70635
        日期: 2025-01-03T11:24:41  |  消息: 4 条 (用户 2 条)  |  模型: deepseek-chat

  [  2] ubuntu 防火墙放行端口情况怎么看？
        ID: b1e2d3f4-...
        日期: 2026-03-13T22:40:47  |  消息: 2 条 (用户 1 条)  |  模型: deepseek-reasoner
```

每行显示：
- **序号**（可用于 `view` / `export` 快速定位）
- **对话标题**
- **ID**（完整 UUID，也支持按 ID 前缀匹配）
- **时间范围**
- **消息数量**（总条数 / 用户消息条数）
- **使用的模型**

---

### `view` — 查看单个对话详情

```bash
python scripts/deepseek_parser.py view 1           # 按列表序号
python scripts/deepseek_parser.py view c26ef77a    # 按 ID 前缀
```

```
======================================================================
  Python类拆分与模块化设计
  ID: c26ef77a-...  |  2025-01-03T11:24:41 → 2025-01-03T11:28:36
  消息: 4 条  |  模型: deepseek-chat
======================================================================

────────────────────────────────────────────────────────────
  [1] 用户  |  deepseek-chat  |  2025-01-03T11:24:41
────────────────────────────────────────────────────────────

[用户发送的代码或问题内容]

────────────────────────────────────────────────────────────
  [2] Assistant  |  deepseek-chat  |  2025-01-03T11:24:43
────────────────────────────────────────────────────────────

[助手的回复内容]

── 思考过程 ──
[如果是 reasoning 模型，这里显示思考链]
```

> `THINK` 片段仅在 `deepseek-reasoner`（R1 系列）模型中出现，`deepseek-chat` 模型没有。

---

### `export` — 导出对话

```bash
python scripts/deepseek_parser.py export 1           # 导出单个对话
python scripts/deepseek_parser.py export c26ef77a    # 按 ID 前缀
python scripts/deepseek_parser.py export --top 10    # 导出前 N 条
python scripts/deepseek_parser.py export             # 导出全部（需确认）
```

导出完成显示耗时统计：

```
  ✅ 2025-01-03_Python类拆分与模块化设计.md  (4 条消息)

⏱  耗时: 0.2 秒  |  📁 共 1 个文件, 保存在: llm_conversation_archives/deepseek_data-merged/
```

全量导出时需要终端确认：

```
即将导出 2288 个对话，确认？(y/N):
```

输入 `y` 回车开始，其余输入或回车则取消。

---

### `status` — 查看对话库概览

```bash
python scripts/deepseek_parser.py status
```

```
============================================================
  DeepSeek 对话知识库 - 概览
============================================================

  📊 对话总数:       2288
  💬 消息总数:       20644（用户 10319 条）
  📅 时间跨度:       2025-01-03 → 2026-06-19
  🤖 使用的模型:     deepseek-chat, deepseek-reasoner

  ────────────────────────────────────────────────────────
  月度分布:
    2025_01: █████████ (107)
    2025_02: ███████████ (127)
    ...
    2025_11: ██████████████████████████████ (330)
    2026_06: ███████ (85)
```

方块长度按当月对话数占最高月份的**比例**缩放。

---

### `help` — 查看全部子命令

```bash
python scripts/deepseek_parser.py --help
python scripts/deepseek_parser.py export --help
python scripts/deepseek_parser.py view --help
```

---

## 输出目录结构

```
llm_conversation_archives/
└── deepseek_data-merged/                    ← 数据源名（自动推导）
    ├── _index.md                            ← ⭐ 归档根索引（全局统计 + 月度明细）
    ├── 2025/
    │   ├── 01_January/
    │   │   ├── 2025-01-03_标题.md            ← 人类可读的对话全文
    │   │   ├── _index.md                    ← 月份索引（统计 + 每日分布 + 清单）
    │   │   └── _data.json                   ← 结构化元数据（程序可读）
    │   ├── 02_February/
    │   └── ...
    └── 2026/
        └── ...
```

### 文件说明

| 文件 | 用途 | 生成方式 |
|------|------|----------|
| `_index.md`（根目录） | 全库统计总览：对话总数、消息数、模型分布、逐月明细表 | 每次导出完成后自动生成 |
| `YYYY/MM_Month/_index.md` | 月度统计：对话量、模型占比、每日对话量柱状图、对话清单 | 每次导出完成后自动刷新 |
| `YYYY/MM_Month/_data.json` | 程序可读的结构化元数据 | 每次导出后自动合并更新 |
| `YYYY-MM-DD_标题.md` | 人类可读的对话全文 | 每次导出新建或覆盖 |

### 根目录 `_index.md` 示例

```
# 📚 对话归档总览

> **数据源:** `conversations.json`
> **生成时间:** 2026-06-19 03:05:00
> **时间跨度:** 2025-01-03 → 2026-06-19

## 📊 全局统计

| 指标 | 数值 |
|------|------|
| 对话总数 | 2288 |
| 消息总数 | 20644（用户 10319 · Assistant 10325） |
| 涉及模型 | deepseek-chat(878) · deepseek-reasoner(1495) |
| 含思考过程 | 2056 条消息 |
| 输入总字符 | ~21,523,891 |
| 输出总字符 | ~62,847,203 |

## 📅 月度统计

| 月份 | 对话 | 消息 | 模型 |
|------|------|------|------|
| 2025 **合计** | 1595 | 12062 | deepseek-chat(876) · deepseek-reasoner(803) |
| 2025/01_January | 107 | 856 | deepseek-chat(80) · deepseek-reasoner(27) |
| ... | ... | ... | ... |
```

### 月份 `_index.md` 示例

```
# 月度对话索引 — 2025年1月 (January)

## 📊 统计概览

| 指标 | 数值 |
|------|------|
| 对话总数 | 18 |
| 消息总数 | 156（用户 72 · Assistant 84） |
| 时间跨度 | 2025-01-03 → 2025-01-31 |
| 涉及模型 | deepseek-chat(15) · deepseek-reasoner(3) |
| 含思考过程 | 12 条消息 |

## 📅 每日对话量

  03日: ████████████████████ (5)
  05日: ████████ (2)
  ...

## 📋 对话清单

- **[Python类拆分与模块化设计](2025-01-03_xxx.md)**  _2025-01-03_  ·  4 条消息  ·  deepseek-chat
```

### `_data.json` 结构

```json
[
  {
    "id": "c26ef77a-...",
    "title": "Python类拆分与模块化设计",
    "inserted_at": "2025-01-03T11:24:41",
    "updated_at": "2025-01-03T11:28:36",
    "message_count": 4,
    "user_message_count": 2,
    "models": ["deepseek-chat"],
    "messages": [
      { "role": "user", "model": "deepseek-chat", "request_length": 256 },
      { "role": "assistant", "model": "deepseek-chat", "response_length": 512, "has_thinking": false }
    ]
  }
]
```

---

## 日志

屏幕输出的内容同时写入日志文件：

| 输出目标 | 格式 | 位置 |
|---------|------|------|
| 屏幕 (stderr) | 纯消息文本 | 终端可见 |
| 文件 | `时间 [级别] 消息` | `scripts/deepseek_parser.log` |

---

## 配套工具

### 合并对话 — `scripts/merge_conversations.py`

将多个 DeepSeek 导出文件合并为一个，自动去重并按时间排序：

```bash
conda activate llm_chat_dashboard
python scripts/merge_conversations.py
```

合并策略：
- 同 ID 对话保留 `updated_at` 更新的那条
- 按 `inserted_at` 升序排列
- 输出到 `llm_sessions/deepseek_data-merged/conversations.json`

修改 `SOURCE_FILES` 列表可配置源文件路径。

---

## 解析原理

### 一、源数据格式

```json
[
  {
    "id": "对话唯一ID",
    "title": "对话标题",
    "inserted_at": "创建时间",
    "updated_at": "更新时间",
    "mapping": {
      "root": { "id": "root", "children": ["消息ID"] },
      "消息节点ID": {
        "id": "...", "parent": "...", "children": ["回复ID"],
        "message": {
          "model": "模型名称",
          "inserted_at": "时间戳",
          "fragments": [
            { "type": "REQUEST",  "content": "用户说的内容..." },
            { "type": "THINK",    "content": "模型思考过程..." },
            { "type": "RESPONSE", "content": "模型回复内容..." }
          ]
        }
      }
    }
  }
]
```

### 二、Fragment 类型

| type | 含义 | 出现条件 |
|------|------|----------|
| `REQUEST` | 用户消息 | 用户发言中必然出现 |
| `THINK` | 模型思考链 | 仅 `deepseek-reasoner` |
| `RESPONSE` | 模型回复 | Assistant 消息中必然出现 |

### 三、核心算法：树 → 线性对话流

`linearize_messages()` 使用深度优先遍历（DFS）将 `mapping` 树展平：

```
root → msg_1 (用户) → msg_2 (Assistant) → msg_3 (用户) → msg_4 (Assistant)

遍历结果: [msg_1, msg_2, msg_3, msg_4]  ← 阅读顺序
```

### 四、消息角色判定

- 包含 `type: "REQUEST"` 的片段 → **用户消息**
- 否则 → **Assistant 消息**

---

## 注意事项

1. **文件路径硬编码**：`JSON_FILE` 配置在脚本顶部，切换数据源时修改此变量。
2. **输出目录自动推导**：路径名由输入文件夹名自动生成。
3. **全量导出耗时长**：数千条对话可能需要数分钟，建议先用 `--top N` 测试。
4. **导出按 ID 覆盖**：相同 ID 重新导出时自动更新，不产生重复。
5. **日志文件**：位于 `scripts/deepseek_parser.log`，可排查运行时问题。
