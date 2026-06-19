# 对话数据分析平台

读取 OpenClaw 对话数据，解析 JSONL 文件，Web 界面展示对话历史。

## 功能特性

- 📋 **会话列表** — 左侧栏展示所有会话，点击选择
- 💬 **对话详情** — 右侧展示选中会话的完整消息流
- 🔧 **工具调用展示** — 内嵌在 Assistant 消息中，默认折叠，点击展开参数和结果
- 📥 **Tool Result** — 默认折叠，通过展开按钮查看完整返回内容
- 🔍 **用户消息清洗** — 自动去除 System metadata，只保留真实用户发言

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 前端 | 原生 HTML + CSS + JavaScript（无框架）|
| 环境 | Conda |

## 快速开始

> ⚠️ 本项目依赖 Conda 环境 `llm_chat_dashboard`，所有操作请先激活该环境。

### 0. 激活 Conda 环境

```bash
conda activate llm_chat_dashboard
```

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
./auto_run.sh run
```

### 3. 访问

- 本地：http://localhost:8002
- 局域网：http://{IP}:8002

## 数据源

对话 JSONL 文件放在：

```
llm_sessions/openclaw/
```

服务启动时自动扫描该目录，增量解析新文件（已解析过的文件不会重复解析）。

## 目录结构

```
pro5/
├── app.py                      # FastAPI 后端入口
├── requirements.txt            # Python 依赖
├── database.db                 # SQLite 数据库（自动生成）
├── auto_run.sh                # 服务管理脚本
├── README.md                  # 项目说明
├── SPEC.md                    # 项目需求规格文档
├── src/                       # 后端核心模块
│   ├── config.py              # 静态文件路径等配置
│   ├── database.py            # 数据库操作
│   ├── parser.py              # JSONL 解析引擎（Web 服务集成使用）
│   ├── routes.py              # FastAPI 路由
│   └── __init__.py
├── scripts/                   # 独立解析工具（离线使用，不用启动 Web）
│   ├── parse_sample.py        # [Step 0] 样本预览 - 解析前 N 条事件，快速验证 JSONL 结构
│   ├── parse_conversations.py # [Step 1] 完整解析 - JSONL → SQLite + JSON + Markdown
│   └── deepseek_parser.py     # DeepSeek 对话解析 - 浏览/查看/导出 DeepSeek 对话记录
├── doc/
│   ├── WEB_DESIGN.md          # Web 界面设计文档
│   ├── ROADMAP.md             # 未来功能路线图
│   ├── ISSUES.md              # 开发问题汇总
│   └── DEVELOPMENT.md         # 开发指南
├── test/
│   └── test_strip_user_metadata.py  # 单元测试
├── static/                    # 前端静态资源
│   ├── index.html              # 主页面（SPA，左侧会话列表 + 右侧对话详情）
│   ├── css/
│   │   ├── style.css          # 公共样式
│   │   └── index.css         # 页面专属样式
│   └── js/
│       ├── api.js               # API 调用封装
│       ├── core.js              # 核心逻辑：通用工具、主会话列表、Tab切换
│       ├── ds-navigation.js     # DeepSeek 归档导航、对话查询、Markdown渲染、搜索
│       └── ds-calendar.js       # DeepSeek 自定义日历、统计大屏、初始化
└── data/                      # 数据输出目录（自动生成）
    └── parsed/                 # parse_conversations.py 输出的 JSON/Markdown
```

## 前端结构

`index.js`（1093 行）已按职责拆分为三份：

| 文件 | 行数 | 职责 |
|------|------|------|
| `core.js` | ~240 | 通用工具函数、主会话列表、Tab切换、API缓存变量 |
| `ds-navigation.js` | ~390 | DeepSeek 年份/月份导航、对话列表、Markdown渲染、全文搜索 |
| `ds-calendar.js` | ~460 | 自定义日历（日选择+月份切换）、统计大屏、初始化 |

加载顺序（依赖关系）：
```
api.js → core.js → ds-navigation.js → ds-calendar.js
```

## 服务管理

```bash
./auto_run.sh run      # 启动
./auto_run.sh stop     # 停止
./auto_run.sh status   # 状态
./auto_run.sh logs     # 日志
./auto_run.sh restart  # 重启
./auto_run.sh clean    # 清理数据和缓存
```

## API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sessions` | 会话列表 |
| `GET` | `/api/sessions/{key}/messages` | 某会话的所有消息 |
| `GET` | `/api/deepseek/structure` | DeepSeek 归档年份/月份结构 |
| `GET` | `/api/deepseek/sessions?year=&month=` | 某年月的 DeepSeek 对话列表 |
| `GET` | `/api/deepseek/sessions/{id}` | 单条 DeepSeek 对话内容 |
| `GET` | `/api/deepseek/search?q=&mode=` | DeepSeek 对话全文搜索 |
| `GET` | `/api/deepseek/dates?year=&month=` | 某月有对话的日期列表（日历用） |
| `GET` | `/api/deepseek/sessions-by-date?date=` | 按日期查询 DeepSeek 对话 |
| `GET` | `/api/deepseek/stats` | 对话统计大屏数据

## 离线解析脚本 (`scripts/`)

> 这两个脚本是**独立运行**的离线工具，不需要启动 Web 服务。用于从原始 JSONL 文件解析对话数据并导出。

### 1. `parse_sample.py` — 样本预览（Step 0）

解析 JSONL 文件的前 30 条事件记录，按行打印解析结果，快速验证文件结构是否正确。

