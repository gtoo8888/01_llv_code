# 对话知识管家

**让对话成为可沉淀的知识资产。**

> 📖 开始使用前，建议先阅读 `doc/` 目录下的文档了解各功能的设计细节。

> 🎯 **最终目标：对话列表为空。**
>
> 这个项目的核心使命不是**保存所有对话**，而是**处理完所有对话**。
>
> 每一条对话只有两个结局：
> - 📦 **有价值的** → 归档萃取，沉淀到知识工作区（`KnowledgeWorkspace/`）
> - 🗑️ **无价值的** → 标记删除
>
> 理想状态下，对话管理列表应该是空的——所有内容都已被分流：知识进了知识库，垃圾进了回收站。
>
> 这才是项目设计的终点，不是 bug。

## 为什么做这个项目

DeepSeek 的聊天记录功能体验不够好：

- 所有对话混在一起，没有分类/归档
- 搜索功能薄弱
- 聊过就沉了，有价值的内容无法留存

我日常与 DeepSeek 的对话中，很多是**深度思考、分析推理、信息整合**——这些是沉淀下来的知识精华，不是用完即弃的临时对话。我需要一个工具来管理这些内容。

---

## 设计理念

### 核心问题：一个矛盾，两种价值

一条对话里同时承载了两种价值：**内容价值**（能萃取的知识）和**元数据价值**（使用行为记录）。前者需要清空，后者需要保留。

### 解法：数据双副本

```
DeepSeek 导出 JSON → 永久存档（只读，物理隔离） + 工作数据库（可修改，日常操作）
```

---

## 三大核心能力

### 1. 📥 对话导入与展示

- DeepSeek 对话按年份/月份/日期导航浏览
- GitHub 风格活跃度日历，直观查看对话频率
- OpenClaw 消息流展示：User / Assistant / Tool Call 结构清晰
- 全文搜索（标题 + 正文），快速定位历史内容
- 统计大屏：月度趋势、时长分布、模型使用比例、时段热力图、对话时长散点图

### 2. 📂 对话归档管理 ✅（已实现）

三层状态生命周期：

| 状态 | 含义 | 显示 |
|------|------|------|
| 🟢 **普通** | 刚导入的原始对话，未处理 | 正常展示，在列表可见 |
| 🟡 **已归档** | 已萃取知识点，内容已沉淀到知识库 | 移入归档区，可查看笔记 |
| 🔴 **已删除** | 临时查询、低价值对话 | 移入回收站，可恢复或永久删除 |

**操作：** 单条/批量归档、删除、恢复、永久删除。支持年月筛选、标题搜索、分页。可填写知识提炼笔记。

> 永久删除仅标记为 `deleted_permanent`，不物理删除原始 `.md` 文件。

### 3. 💎 知识沉淀

通过归档机制，把有价值的对话内容**萃取出来**，转化为可反复查阅的知识资产。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 前端 | 原生 HTML + CSS + JavaScript（无框架）|
| 环境 | Conda |

## 快速开始

```bash
conda activate llm_chat_dashboard
pip install -r requirements.txt
./auto_run.sh run
```

访问：http://localhost:8002

## 新功能介绍

### 🔍 右侧正文搜索

对话内容显示后，右上角出现 🔍 按钮，点击展开搜索条，**仅搜索右侧正文**（不影响左侧侧栏）。

- **回车** → 首次执行搜索，之后跳转到下一个匹配
- **Shift+回车** → 跳转到上一个匹配
- 匹配项黄色高亮，当前匹配项红色高亮

### 🕐 侧栏时钟

侧栏顶部实时显示当前时间：`YYYY-MM-DD HH:mm:ss 星期X`，每秒自动刷新。

## 数据源

```
llm_sessions/deepseek/main/conversations.json   # DeepSeek 官方导出
llm_sessions/openclaw/                          # OpenClaw 对话 JSONL
```

## 离线工具（`scripts/`）

```bash
conda activate llm_chat_dashboard
python scripts/deepseek_parser.py list          # 列出所有对话
python scripts/deepseek_parser.py view 1        # 查看第1条对话
python scripts/deepseek_parser.py export        # 导出全部对话为 Markdown
python scripts/merge_conversations.py            # 合并多份导出文件

# 对话批量分类
python scripts/deepseek_conversation_topic_classifier.py              # 全量分类
python scripts/deepseek_conversation_topic_classifier.py --months 2026/05  # 指定月份测试
python scripts/deepseek_conversation_topic_classifier.py --max-files 20    # 快速验证
```

