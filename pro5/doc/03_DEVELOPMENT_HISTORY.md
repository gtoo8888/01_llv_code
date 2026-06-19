# 开发记录

_本文档记录项目开发过程中的技术决策、性能优化、Bug 修复等内容，供后续迭代参考。_

---

## 对话管理 — 前端先行版（2026-06-19）

### 概述

按设计文档 `doc/ARCHIVE_DESIGN.md` 的前端先行方案，用假数据实现了完整的对话管理界面，包含状态管理、筛选、搜索、分页、弹窗交互。

### 功能清单

| 功能 | 说明 |
|------|------|
| 状态卡片 | 纵向排列的三行：待处理/已归档/回收站，带进度条、百分比、数量，点击筛选 |
| 归档完成率 | 进度条显示 `archived ÷ (raw + archived)` |
| 年月筛选 | 两个下拉框，支持「全部年份/全部月份」组合，切换后统计和列表联动 |
| 标题搜索 | 输入关键词 + 点「搜索」按钮（或回车），与年月/状态筛选叠加 |
| 分页 | 每页 15 条（上线后改 100），列表底部页码导航 |
| 归档弹窗 | 可填写知识提炼笔记 |
| 删除确认 | 二次确认移入回收站 |
| 恢复 | 从已归档/回收站恢复到待处理 |
| 永久删除 | 仅回收站可见，确认后从数据中移除 |
| 批量操作 | 全选 + 批量归档/删除/恢复/永久删除 |
| 右侧详情 | 点击对话标题在右侧展示信息+笔记 |

### 文件变更

| 文件 | 类型 | 说明 |
|------|------|------|
| `static/index.html` | 修改 | DeepSeek 视图拆分子 Tab、添加弹窗容器、CSS 加载调整 |
| `static/js/core.js` | 修改 | 添加 `switchDsSubTab()`、页面初始化逻辑 |
| `static/js/archive-manager.js` | **新增** | 完整的前端管理模块，52 条假数据 |
| `static/css/archive.css` | **新增** | 管理界面 + 弹窗 + 分页样式 |
| `static/css/layout.css` | **新增** | 布局/侧边栏/主内容区（从 index.css 拆分） |
| `static/css/messages.css` | **新增** | 消息气泡/工具调用（从 index.css 拆分） |
| `static/css/deepseek.css` | **新增** | DeepSeek 相关样式（从 index.css 拆分） |
| `static/css/stats.css` | **新增** | 统计大屏（从 index.css 拆分） |
| `static/css/index.css` | 删除 | CSS 拆分后不再需要 |

### 注意点

- **弹窗 onclick**：所有弹窗按钮的点击事件使用字符串形式（如 `'amDoDelete(state.pendingId)'`），而非闭包函数引用，避免序列化后变量丢失
- **State 全局化**：`state` 变量不使用 IIFE 包裹，确保弹窗 `onclick` 字符串能直接访问
- **搜索框焦点**：筛选区（`am-filter-area`）与结果区（`am-results`）分离，结果重渲染不影响搜索框 DOM

---

## 性能优化

### DOM 操作优化

| 模块 | 改前 | 改后 |
|------|------|------|
| **日历网格** | 切月时 `innerHTML` 重建全部 42 个格子 | 首次 `DocumentFragment` 建好 DOM，之后只更新格子数字/样式/dot |
| **月份切换** | 两个独立函数 `dsCalPrevMonth` / `dsCalNextMonth` | 统一 `dsCalSwitchMonth(delta)` |
| **日期选中** | `querySelectorAll` 遍历全部格子 | 缓存 `dsCalGridCells` 数组直接遍历 |
| **会话列表** | `innerHTML` + 字符串拼接（HTML 解析开销） | `DocumentFragment` + `createElement` 批量插入 |
| **会话选中** | `querySelectorAll` 全量遍历 | 先取 `.active` 再按 `[data-id=]` 定位 |
| **加载/错误态** | `innerHTML` 字符串替换 | `textContent` + `appendChild` 新建元素 |

### API 缓存

