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
├── llm_sessions/              # 对话数据源
│   └── openclaw/              #  JSONL 文件目录
├── scripts/                    # 解析脚本（备用）
├── doc/
│   ├── WEB_DESIGN.md          # Web 界面设计文档
│   ├── ROADMAP.md             # 未来功能路线图
│   ├── ISSUES.md              # 开发问题汇总
│   └── DEVELOPMENT.md         # 开发指南
├── test/
│   └── test_strip_user_metadata.py  # 单元测试
└── static/                    # 前端静态资源
    ├── index.html              # 主页面（SPA，左侧会话列表 + 右侧对话详情）
    ├── css/
    │   ├── style.css          # 公共样式
    │   └── index.css         # 页面专属样式
    └── js/
        ├── api.js             # API 调用封装
        └── index.js           # 页面逻辑
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

## 单元测试

```bash
python -m pytest test/test_strip_user_metadata.py -v
```
