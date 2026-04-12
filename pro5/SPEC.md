# 对话数据分析平台 — 项目规格文档

> 本文档是项目开发前的需求确认文档，待确认后再进入编码阶段。

---

## 一、项目概述

**项目名称：** 对话数据分析平台（Conversation Analytics）

**核心目标：** 将 OpenClaw 与大模型对话产生的原始数据，转化为人类可读的、结构化的对话记录，并提供可视化统计与搜索能力。

**当前阶段目标（v0.1）：**
- 读取 OpenClaw 原始 JSONL 数据
- 解析并转换为易读的对话格式存储
- Web 界面展示对话历史
- 支持按会话、时间、渠道筛选

**未来扩展（v0.2+）：**
- 搜索功能
- 支持其他对话平台数据接入
- 导出、分享功能

---

## 二、数据来源与格式

### 2.1 数据目录

**源目录（Read-only）：**
```
/data_sdb/openclaw/KnowledgeWorkspace/03_workspace/03_drafts/
```
用户会定期放入 JSONL 文件，格式为：
`{uuid}.jsonl.reset.{timestamp}` 或类似命名规则。

**目标存储目录（项目内）：**
```
pro5/
├── data/
│   ├── raw/              # 原始 JSONL 文件（只读，保留）
│   └── parsed/          # 解析后的对话记录（SQLite）
```

### 2.2 原始数据格式（OpenClaw JSONL）

每行是一条独立事件，事件类型有：

| `type` | 说明 | 关键字段 |
|--------|------|---------|
| `session` | 会话开始 | `id`, `timestamp`, `cwd` |
| `model_change` | 模型切换 | `modelId`, `provider`, `timestamp` |
| `thinking_level_change` | 思考级别变更 | `thinkingLevel` |
| `custom` (`model-snapshot`) | 模型快照 | `data.modelId`, `data.provider` |
| `message` | 消息 | `message.role`, `message.content[]`, `message.api`, `message.provider`, `message.model`, `message.usage`, `message.stopReason` |

**`message` 类型是核心**，其 `content` 数组包含多种元素：

- `type: "text"` — 纯文本回复
- `type: "thinking"` — AI 思考过程（推理痕迹）
- `type: "toolCall"` — 调用工具（`name`, `arguments`）
- `type: "toolResult"` — 工具返回结果

### 2.3 解析后的存储格式

SQLite 数据库表设计：

```sql
-- 会话元信息
CREATE TABLE sessions (
    session_key TEXT PRIMARY KEY,    -- 对应 JSONL 中 id
    start_time DATETIME,
    cwd TEXT,
    channel TEXT                     -- 从 session 元数据推断或留空
);

-- 消息记录
CREATE TABLE messages (
    id TEXT PRIMARY KEY,             -- JSONL 中的 message id
    session_key TEXT NOT NULL,
    role TEXT,                      -- user / assistant / system / tool
    content TEXT,                   -- 主要文本内容（去重、去 thinking 后的可读版）
    raw_content TEXT,               -- 原始 content 数组 JSON（保留完整信息）
    timestamp DATETIME,
    model TEXT,
    channel TEXT,
    tokens_used INTEGER DEFAULT 0,
    stop_reason TEXT,
    FOREIGN KEY (session_key) REFERENCES sessions(session_key)
);

-- 工具调用记录
CREATE TABLE tool_calls (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,       -- 关联到上一条 assistant 消息
    tool_name TEXT,
    arguments TEXT,                  -- JSON 字符串
    result TEXT,                     -- 工具返回内容
    FOREIGN KEY (message_id) REFERENCES messages(id)
);
```

**content 的处理规则（人类可读化）：**
- 保留 `text` 类型的文本
- 保留 `toolCall` 的 `name` 和简要 arguments（去掉超长参数）
- **不保留** `thinking` 内容（太长且可读性差），但记录该消息有 thinking
- `toolResult` 归入对应的 `tool_call` 记录

---

## 三、功能规划

### 3.1 数据导入与管理

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 扫描源目录 | 扫描指定目录，发现新的 JSONL 文件 | P0 |
| 增量解析 | 对比已有数据，只解析新增行 | P0 |
| 全量解析 | 从头解析整个文件 | P0 |
| 解析脚本（测试） | 先解析 1-2 条，打印输出给用户确认格式 | P0 |
| 定时同步 | 可选：定时扫描新文件 | P2 |

### 3.2 Web 展示界面