| 缓存 | 用途 | 策略 |
|------|------|------|
| `dsStructureCache` | `deepseekGetStructure()` 归档结构 | 首次请求后缓存，切换年份直接读缓存，免重复请求 |
| `dsDatesCache`(Map) | `deepseekGetDates(year,month)` 日历数据 | 键 `"YYYY-MM"`，存 Promise 防并发重复请求 |

---

## 死代码清理

- 删除未调用的 `toggleExpand` 函数（toolresult 展开/折叠由内联 onclick 直接操作兄弟元素实现）

---

## Bug 修复

### 函数名覆盖导致 "sessions is not iterable"

`renderSessionList` 声明了两次（主列表 `core.js` + DeepSeek 列表 `ds-navigation.js`），JS 函数提升导致后者覆盖前者。主列表调用时传参错位：`listEl`=会话数组、`sessions`=`undefined` → `for...of undefined` 抛错。

**修复**：DeepSeek 版改名 `renderDsSessionList`，加 `Array.isArray` 防御。

---

## 单元测试

运行方式：

```bash
python -m pytest test/test_strip_user_metadata.py -v
```

---

## 对话管理 — 后端实现 + 前端对接（2026-06-19）

### 概述

将前端先行版的假数据替换为真实后端 API，完成了对话管理的全链路实现：数据库层 → API 层 → 前端对接。

### 新增功能

| 功能 | 说明 |
|------|------|
| **正文搜索** | 右侧面板独立搜索条，回车下一个/Shift+回车上一个，黄色高亮，不影响左侧栏 |
| **侧栏时钟** | 侧栏顶部实时时间显示 YYYY-MM-DD HH:mm:ss 星期X |
| **归档统计** | stats 端点新增 archive_stats 字段 |

### 后端改动

**数据库 `src/database.py`**：

新增 `conversation_status` 表，含懒初始化策略。

新增函数：`get_or_init_status`、`upsert_status`、`get_status_for_sessions`、`get_status_counts`、`permanent_delete_status`、`ensure_all_sessions_init`

**API 路由 `src/routes.py`**：

增强 4 个现有端点（添加 status 字段 + status 筛选）：`sessions`、`sessions-by-date`、`stats`、`search`

新增 4 个端点：`sessions/all`、`sessions/{id}/status`(GET)、`sessions/{id}/status`(PATCH)、`sessions/{id}/permanent`(DELETE)

**启动逻辑 `app.py`**：启动时预填所有对话 ID 到状态表

### Bug 修复

1. **路由冲突**：`/api/deepseek/sessions/all` 被 `{session_id}` 参数路由抢匹配，导致 404。将 `all` 路由移到 `{session_id}` 前注册解决。
2. **脚本加载顺序**：`core.js` 底部调用 `loadDsStructure()` 但函数定义在 `ds-navigation.js` 中（加载顺序靠后），ReferenceError。将初始化代码移到 `ds-navigation.js` 末尾。

## 对话批量分类方案
---

## 一、背景与目标

### 1.1 现状
- DeepSeek 全量对话 **2287 条**，时间跨度 2025.01 → 2026.06
- 内容高度混杂：Linux 内核、FFmpeg、PyQt、串口通讯、REITs、宠物喂养、电影剧情……
- 当前仅按年月目录组织，**无主题索引**
- 查找特定主题只能全文搜索或凭记忆翻找

### 1.2 目标
为全部对话打上主题标签（1~2 个），生成按主题分组的索引，让用户能快速浏览和定位特定领域的对话。

---

## 二、核心原则

### 2.1 物理不动，逻辑标记
- 不修改原始 `.md` 对话文件
- 保留现有年月目录结构不变
- 分类结果独立存储为索引文件，随时可重跑、可回滚

### 2.2 精确匹配，拒绝模糊
- 所有关键词匹配采用**子串精确查找**
- **不使用任何模糊匹配**（difflib、编辑距离、相似度计算等）
- 宁可漏掉，不可误判

### 2.3 计分竞争，择优标签
- 每个类别通过关键词命中次数和权重计算得分
- 多个类别公平竞争，取最高 1~2 个作为最终标签
- 得分低于阈值的对话归入"待分类"

### 2.4 规则透明，人机协作
- 每条归类都能追溯到具体命中了哪些关键词
- 机器负责统计和候选词发现，人负责最终确权
- 通过迭代逐步完善，而非一步到位

---

## 三、分类体系

