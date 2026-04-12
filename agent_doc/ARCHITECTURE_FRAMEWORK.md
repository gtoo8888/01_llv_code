# 代码开发通用架构框架

_供 AI 理解代码项目通用开发规范的参考文档_

本目录用于沉淀 AI 执行代码开发任务时的通用框架和规范，减少每次从零开始的结构设计工作。

---

## 一、核心架构风格

**前后端分离 + 单页内嵌多视图**

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 后端 | Python FastAPI | 轻量、异步、自动 OpenAPI 文档 |
| 数据库 | SQLite | 无部署依赖，适合中小型数据 |
| 前端 | 原生 HTML/CSS/JS | 无框架依赖，包体积小，可独立运行 |
| 图表 | Canvas 自绘 或 轻量库 | 按需引入，避免大而全的图表库 |
| 环境管理 | Conda | Python 版本隔离，依赖可复现 |

---

## 二、目录结构规范

```
{project}/
├── app.py                  # FastAPI 后端入口
├── requirements.txt        # Python 依赖列表
├── database.db             # SQLite 数据库文件（自动生成）
├── auto_run.sh             # 服务管理脚本（启/停/状态/日志）
├── README.md               # 项目说明文档
├── doc/                    # 详细文档目录
│   ├── DEVELOPMENT.md      # 开发指南
│   └── todo.md             # 开发计划/任务清单
├── test/                   # 后端测试目录
│   ├── test_main.py        # 测试示例
│   └── test_xxx.py         # 按模块组织测试
└── static/                 # 静态资源目录
    ├── index.html          # 主页面/导航页
    ├── page1.html          # 功能页1
    ├── page2.html          # 功能页2
    ├── css/
    │   ├── style.css       # 公共样式
    │   ├── page1.css       # 页面1专属样式
    │   └── page2.css       # 页面2专属样式
    └── js/
        ├── api.js          # API 调用封装（统一出口）
        ├── utils.js        # 工具函数
        ├── page1.js        # 页面1业务逻辑
        └── page2.js        # 页面2业务逻辑
```

### 命名规范

- **Python 文件**：小写下划线 `financial_calculator.py`
- **JS/CSS 文件**：小写下划线 `api_client.js`
- **HTML 页面**：小写横线（kebab-case）`financial-calculator.html`
- **目录**：小写下划线 `static/js/`

---

## 三、后端架构规范

> **当前无特殊约束**：AI 可根据项目需求自行设计路由、数据库操作和错误处理。  
> 建议遵循 FastAPI 最佳实践（类型注解、依赖注入等），后续如有通用模式再补充。

---

## 四、前端架构规范

> **当前无特殊约束**：AI 可自由使用原生 HTML/CSS/JS 实现页面功能，无需框架。  
> 后续会根据实际开发经验总结公共样式、API 封装、状态管理等规范。

---

## 五、服务管理脚本（auto_run.sh）

> **说明**：每个项目会配备一个通用启动脚本 `auto_run.sh`，支持 `start|stop|restart|status|logs` 等常用命令。  

---

## 六、开发流程建议

```
1. 需求分析 → 编写 doc/todo.md（任务拆解）
2. 搭建架子 → 创建目录结构 + auto_run.sh + 基础 app.py
3. API 先行 → 先定义后端接口（路由和响应格式），前后端可并行开发
4. 集成测试 → 前后端对接，使用真实数据测试
5. 优化迭代 → 在 doc/ 中记录问题与解决方案
6. 文档完善 → 更新 README.md、DEVELOPMENT.md
```

---

## 七、这套框架适合的场景

✅ **适合**
- 内部工具、运维脚本的可视化界面
- 数据可视化（图表、报表、仪表盘）
- 个人/小团队使用的 Web 小工具
- 快速原型验证

❌ **不适合**
- 高并发、多用户 Web 应用（建议使用 FastAPI + Vue/React + PostgreSQL）
- 复杂数据模型和大量关联查询（考虑 PostgreSQL + SQLAlchemy ORM）
- SEO 敏感的前台网站（应使用 SSR 框架如 Next.js、Nuxt）
- 移动端优先的应用（建议使用专门的移动端框架如 React Native、Flutter）