分类脚本基于关键词映射表为所有对话打上主题标签（1~2 个），输出按主题分组的索引。详见 `doc/CLASSIFICATION_PLAN.md`。

## 目录结构

```
pro5/
├── app.py                      # FastAPI 后端入口（启动预填所有会话 ID）
├── requirements.txt            # Python 依赖
├── database.db                 # SQLite 工作数据库
├── archives/                   # 永久存档目录
├── auto_run.sh                 # 服务管理脚本
├── README.md                   # 项目说明
├── src/                        # 后端核心模块
│   ├── config.py               # 配置
│   ├── database.py             # 数据库操作（含 conversation_status 表）
│   ├── parser.py               # JSONL 解析引擎
│   ├── routes.py               # FastAPI 路由
│   └── __init__.py
├── scripts/                    # 离线解析工具
├── doc/                        # 项目文档
├── static/
│   ├── index.html              # SPA 主页面
│   ├── css/
│   │   ├── layout.css          # 布局/侧栏/主内容区
│   │   ├── messages.css        # 消息气泡
│   │   ├── deepseek.css        # DeepSeek 浏览样式
│   │   ├── archive.css         # 对话管理样式
│   │   ├── stats.css           # 统计大屏样式
│   │   └── style.css           # 公共变量/全局样式
│   └── js/
│       ├── api.js              # API 封装（含状态管理接口）
│       ├── core.js             # 核心逻辑、Tab切换、正文搜索、时钟
│       ├── ds-navigation.js    # DeepSeek 年月导航/搜索/Markdown渲染
│       ├── ds-calendar.js      # 自定义日历 + 统计大屏
│       └── archive-manager.js  # 对话管理（归档/删除/恢复，对接真实 API）
└── data/
    └── parsed/                 # 解析产物
```

## 前端结构

| 文件 | 职责 |
|------|------|
| `api.js` | 所有 fetch 封装（含 PATCH/DELETE 操作） |
| `core.js` | Tab切换、OpenClaw 会话列表、正文搜索、侧栏时钟 |
| `ds-navigation.js` | DeepSeek 年份/月份导航、Markdown渲染、全文搜索 |
| `ds-calendar.js` | 自定义日历、统计大屏、GitHub 热力图 |
| `archive-manager.js` | 对话管理（状态卡片、批量操作、弹窗、真实 API） |

加载顺序：`api.js → core.js → ds-navigation.js → ds-calendar.js → archive-manager.js`

## API 列表

### OpenClaw 会话
| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sessions` | OpenClaw 会话列表 |
| `GET` | `/api/sessions/{key}/messages` | 某会话的所有消息 |

### DeepSeek 浏览
| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/deepseek/structure` | 归档年份/月份结构 |
| `GET` | `/api/deepseek/sessions?year=&month=&status=` | 某年月的对话列表（支持 status 筛选）|
| `GET` | `/api/deepseek/sessions/{id}` | 单条对话内容（Markdown） |
| `GET` | `/api/deepseek/sessions-by-date?date=` | 按日期查询 |
| `GET` | `/api/deepseek/dates?year=&month=` | 某月有对话的日期列表 |
| `GET` | `/api/deepseek/search?q=&mode=` | 标题/全文搜索 |
| `GET` | `/api/deepseek/stats` | 统计大屏（含 archive_stats）|

### DeepSeek 状态管理
| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/deepseek/sessions/all` | **全量对话 + 状态 + 笔记** |
| `GET` | `/api/deepseek/sessions/{id}/status` | 单条对话状态信息 |
| `PATCH` | `/api/deepseek/sessions/{id}/status` | 更新状态（raw/archived/deleted） |
| `DELETE` | `/api/deepseek/sessions/{id}/permanent` | 永久删除（标记） |

## 服务管理

```bash
./auto_run.sh run      # 启动
./auto_run.sh stop     # 停止
./auto_run.sh status   # 状态
./auto_run.sh logs     # 日志
./auto_run.sh restart  # 重启
./auto_run.sh clean    # 清理数据
```

## 相关文档

| 文档 | 内容 |
|------|------|
| `01_ARCHIVE_DESIGN.md` | 对话归档管理设计方案 |
| `02_SCRIPTS_USAGE.md` | 离线脚本使用指南（含所有 scripts/ 工具） |
| `03_DEVELOPMENT_HISTORY.md` | 开发记录、分类方案 |
| `04_DEVELOPMENT_ISSUES.md` | 开发问题复盘（含 Bug 修复、教训总结） |