### 3.1 标签层级结构

分类采用 **父类/子类** 两级层次结构，共 12 个父类、25 个子类：

| 父类 | 子类 |
|------|------|
| 金融投资 | 股票基金、债券套利、理财宏观、期权期货 |
| Python | 基础语法、数据处理、Web框架、日志工具 |
| PyQt | 综合 |
| C++ | 语法特性、编译构建 |
| 音视频 | FFmpeg、编码封装 |
| 嵌入/硬件 | 通信、芯片 |
| 系统 | Linux、工具 |
| 工具/运维 | Git、通讯、调试部署 |
| 生活日常 | 宠物、影视娱乐、旅游美食、生活健康 |
| 医学/健康 | 器械、健康饮食 |
| 学术/教育 | 考试、院校论文 |

数据按 `output/category_summary.csv` 统计。

### 3.2 标签规则
- 每条对话打 **1~2 个标签**（子类级别）
- 可能只打 1 个（只有一个类别过阈值）
- 可能进入"待分类"（零个类别过阈值）

---

## 四、关键词映射表

### 4.1 文件位置
`scripts/keyword_map.json`，与脚本逻辑分离，可独立编辑。

### 4.2 JSON 结构（嵌套层级）
```json
{
    "金融投资": {
        "股票基金": {
            "股票": 1.0, "A股": 1.5, "ETF": 2.0,
            "挂单量": 2.0
        },
        "债券套利": {
            "债券": 1.5, "可转债": 2.0, "REIT": 2.0
        }
    }
}
```

加载时自动拍平成 `父类/子类` 扁平格式供脚本使用。

### 4.3 确信度权重体系

| 确信度 | 权重值 | 适用场景 | 示例 |
|--------|--------|---------|------|
| 高 | 2.0 | 长尾专有名词，几乎不会在其他语境出现 | `ffprobe`、`信号与槽`、`龙虎榜`、`可转债` |
| 中 | 1.0 | 一般领域词，有一定区分度 | `python`、`股票`、`cmake`、`串口` |
| 低 | 0.5 | 短词或多义词，容易在无关语境出现 | `内存`、`线程`、`编码`、`信号` |

### 4.4 低确信度词的特殊规则
- 低确信度词（权重 ≤ 0.5）在正文中需要**累计出现 ≥ 3 次**才开始计分
- 标题命中不受此限制——标题里出现即说明该词有主题意义
- 此规则用于防止"内存"在闲聊中误触 C/C++ 分类

### 4.5 关键词变体覆盖
同一概念的常见写法变体直接在映射表中列出，无需模糊匹配：
- `ffmpeg` / `FFmpeg` → 实际匹配时统一转为小写后做子串查找
- `REIT` / `REITs` → 都列入
- `PyQt` / `pyqt` / `PyQt5` → 大小写不敏感匹配覆盖

---

## 五、匹配与计分算法

### 5.1 输入
每条对话：
- **标题文本**：从文件名提取（去掉日期前缀和 `.md` 后缀）
- **正文文本**：读取 `.md` 文件全部内容

### 5.2 扫描方式（flashtext + count 组合）

采用两阶段策略：

1. **flashtext 快速筛选**：用 `KeywordProcessor` 做一次非重叠扫描，找出文本中**出现了哪些关键词**（过滤掉 ~130 个不存在的）
2. **`str.count()` 精确计数**：对筛选出的关键词逐一调用 `text_lower.count(kw_lower)` 做精确匹配，支持**重叠计数**

这样兼顾了速度（不用对 150 个关键词逐个 count）和正确性（与原方案行为一致，支持重叠匹配）。

### 5.3 计分公式

对于每个类别 C 中的每个关键词 K：

```
命中得分 = 标题命中次数 × 10 × 权重 + 正文命中次数 × 1 × 权重
```

**特殊规则**：
- 如果 K 的权重 ≤ 0.5 且正文命中次数 < 3，则正文部分得分 = 0（标题部分不受影响）

### 5.4 类别总分
类别 C 的总分 = C 内所有关键词的命中得分之和

### 5.5 标签决策

