# 01_llv_code

AI 生成代码项目仓库。由 OpenClaw 共同维护。

---

## 项目一览

| 项目 | 描述 | 端口 |
|------|------|------|
| **pro1** | 财务管理工具 — FastAPI 后端 + 前端静态页面，支持 A 股指数、计算器、图表 | 8081 |
| **pro2** | 论文可视化 — 按 GB/T 13745-2009 中国学科分类生成论文可视化图谱 | 8001 |
| **pro3** | Linux 系统监控面板 — 实时 CPU / 内存监控，带 Web 界面 | 8000 |
| **pro4** | Whisper 批量语音转文字 — 批量将音频转为文本（OpenAI Whisper） | — |
| **drafts** | 零散代码片段与实验代码 | — |

---

## 通用架构框架

> ⚠️ **AI 开发新项目时，必须先阅读 `agent_doc/` 下的全部文档，再开始编码。**

`agent_doc/` 目录下沉淀了适用于轻量级 Web 工具开发的通用架构规范，供 AI 开发新项目时直接参考。

### 新项目开发流程

1. **阅读框架文档** — 先完整阅读 `agent_doc/` 下所有文档（架构风格、目录结构、命名规范、开发原则、服务脚本）
2. **参考 README 模板** — 以 `README_TEMPLATE.md` 为模板，为新项目编写专属 README
3. **搭建项目结构** — 按 `ARCHITECTURE_FRAMEWORK.md` 中的目录结构规范创建项目
4. **遵循开发原则** — 前后端联动、需求先行、添加单元测试、代码拆分到位

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE_FRAMEWORK.md](./agent_doc/ARCHITECTURE_FRAMEWORK.md) | 核心架构风格、目录结构规范、命名规范、开发流程 |
| [DEVELOPMENT.md](./agent_doc/DEVELOPMENT.md) | 开发原则（前后端联动、需求确认、单元测试、代码拆分） |
| [auto_run.sh](./agent_doc/auto_run.sh) | 服务管理脚本模板（run/stop/status/logs/restart/clean） |
| [README_TEMPLATE.md](./agent_doc/README_TEMPLATE.md) | 项目 README 标准模板 |

---

## 目录结构

```
01_llv_code/
├── agent_doc/              # 通用架构框架（供 AI 开发新项目参考）
│   ├── ARCHITECTURE_FRAMEWORK.md
│   ├── DEVELOPMENT.md
│   ├── auto_run.sh
│   └── README_TEMPLATE.md
├── pro1/                   # 财务管理系统
├── pro2/                   # 论文可视化
├── pro3/                   # Linux 系统监控
├── pro4/                   # Whisper 批量转录
└── drafts/                 # 实验性代码片段
```

---

## 各项目详情

### pro1 — 财务管理系统

```bash
cd /data_sdb/openclaw/02_llv_generated/01_llv_code/pro1/financial_management_tools
./auto_run.sh run
```

访问 http://localhost:8081

### pro2 — 论文可视化

```bash
cd /data_sdb/openclaw/02_llv_generated/01_llv_code/pro2
./auto_run.sh run
```

访问 http://localhost:8001

### pro3 — Linux 系统监控

```bash
cd /data_sdb/openclaw/02_llv_generated/01_llv_code/pro3
./auto_run.sh run
```

访问 http://localhost:8000

---

本仓库为多项目合集仓库，各 `proN` 目录相互独立。`drafts/` 目录下为零散代码片段，不构成完整项目。
