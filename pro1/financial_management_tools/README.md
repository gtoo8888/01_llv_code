# 理财收益计算器

一个Web 应用，用于计算理财产品的收益，并提供A股主要指数行情数据。

## 文档目录

| 文档 | 说明 |
|------|------|
| **README.md** | 项目介绍、快速开始（本文档） |
| [ARCHITECTURE.md](./doc/ARCHITECTURE.md) | 技术架构、前后端分离设计 |
| [DEPLOY.md](./doc/DEPLOY.md) | 生产环境部署指南 |
| [DEVELOP.md](./doc/DEVELOP.md) | 开发指南（供大模型阅读） |
| [DEVELOP_ISSUES.md](./doc/DEVELOP_ISSUES.md) | 开发问题记录 |
| [OPTIMIZATION.md](./doc/OPTIMIZATION.md) | 性能优化记录 |

---

## 技术栈

- **后端：** Python + FastAPI + SQLite
- **前端：** 原生 HTML + CSS + JavaScript
- **数据源：** Akshare（A股行情数据）
- **测试：** pytest
- **环境：** Conda finance 环境

## 快速开始

```bash
cd /date_sdb/soft/openclaw/code

# 启动服务
./auto_run.sh run

# 停止服务
./auto_run.sh stop
```

访问：**http://localhost:8081**

## 页面说明

| 页面 | 地址 | 说明 |
|------|------|------|
| 首页 | http://localhost:8081/ | 欢迎页，可跳转到各功能页面 |
| 理财收益计算器 | http://localhost:8081/wealth.html | 计算理财收益，保存历史记录 |
| 收益率计算器 | http://localhost:8081/calculator.html | 4种收益率计算工具 |
| 收益走势 | http://localhost:8081/chart.html | 可视化收益变化趋势 |
| 指数行情 | http://localhost:8081/indices.html | A股主要指数实时行情 |

## 指数行情功能

- 支持10个主要A股指数：上证指数、上证50、沪深300、中证A500、科创50、中证500、中证红利、创业板指、创业板50、红利低波100
- 支持选择历史日期查询
- 数据来源于 Akshare，每次查询间隔1秒防反爬
- 数据自动缓存到 SQLite 数据库

## 项目结构

```
├── main.py                    # FastAPI 后端入口
├── auto_run.sh                # 启动/停止脚本
├── requirements.txt           # Python 依赖
├── database.db                # SQLite 数据库
├── test_main.py               # 单元测试
├── test_akshare.py            # Akshare 测试脚本
├── README.md                  # 项目说明（入口）
├── app/                       # 应用代码（模块化结构）
├── doc/                      # 文档目录
│   ├── ARCHITECTURE.md       # 技术架构
│   ├── DEPLOY.md             # 部署指南
│   ├── DEVELOP.md             # 开发指南
│   ├── DEVELOP_ISSUES.md      # 开发问题记录
│   └── OPTIMIZATION.md        # 性能优化记录
└── static/                   # 静态资源
```

## 常用命令

```bash
./auto_run.sh run      # 启动
./auto_run.sh stop     # 停止
./auto_run.sh status   # 状态
./auto_run.sh logs     # 日志
./auto_run.sh restart  # 重启
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/indices` | 获取指数行情（从 Akshare 抓取） |
| `GET /api/indices/progress` | 获取指数抓取进度 |
| `GET /api/indices/cached` | 获取缓存的指数行情 |
| `GET /api/chart-data` | 获取收益走势数据 |
| `POST /calculate` | 计算理财收益 |
| `GET /records` | 获取理财记录 |

## 测试

```bash
# 激活环境
conda activate finance

# 运行所有测试
python3 -m pytest -v

# 运行特定测试
python3 -m pytest tests/test_calculator.py -v
```

---

> 💡 更多内容请参考：[ARCHITECTURE.md](./doc/ARCHITECTURE.md) | [DEPLOY.md](./doc/DEPLOY.md) | [DEVELOP.md](./doc/DEVELOP.md)