```
输入：该对话对所有类别的得分列表
输出：1~2 个标签 或 "待分类"

步骤：
1. 过滤：丢弃总分 < 3 的类别（阈值可调）
2. 排序：剩余类别按得分降序排列
3. 截断：取前 2 个作为标签
4. 兜底：如果剩余类别数为 0，标记为"待分类"
```

### 5.6 性能数据
全量 2276 条对话耗时约 **3~9 秒**，平均每文件 **1.5~3.7ms**。

---

## 六、初始映射表的构建方法

### 6.1 冷启动三步走

**第一步：从文件名捞高频词**
- 扫描所有对话文件名，提取中文词和英文词
- 统计词频，输出 Top N 列表
- 人工扫一眼，将有明显领域归属的词拖入对应类别

**第二步：凭领域直觉主动补全**
- 回忆自己聊过的话题，补充必然出现但文件名未必体现的词
- 原则：**宁可漏掉，不要误加**（漏掉的会被后续迭代发现，误加的会制造错误归类）

**第三步：用第一轮结果反哺**
- 运行脚本，查看 `unmatched_words.csv`（jieba 分词生成的高频词报告）
- 将报告中明显属于某类别的新词加入映射表
- 重跑脚本，覆盖率逐步收敛

### 6.2 映射表维护策略
- 映射表独立为 `keyword_map.json`，与脚本逻辑分离
- 每次修改映射表后重跑脚本即可生效
- 不加"可能有用"的词，只加"确信属于某类别"的词

---

## 七、输出物

### 7.1 分类概要 CSV
**文件名**：`category_summary.csv`

**内容**：父类,子类,条数 三级数据，按 JSON 顺序排列。

| 列名 | 说明 | 示例 |
|------|------|------|
| `parent` | 父类名称 | `金融投资` |
| `child` | 子类名称 | `股票基金` |
| `count` | 该子类的对话数量 | `312` |

**用途**：一眼看清各主题分布概览。

### 7.2 主题索引 Markdown
**文件名**：`topic_index.md`

**内容**：带编号的层级 Markdown，父类用 `## 1.` 编号，子类用 `### 1.1` 编号。

```markdown
## 1. 金融投资（568条）
### 1.1 股票基金（312条）
- 对话标题
### 1.2 债券套利（98条）
- 对话标题
```

**用途**：快速浏览全貌，定位特定主题对话。

### 7.3 详细得分日志 CSV
**文件名**：`score_log.csv`

**表结构**：

| 列名 | 说明 | 示例 |
|------|------|------|
| `file_path` | 对话文件相对路径 | `2025/01_January/xxx.md` |
| `category` | 匹配到的类别名称 | `金融投资/股票基金` |
| `keyword_hits` | 具体命中关键词及次数 | `股票(标题×1,正文×8)` |
| `title_score` | 标题命中得分 | `20.0` |
| `body_score` | 正文命中得分 | `15.0` |
| `total_score` | 该类别总分 | `35.0` |
| `assigned_tags` | 最终分配标签 | `金融投资/股票基金, Python/基础语法` |

**用途**：抽查归类合理性，校准阈值。

### 7.4 待分类高频词报告 CSV
**文件名**：`unmatched_words.csv`

**表结构**：

| 列名 | 说明 | 示例 |
|------|------|------|
| `word` | jieba 分词提取的词或短语 | `除权` |
| `total_frequency` | 在所有待分类对话中累计出现次数 | `30` |
| `file_count` | 出现在几个不同对话文件中 | `5` |

**核心机制——"新词发现器"**：
- 用 jieba 精确模式对"待分类"对话做分词
- 过滤停用词后按次数降序排列
- 用户在报告中看到"除权"出现 30 次，判断它属于"金融投资"，手动加入映射表
- 重跑脚本后，这些对话就会命中新关键词，离开"待分类"

**用途**：发现映射表中遗漏的关键词，反哺映射表扩充。

### 7.5 手动标签覆盖文件
**文件名**：`manual_tags.json`

**结构**：
```json
{
  "2025/01_January/xxx.md": ["金融投资/股票基金"],
  "2025/03_May/yyy.md": ["Python/基础语法", "音视频/编码封装"]
}
```

**用途**：
- 用户手工修正的标签持久化存储
- 脚本运行时优先读取，已有条目跳过自动分类
- 确保手工修正不会被重跑覆盖

