# 论文库可视化项目开发计划

> 项目路径：`/data_sdb/openclaw/02_llv_generated/01_llv_code/pro2/`
> 数据源：`/data_sdb/openclaw/01_data/04_papers/raw/`
> 当前版本：v0.1 — 最小可用版本

---

## 一、需求理解

**本版本目标：** 读取指定文件夹，以树状结构可视化展示目录层级与文件分布。

**仅做：**
- 读取用户指定的目录路径
- 将目录结构渲染为树状图（前端展示）

**不做（未来演进方向）：**
- 搜索功能
- PDF 内容提取 / 摘要 / 关键词
- 旭日图（下个版本考虑）
- 词云、网络图等进阶可视化

---

## 二、开发原则（大模型必须遵守）

> 摘录自 pro3/doc/DEVELOPMENT.md

1. **前后端联动实现** — 不要只写前端或只写后端，实现一个功能需要前后端配合
2. **开发前先确认需求** — 不要马上开始编码，先和用户确认具体细节
3. **后端代码需添加单元测试** — 完成后询问用户是否需要添加单元测试
4. **前端代码做好拆分** — 一个功能对应一个 HTML 文件；CSS 和 JS 必须拆分到独立文件，禁止大量内联代码；页面导航必须包含，方便页面跳转

---

## 三、技术方案

| 层级 | 技术选型                                  |
| ---- | ----------------------------------------- |
| 后端 | Python FastAPI                            |
| 前端 | 原生 HTML + CSS + JavaScript（无框架）    |
| 图表 | Canvas 自行绘制（参考 pro3 的 charts.js） |
| 依赖 | `fastapi`、`uvicorn`                      |

---

## 四、文件结构

> 参考 pro1/financial_management_tools/static 的前端目录规划

```
/data_sdb/openclaw/02_llv_generated/01_llv_code/pro2/
├── app.py                        # FastAPI 主程序
├── README.md
├── PROJECT_PLAN.md
├── test_main.py                  # 后端单元测试（如需要）
├── doc/
│   └── DEVELOPMENT.md            # 开发规范
├── scripts/
│   └── scan_dir.py               # 目录扫描逻辑（可复用）
└── static/                       # 前端资源
    ├── index.html                 # 首页（主功能页面）
    ├── tree.html                  # 树图页面
    ├── css/
    │   ├── style.css             # 公共样式
    │   └── tree.css              # 树图页面样式
    └── js/
        ├── api.js                # API 调用封装
        ├── tree.js               # 树图 Canvas 绘制逻辑
        ├── events.js             # 事件处理（参考 pro3/events.js）
        ├── constants.js           # 常量配置（参考 pro3/constants.js）
        └── main.js               # 入口初始化
```

---

## 五、开发步骤

### 阶段 1：目录解析逻辑

**目标：** 读取指定目录，输出树状结构数据

**任务：**
- [ ] 写脚本 `scripts/scan_dir.py`
- [ ] 接收目录路径（后端接口传入），遍历目录
- [ ] 返回 JSON 树结构：
  ```json
  {
    "name": "raw",
    "children": [
      {
        "name": "02_Economics",
        "children": [
          {
            "name": "0202_Applied_Economics",
            "children": [
              { "name": "Quantitative_Finance", "children": [] }
            ]
          }
        ]
      }
    ]
  }
  ```
- [ ] 支持可选参数：是否包含文件（叶子节点为文件时显示文件名）

---

### 阶段 2：后端 API

**目标：** 提供目录扫描接口

**任务：**
- [ ] FastAPI 接口：`POST /tree`（请求体接收目录路径）
- [ ] 调用扫描逻辑返回 JSON 树
- [ ] 添加 CORS 支持
- [ ] 根路径 `/` 返回前端 index.html

---

### 阶段 3：前端树状图展示

**目标：** 用户输入路径，前端渲染树状图

**任务：**
- [ ] `static/index.html` — 页面：输入框（目录路径）+ 展示按钮 + 树图画布
- [ ] `static/css/style.css` — 公共基础样式
- [ ] `static/css/tree.css` — 树图页面专用样式
- [ ] `static/js/constants.js` — 常量配置（画布尺寸、颜色等）
- [ ] `static/js/api.js` — `/tree` 接口调用封装
- [ ] `static/js/events.js` — 按钮点击事件绑定、输入框回车事件
- [ ] `static/js/tree.js` — Canvas 树图绘制（展开/收起交互）
- [ ] `static/js/main.js` — 入口初始化，按 DOMContentLoaded 初始化事件

**Canvas 树图交互：**
- 点击节点可展开/收起子树
- 鼠标悬停高亮当前节点
- 显示各节点下的文件/目录数量

---

### 阶段 4：单页测试与迭代

- [ ] 前后端联调，确认数据流通
- [ ] 手动测试边界情况（空目录、路径不存在、权限不足等）
- [ ] 询问用户是否需要添加单元测试

---

## 六、页面导航设计

```
/                    → overview.html（概览页面）
/tree.html           → tree.html（目录树页面）
```

后续扩展页面放在同级目录，遵循"一个功能 = 一个 HTML + 对应 css/js 文件"原则。

---

## 七、演进方向（未来版本）

以下为本版本**不做**的功能，留作后续迭代参考：

- 旭日图（sunburst）替代树图
- 搜索功能
- PDF 全文内容提取
- 关键词词云
- 作者合作网络图
- PDF 在线预览

---

_文档版本：v0.1 — 2026-03-22_