```bash
conda activate llm_chat_dashboard && python scripts/parse_sample.py
```

输出示例：每行事件会显示 type、id、parent、timestamp，以及消息内容预览（自动折叠 toolCall/toolResult 参数）。

### 2. `parse_conversations.py` — 完整解析（Step 1）

将 JSONL 完整解析并写入 SQLite 数据库，同时导出 JSON 和 Markdown 格式供人工查阅。

```bash
conda activate llm_chat_dashboard && python scripts/parse_conversations.py
```

执行流程：
1. 初始化 SQLite 数据库（创建 sessions / messages / tool_calls 三张表）
2. 逐行解析 JSONL，提取会话、消息、工具调用
3. 建立 toolCall 与 toolResult 的配对关系
4. 写入数据库
5. 导出完整 JSON（`data/parsed/all_conversations.json`）
6. 导出人类可读 Markdown（`data/parsed/all_conversations.md`）

配置项（脚本顶部硬编码）：
| 参数 | 说明 |
|------|------|
| `SOURCE_FILE` | 输入的 JSONL 文件路径 |
| `DB_PATH` | SQLite 数据库保存路径 |
| `JSON_OUTPUT` | JSON 导出路径 |
| `MD_OUTPUT` | Markdown 导出路径 |
| `LIMIT` | 限制解析条数（`None`=全部） |

## DeepSeek 对话解析 (`scripts/deepseek_parser.py`)

> ⚠️ **DeepSeek 对话内容为本系统的核心知识存储**
> 与 OpenClaw 的临时对话日志不同，DeepSeek 归档中的对话是经过用户精心整理、筛选过的知识沉淀，包含大量深度思考、分析推理、信息整合等内容。这些文件是你可以反复查阅、搜索、依赖的知识资产，而非一次性对话记录。
> 建议优先关注 DeepSeek 归档的日常维护与搜索使用。

> 解析 DeepSeek 官方导出的 JSON 对话文件（33MB 单行数组格式），
> 查看你的核心对话知识库。文件放在 `llm_sessions/deepseek/main/conversations.json`。

### 列出所有对话

```bash
conda activate llm_chat_dashboard
python scripts/deepseek_parser.py list
```

输出示例：每个对话显示标题、日期范围、消息条数、使用的模型。

### 查看单个对话详情

支持按索引号或 ID 前缀查找：

```bash
# 按列表中的序号
python scripts/deepseek_parser.py view 1

# 按 ID 前缀
python scripts/deepseek_parser.py view c26ef77a
```

会显示完整的对话内容，包括 REQUEST、THINK（思考过程）和 RESPONSE。

### 导出全部对话为 Markdown

```bash
conda activate llm_chat_dashboard
python scripts/deepseek_parser.py export
```

导出到 `data/deepseek_conversations/` 目录，按 `日期_标题.md` 命名。
每个文件包含完整的对话记录，THINK 段默认折叠为 `<details>` 可展开。

## 新增功能

### 📅 GitHub 风格活跃度日历

- `🔥 活跃度日历（近 12 周）` — 统计大屏中的热力图，绿色深浅代表每日对话数量
- 5 级配色（`#ebedf0` → `#216e39`），周标签 + 星期行 + 图例

### 📆 自定义日历（按日期浏览）

- 按月切换的日历视图，有对话的日期显示绿色圆点
- 点击日期筛选当日对话列表

## 性能优化

### DOM 操作优化（3.1）

| 模块 | 改前 | 改后 |
|------|------|------|
| **日历网格** | 切月时 `innerHTML` 重建全部 42 个格子 | 首次 `DocumentFragment` 建好 DOM，之后只更新格子数字/样式/dot |
| **月份切换** | 两个独立函数 `dsCalPrevMonth` / `dsCalNextMonth` | 统一 `dsCalSwitchMonth(delta)` |
| **日期选中** | `querySelectorAll` 遍历全部格子 | 缓存 `dsCalGridCells` 数组直接遍历 |
| **会话列表** | `innerHTML` + 字符串拼接（HTML 解析开销） | `DocumentFragment` + `createElement` 批量插入 |
| **会话选中** | `querySelectorAll` 全量遍历 | 先取 `.active` 再按 `[data-id=]` 定位 |
| **加载/错误态** | `innerHTML` 字符串替换 | `textContent` + `appendChild` 新建元素 |

### 死代码清理（2.2）

- 删除未调用的 `toggleExpand` 函数（toolresult 展开/折叠由内联 onclick 直接操作兄弟元素实现）

### API 缓存（3.2）

| 缓存 | 用途 | 策略 |
|------|------|------|
| `dsStructureCache` | `deepseekGetStructure()` 归档结构 | 首次请求后缓存，切换年份直接读缓存，免重复请求 |
| `dsDatesCache`(Map) | `deepseekGetDates(year,month)` 日历数据 | 键 `"YYYY-MM"`，存 Promise 防并发重复请求 |

## Bug 修复

### 函数名覆盖导致 "sessions is not iterable"

`renderSessionList` 声明了两次（主列表 `core.js` + DeepSeek 列表 `ds-navigation.js`），JS 函数提升导致后者覆盖前者。主列表调用时传参错位：`listEl`=会话数组、`sessions`=`undefined` → `for...of undefined` 抛错。

**修复**：DeepSeek 版改名 `renderDsSessionList`，加 `Array.isArray` 防御。

## 单元测试

```bash
python -m pytest test/test_strip_user_metadata.py -v
```