---

## 八、迭代工作流

```
编辑 keyword_map.json → 跑脚本 → 检查输出
├── 看 category_summary.csv → 各主题分布是否合理
├── 看 topic_index.md      → 覆盖率是否满意
├── 看 score_log.csv       → 调整阈值/权重
├── 看 unmatched_words.csv → 发现新词 → 加入映射表
├── 发现错误归类           → 写入 manual_tags.json
└── 重跑脚本               → 覆盖率提升
                                  ↓
                            满意为止
```

通常 2~3 轮即可达到 90% 以上覆盖率。

---

## 九、技术选型

| 要求 | 选型 |
|------|------|
| 语言 | Python 3 |
| 依赖 | `flashtext`（多模式匹配）、`jieba`（中文分词） |
| 标准库 | `os`、`re`、`pathlib`、`json`、`csv`、`time` |
| 存储 | 文本文件（Markdown + CSV + JSON），无需数据库 |

---

## 十、与后续阶段衔接

| 阶段 | 内容 | 依赖本方案产出 |
|------|------|---------------|
| Phase 2 标签入库 | 将标签数据导入 pro5 数据库 `tags` 字段 | `score_log.csv` 中的 `file_path` + `assigned_tags` |
| Phase 3 前端交互 | 标签筛选、自动补全、可视化 | 数据库中已入库的标签数据 |
| 手动修正长期化 | `manual_tags.json` 作为持久化的用户纠错层 | 本方案已预留 |

---

## 十一、实现日志

### 2026-06-19 初始实现
- 完成 `deepseek_conversation_topic_classifier.py` 和 `keyword_map.json`
- 采用逐关键词 `str.count()` 匹配，13 个一级分类，150+ 关键词
- 输出 4 个文件：`topic_index.md`、`score_log.csv`、`unmatched_words.csv`、`manual_tags.json`
- 首轮覆盖率 91.7%

### 优化记录
- **第 1 轮**：修复无用 import、清理 `ensure_output_dir()`、加固除零风险
- **第 2 轮**：添加每步时间统计
- **第 3 轮**：缓存 title_lower/body_lower，避免 extract_unmatched_words 重复读文件
- **第 4 轮**：用 `flashtext` 替代逐关键词 `.count()`，配合 `str.count()` 精确计数
- **第 5 轮**：修复 `kw_info` 多类别覆盖 Bug（改为列表存储）
- **第 6 轮**：`split_text_into_words` 由 2-6 字滑动窗口改为 jieba 精确模式分词
- **第 7 轮**：分类体系改为 `父类/子类` 层级结构，输出带编号，输出顺序按 JSON
- **第 8 轮**：新增 `category_summary.csv` 概要统计
- **第 9 轮**：精简 `score_log.csv`，去冗余 title 列；file_path 相对路径化

---


## 对话主题分布统计（分类结果集成）

将离线分类脚本的产出集成到主程序统计大屏，实现「主题分布可视化」。

---

## 一、数据链路

```
分类脚本（离线）
  │  输出 category_summary.csv
  ▼
scripts/output/category_summary.csv       ← 原始输出
  │
  │  同步副本（脚本自动）
  ▼
llm_conversation_archives/deepseek_data-merged/category_summary.csv  ← 主程序读取
  │
  │  GET /api/deepseek/stats/topics
  ▼
FastAPI 后端读 CSV → JSON          ← src/routes.py
  │
  │  fetch JSON
  ▼
统计大屏底部「🎯 对话主题分布」         ← static/js/ds-calendar.js
```

### 为什么走 CSV 而非入库
- 分类脚本离线运行，CSV 是其标准产出
- CSV 可被多个组件独立消费，降低耦合
- 后端读 CSV 零依赖，DB 无变动，回滚零成本
- 后续 Phase 2 标签入库后可升级为 DB 查询

---

## 二、后端 API

### `GET /api/deepseek/stats/topics`

**路径：** `src/routes.py`（位于 `deepseek_stats()` 之后、`_parse_file_metadata()` 之前）

**行为：**
1. 检查 `llm_conversation_archives/deepseek_data-merged/category_summary.csv` 是否存在
2. 存在则解析、按父类聚合子类、计算百分比
3. 不存在则返回空的 `{"parents": [], "total": 0}`

