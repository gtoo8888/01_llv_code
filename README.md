# 01_llv_code

AI 生成代码项目仓库。由 OpenClaw 共同维护。

---

## 项目一览

| 项目 | 类型 | 描述 | 端口 | 环境 |
|------|------|------|------|------|
| **pro1** | 🌐 Web | 财务管理工具 | 8081 | base |
| **pro2** | 🌐 Web | 论文可视化 | 8001 | `paper_dashboard` |
| **pro3** | 🌐 Web | 系统监控 | 8000 | `linux_dashboard` |
| **pro4** | 📦 脚本 | 语音转文字 | — | `whisper_dashboard` |
| **pro5** | 🌐 Web | 对话知识管家 | 8002 | `llm_chat_dashboard` |
| **pro6** | 📦 脚本 | 电影票房分析 | — | base |
| **pro7** | 📦 脚本 | 字幕提取 | — | base |
| **pro8** | 📦 脚本 | 代码统计 | — | base |
| **pro9** | 📦 脚本 | RPC 工具集 | — | `openclaw_tool` |
| **drafts** | 📦 杂项 | 零散片段 | — | — |

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
├── pro4/                   # 语音转文字
├── pro5/                   # 对话知识管家
├── pro6/                   # 电影票房分析
├── pro7/                   # 字幕提取
├── pro8/                   # 代码统计
├── pro9/                   # OpenClaw RPC 工具集
└── drafts/                 # 实验性代码片段
```

---

## 各项目启动

```bash
# pro1 — 财务管理工具
cd pro1/financial_management_tools
conda activate base
./auto_run.sh run
# 访问: http://localhost:8081

# pro2 — 论文可视化
cd pro2
conda activate paper_dashboard
./auto_run.sh run
# 访问: http://localhost:8001

# pro3 — 系统监控
cd pro3
conda activate linux_dashboard
./auto_run.sh run
# 访问: http://localhost:8000

# pro4 — 语音转文字
cd pro4
conda activate whisper_dashboard
python transcribe.py <音频文件>

# pro5 — 对话知识管家
cd pro5
conda activate llm_chat_dashboard
./auto_run.sh run
# 访问: http://localhost:8002

# pro6 — 电影票房分析
cd pro6
conda activate base
python taopiaopiao_to_csv.py

# pro7 — 字幕提取
cd pro7
conda activate base
python extract_english_ass.py

# pro8 — 代码统计
cd pro8
conda activate base
python count_word.py <目录路径>

# pro9 — RPC 工具集
cd pro9
conda activate openclaw_tool
python session_stats.py --token <token>
```

---

本仓库为多项目合集仓库，各 `proN` 目录相互独立。`drafts/` 目录下为零散代码片段，不构成完整项目。
