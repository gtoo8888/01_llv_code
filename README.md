# 01_llv_code

AI 生成代码项目仓库。由 OpenClaw 共同维护。

## 项目一览

| 项目 | 描述 |
|------|------|
| **pro1** | 财务管理工具 — FastAPI 后端 + 前端静态页面，支持 A 股指数、计算器、图表 |
| **pro2** | 论文可视化 — 按 GB/T 13745-2009 中国学科分类生成论文可视化图谱 |
| **pro3** | Linux 系统监控面板 — 实时 CPU / 内存监控，带 Web 界面 |
| **pro4** | Whisper 批量语音转文字 — 批量将音频转为文本（OpenAI Whisper） |
| **drafts** | 零散代码片段与实验代码 |

## 目录结构

```
01_llv_code/
├── pro1/              # 财务管理系统
│   └── financial_management_tools/
│       ├── main.py            # FastAPI 入口
│       ├── static/            # 前端（HTML/JS/CSS）
│       ├── doc/                # 架构与开发文档
│       └── tests/              # 单元测试
├── pro2/              # 论文可视化
│   ├── app.py                 # 主应用
│   ├── subjects.py            # 学科分类逻辑
│   └── static/                # 前端资源
├── pro3/              # Linux 系统监控
│   ├── app.py                 # 监控 Web 服务
│   ├── test_*.py               # 基础测试
│   ├── build.sh               # 构建脚本
│   └── doc/                   # 说明文档
├── pro4/              # Whisper 批量转录
│   ├── main.py                 # 入口文件
│   ├── transcribe.py           # 转录逻辑
│   ├── converter.py            # 音频转换
│   └── whisper_models/          # 模型缓存目录
└── drafts/           # 实验性代码片段
```

## 说明

本仓库为多项目合集仓库，各 `proN` 目录相互独立。`drafts/` 目录下为独立片段代码，不构成完整项目。