**响应结构：**
```json
{
  "parents": [
    {
      "parent": "金融投资",
      "total": 1187,
      "pct": 27,
      "children": [
        {"child": "债券套利", "count": 86},
        {"child": "期权期货", "count": 70},
        {"child": "理财宏观", "count": 546},
        {"child": "股票基金", "count": 485}
      ]
    }
  ],
  "total": 4384
}
```

- `total` 是所有子类 count 之和（含双标签重复计数）
- `pct` 是父类 `total` 占 `total` 的百分比，用于前端进度条

---

## 三、前端实现

### 3.1 页面位置

位于统计大屏 `renderStatsDashboard()` 中，**对话时长分布之后、数据更新页脚之前**。

加载方式：与统计页面**同步加载**（方案 A），在 HTML 渲染完成后并行 fetch，不阻塞首屏展示。

### 3.2 渲染函数

**`renderTopicDistribution(data)`** — `static/js/ds-calendar.js`

核心逻辑：
1. 遍历 `data.parents`，为每个父类生成一行 `stats-legend-item`（复用统计页已有样式）
2. 对每个父类的 children 列表，生成缩进子类行（带 `├` / `└` 树形连线符）
3. 父类颜色固定 12 色轮换，与模型分布视觉一致

### 3.3 视觉结构

```
┌─ 🎯 对话主题分布 ─────────────────────────────┐
│                                                 │
│  ● 金融投资       ████████████████████  1187条 27% │
│    ├ 理财宏观                         546条      │
│    ├ 股票基金                         485条      │
│    ├ 债券套利                          86条      │
│    └ 期权期货                          70条      │
│                                                 │
│  ● Python         ████████████████     454条 10% │
│    ├ 基础语法                         382条      │
│    ├ 数据处理                          66条      │
│    ├ Web框架                            2条      │
│    └ 日志工具                           4条      │
│  ...                                           │
└─────────────────────────────────────────────────┘
```

### 3.4 CSS 样式

三点新增样式（`static/css/stats.css`）：

| 类名 | 用途 |
|------|------|
| `.topic-child-item` | 子类行布局（flex，padding-left: 28px 缩进） |
| `.topic-child-icon` | `├` / `└` 符号（定宽 14px 居中） |
| `.topic-child-label` | 子类名称（flex:1 自适应） |
| `.topic-child-count` | 对话数（右对齐 40px） |

---

## 四、分类脚本修改

**脚本：** `scripts/deepseek_conversation_topic_classifier.py`

在输出 `category_summary.csv` 到 `scripts/output/` 后，额外同步一份到归档根目录：

```python
SYNC_ARCHIVE_ROOT = Path("/data_sdb/openclaw/.../llm_conversation_archives/deepseek_data-merged")

# 同步到归档根目录（供主程序 stats 使用）
if SYNC_ARCHIVE_ROOT.exists():
    sync_path = SYNC_ARCHIVE_ROOT / "category_summary.csv"
    generate_summary_csv(results, sync_path, parent_order)
    print(f"      📎 同步到: {sync_path}")
```

---

## 五、依赖关系

| 前置条件 | 说明 |
|---------|------|
| 分类脚本至少跑过一次 | 生成 `category_summary.csv` 并同步到归档目录 |
| 主程序重新启动 | 新路由和前端代码需加载 |
| 统计大屏打开 | 主题分布区块在统计大屏底部 |

**缺失 CSV 时的行为：** 前端显示"暂无分类数据"提示，不会崩溃或影响其他统计功能。

---

## 六、后续扩展方向

| 方向 | 说明 | 依赖 |
|------|------|------|
| 分类信息入库 | 将 tags 写入 `conversation_status` 表 | Phase 2 |
| 对话列表按主题筛选 | 存档管理页增加主题下拉筛选 | 标签入库后 |
| 主题 × 时间趋势图 | 按月份展示各主题对话量变化 | 标签入库后 |
| 主题 × 归档进度 | 展示各主题中 raw/archived/deleted 比例 | 标签入库后 |
| 实时自动分类 | 主程序启动时自动调用分类脚本 | 独立 |

---

_文档版本：v1.0_
_创建日期：2026-06-19_