| 页面 | 说明 | 优先级 |
|------|------|--------|
| 首页仪表盘 | 总览统计（消息数、会话数、Token 消耗、日期范围） | P0 |
| 对话历史列表 | 按时间倒序列出所有会话，点击展开对话详情 | P0 |
| 对话详情页 | 展示单个会话的完整对话流（消息+工具调用） | P0 |
| 筛选功能 | 按日期范围、渠道筛选 | P1 |
| 搜索功能 | 按关键词搜索对话内容（未来扩展） | P2 |

### 3.3 存储与导出

| 功能 | 说明 | 优先级 |
|------|------|--------|
| Markdown 导出 | 将单个会话导出为 .md 文件 | P1 |
| JSON 导出 | 导出原始或处理后的对话 JSON | P2 |

---

## 四、技术方案

### 4.1 技术栈

| 层级 | 技术 | 选型理由 |
|------|------|---------|
| 后端 | Python FastAPI | 轻量异步，与其他项目一致 |
| 数据库 | SQLite | 零部署，适合中小量数据 |
| 前端 | 原生 HTML/CSS/JS | 无框架依赖，与其他项目一致 |
| 数据解析 | 标准库 json + 内置类型 | 不需要额外依赖 |
| 图表 | Canvas 手绘 | 轻量，避免大而全的库 |

### 4.2 项目结构

```
pro5/
├── app.py                  # FastAPI 后端入口
├── requirements.txt        # Python 依赖
├── database.db             # SQLite 数据库（自动生成）
├── auto_run.sh            # 服务管理脚本
├── README.md              # 项目说明
├── SPEC.md                # 本规格文档
├── doc/
│   ├── DEVELOPMENT.md      # 开发指南（后续补充）
│   └── todo.md            # 开发任务清单（后续补充）
├── test/
│   └── test_parser.py      # 解析器单元测试
├── data/
│   ├── raw/               # 原始 JSONL 文件（软链接或复制）
│   └── parsed/             # 解析后数据（SQLite）
├── scripts/
│   └── parse_sample.py     # 解析测试脚本（先于主项目运行）
└── static/                # 静态资源
    ├── index.html          # 首页仪表盘
    ├── conversations.html  # 对话历史列表
    ├── conversation.html   # 对话详情页
    ├── css/style.css
    └── js/
        ├── api.js
        └── utils.js
```

### 4.3 关键解析逻辑

OpenClaw JSONL 是**每行独立事件**，不是嵌套结构。解析流程：

```
逐行读取 JSONL
  ↓
判断 type：
  ├─ session       → 新建会话记录
  ├─ message       → 提取消息内容，写入 messages 表
  │                 同时根据 parentId 关联到会话
  ├─ toolCall      → 在 tool_calls 表中记录
  └─ 其他类型      → 跳过或提取元数据
```

**parentId 关联逻辑：**
- 一条 `message` 的 `id` 是全局唯一的
- 它的 `parentId` 可能指向前一条 assistant 消息（工具调用结果）
- 也可能指向 `thinking_level_change` 或 `custom` 等中间节点
- 需要构建 id → message 的映射，按时间顺序处理

---

## 五、界面原型（文字描述）

### 5.1 首页仪表盘
- 4 个统计卡片：总消息数、总会话数、总 Token 消耗、数据日期范围
- 每日消息趋势折线图
- 渠道/模型分布饼图

### 5.2 对话历史列表
- 表格形式：会话 ID（前8位）、首条消息时间、最后消息时间、消息数、渠道
- 点击行跳转对话详情

### 5.3 对话详情页
- 顶部：会话 ID、时间范围、使用模型
- 消息流：role 标签 + 内容 + 时间戳
- 工具调用可折叠展示参数和结果

---

## 六、优先级与开发顺序

```
Step 0. 解析测试脚本
  → 先写 parse_sample.py，解析 JSONL 前 50 行
  → 打印输出，用户确认格式理解正确

Step 1. 数据库设计 + 解析脚本
  → 建表、写完整解析逻辑
  → 处理增量导入

Step 2. Web 界面基础框架
  → FastAPI 路由 + 前端静态文件

Step 3. 仪表盘页面
  → 统计数据 + 趋势图

Step 4. 对话历史列表页

Step 5. 对话详情页
```

---

## 七、待确认事项

以下问题需要用户回答后才能继续：

1. **数据目录**：源 JSONL 文件目录是固定的吗？还是由用户每次指定？
2. **历史数据处理**：已有的 JSONL 文件是一次性导入，还是增量追加？
3. **Thinking 内容**：消息中的 `thinking`（AI 推理过程）是否要保留？还是直接丢弃？
4. **工具调用展示**：工具调用的 `arguments`（通常很长）要展示到哪个层级？简单摘要还是完整内容？

---

_文档版本：v0.1_
_创建日期：2026-04-04_
