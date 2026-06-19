# 词云功能开发方案

## 一、需求概述

在统计大屏中增加一个「主题词云 / 标签云」模块，将用户对话的核心主题以可视化方式呈现，一眼看出近期在聊什么。

---

## 二、数据来源评估

### 2.1 可选数据源

| 数据源 | 内容 | 精度 | 获取成本 |
|--------|------|------|----------|
| **会话标题** | 每条对话的 `title` 字段 | 🟡 标题通常概括了主题 | 🟢 已在 `_data.json` |
| **会话消息内容** | 全部对话文本 | 🟢 最精确 | 🔴 需解析 Markdown 或原始 JSON |
| **消息 metadata** | `request_length`, `thinking_length` 等 | ❌ 不可用（非文本） | — |

### 2.2 推荐方案：标题级词云（第一阶段）

从 `_data.json` 中已有的 `title` 字段提取关键词。标题是用户自己概括的，天然具有"主题"属性，虽然信息密度不如全文，但获取成本为零。

### 2.3 未来升级：全文级词云（第二阶段）

解析 Markdown 文件正文做全量分词，精度更高，但需处理文件 I/O 和体量问题。

---

## 三、技术架构

```
┌─────────────────────────────────────────────┐
│                  前端                         │
│  ┌──────────────┐   ┌─────────────────────┐  │
│  │ Canvas 词云   │   │ CSS 标签云（备用方案）│  │
│  │ 螺旋布局算法   │   │ flex-wrap + 字体大小 │  │
│  └──────┬───────┘   └─────────────────────┘  │
└─────────┼───────────────────────────────────┘
          │ GET /api/deepseek/stats
          │ (word_cloud 字段)
┌─────────┼───────────────────────────────────┐
│         ▼           后端                      │
│  ┌──────────────────────────────────────┐    │
│  │ 词频统计模块 (stats endpoint 内)      │    │
│  │                                      │    │
│  │  1. 从 _data.json 读取所有 title      │    │
│  │  2. jieba 分词 + 停用词过滤           │    │
│  │  3. 聚合统计 → top N 返回             │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

---

## 四、后端开发方案

### 4.1 依赖

```bash
pip install jieba
```

### 4.2 停用词表

需要一个基础中文停用词表（约 200 词），过滤"的、了、是、在、我、有、和、就、不、人、都、一、一个、上、也、很、到、说、要、去、你、会、着、没有、看、好、自己、这"等无意义词。

停用词表可以内置在代码中（小），也可以从文件加载。

### 4.3 代码位置

在 `routes.py` 的 `deepseek_stats()` 函数中，遍历会话时增加词频统计：

```python
import jieba

# 停用词表
STOP_WORDS = set("的 了 是 在 我 有 和 就 不 人 都 一 ...".split())

# 在会话循环中
title = s.get("title", "") or ""
if title:
    words = jieba.lcut(title)
    for w in words:
        w = w.strip().lower()
        if len(w) >= 2 and w not in STOP_WORDS and not w.isdigit():
            word_freq[w] = word_freq.get(w, 0) + 1
```

### 4.4 返回结构

在 stats 响应中增加字段：

```json
"word_cloud": [
  { "word": "宏观经济", "count": 28 },
  { "word": "代码", "count": 25 },
  { "word": "A股", "count": 22 },
  { "word": "投资", "count": 18 },
  ...
]
```

按 `count` 降序排列，取 top 50。

### 4.5 性能考虑

- `_data.json` 已经全量加载到内存，title 字段提取无额外 I/O
- jieba 首次加载需要初始化词典（秒级），后续调用很快
- `jieba.lcut()` 一次约 0.1ms，1000 条标题约 100ms，可接受

### 4.6 后端工作量

| 项目 | 行数 | 说明 |
|------|------|------|
| 停用词表 | ~5 | 内联定义 |
| 词频统计 | ~15 | 在会话循环中加 |
| 排序输出 | ~5 | top N |
| **合计** | **~25 行** | |

---

## 五、前端开发方案

### 5.1 方案 A：Canvas 词云（推荐）

用 `<canvas>` 绘制真正的词云。

**算法核心：螺旋放置**

```
1. 根据词频计算每个词的字体大小（12px ~ 48px）
2. 测量每个词渲染后的宽高
3. 从画布中心开始，沿阿基米德螺旋线向外搜索
4. 在搜索位置检查新词与已放置词是否有碰撞
5. 无碰撞则放置，有碰撞则继续沿螺旋搜索
```

**碰撞检测：**
- 使用离屏 Canvas（offscreen canvas）逐像素检测 + 矩形包围盒混合
- 或纯矩形包围盒（性能更好，但密集时可能有细微重叠）

**伪代码：**

```javascript
function drawWordCloud(canvas, words) {
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const placed = [];

  words.sort((a, b) => b.count - a.count);
  const maxCount = words[0].count;

  for (const w of words) {
    const fontSize = 12 + (w.count / maxCount) * 36; // 12-48px
    ctx.font = `bold ${fontSize}px sans-serif`;
    const metrics = ctx.measureText(w.word);
    const tw = metrics.width;
    const th = fontSize * 1.2;

    // 螺旋搜索
    let angle = 0;
    let found = false;
    while (!found && angle < Math.PI * 16) {
      const r = angle * 2;
      const x = cx + r * Math.cos(angle) - tw / 2;
      const y = cy + r * Math.sin(angle) - th / 2;
      if (!collides(placed, x, y, tw, th, ctx)) {
        placed.push({ x, y, w, tw, th, fontSize });
        ctx.fillStyle = randomColor();
        ctx.fillText(w.word, x, y + th);
        found = true;
      }
      angle += 0.1;
    }
  }
}
```

**碰撞检测：**

```javascript
function collides(placed, x, y, tw, th, ctx) {
  // 检查边界
  if (x < 0 || y < 0 || x + tw > ctx.canvas.width || y + th > ctx.canvas.height) return true;
  // 检查与已放置词的重叠
  for (const p of placed) {
    if (x < p.x + p.tw && x + tw > p.x && y < p.y + p.th && y + th > p.y) return true;
  }
  return false;
}
```

**约 80-120 行代码。**

### 5.2 方案 B：CSS 标签云（简化版）

不需要画布，直接用 DOM 元素：

```html
<div class="tag-cloud">
  <span style="font-size: 32px">宏观经济</span>
  <span style="font-size: 28px">代码</span>
  <span style="font-size: 24px">A股</span>
  ...
</div>
```

```css
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  padding: 16px;
  line-height: 1.8;
}
.tag-cloud span {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(74, 144, 217, 0.1);
  transition: transform 0.2s;
  cursor: default;
}
.tag-cloud span:hover {
  transform: scale(1.1);
}
```

**约 20 行 HTML + 20 行 CSS**，但有重叠问题，密集时文本会交错。

### 5.3 方案 C：主题热词列表（最简版）

不做词云，做成按频次排列的横条图（复用现有 legend 样式）：

```
宏观经济 ████████████████ 28
代码     ██████████████  25
A股      ████████████    22
投资     █████████       18
```

**约 10 行模板代码**，信息密度最高，但视觉效果最弱。

---

## 六、方案对比

| 维度 | 方案 A Canvas 词云 | 方案 B CSS 标签云 | 方案 C 热词列表 |
|------|:------------------:|:-----------------:|:--------------:|
| 视觉效果 | ⭐⭐⭐ 最佳 | ⭐⭐ 尚可 | ⭐ 一般 |
| 开发难度 | ⭐⭐⭐ 较难 | ⭐ 简单 | ⭐ 很简单 |
| 代码量 | ~120 行 | ~40 行 | ~15 行 |
| 运行性能 | 🟡 中等（Canvas 绘制） | 🟢 好 | 🟢 好 |
| 交互性 | 🟡 有限 | 🟢 天然 DOM 可交互 | 🟢 可交互 |
| 移动端适配 | 🟡 需要额外处理 | 🟢 flex-wrap 自适应 | 🟢 自适应 |

### 推荐路线

```
第一阶段 → 方案 C（热词列表）  简单好做，快速上线
第二阶段 → 方案 A（Canvas 词云）提升视觉效果
```

---

## 七、实施步骤

### Phase 1：后端 + 热词列表（0.5 天）

1. `pip install jieba`
2. `routes.py` 增加词频统计 ~25 行
3. `ds-calendar.js` 增加热词列表区域 ~15 行
4. `index.css` 增加标签样式 ~15 行

### Phase 2：Canvas 词云（1-2 天）

1. 实现螺旋放置算法 ~80 行
2. 实现碰撞检测 ~20 行
3. 颜色生成、字体缩放 ~20 行
4. 响应式 + 深色模式适配
5. 替换或补充热词列表

---

## 八、风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| jieba 首次加载慢 | 首次 stats 请求延迟 ~2s | 启动时预加载 jieba 词典 |
| 标题过短 | 关键词太少，词云稀疏 | 如标题不足则提取文件名中的关键词 |
| 英文内容 | jieba 对纯英文分词效果差 | 英文部分直接用空格 split 补充 |
| 画布模糊 | 高 DPI 屏幕上 Canvas 模糊 | `canvas.width = size * devicePixelRatio` |
| 词云布局时间长 | 超过 200 词时布局慢 | 限制 top 50 词 |

---

## 九、附录

### 9.1 颜色方案

```javascript
const CLOUD_COLORS = [
  '#4a90d9', '#50c878', '#f5a623', '#ff7a59',
  '#d973bf', '#7b61ff', '#d93025', '#30a14e',
  '#216e39', '#9be9a8', '#e8a838', '#5dade2',
];
```

随机分配，每个词一种颜色，同色不连续出现。

### 9.2 词云尺寸

- 容器：与 `stats-section` 同宽（max 960px）
- 画布：750 × 300 px（可配置）
- 字号范围：12px（低频）~ 48px（高频）
- 最多显示：50 个词

### 9.3 停用词表示例

```
的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到
说 要 去 你 会 着 没有 看 好 自己 这 他 她 它 们 什么
怎么 如何 为什么 哪个 哪里 谁 时候 时间 觉得 应该 可以
能 让 把 被 从 对 与 为 以 及 等 或 但 而 如果 因为
所以 但是 而且 虽然 只是 不过 还是 就是 这个 那个 这些
那些 已经 还是 没有 不是 非常 比较 一定 可能 需要
关于 对于 通过 进行 使用 利用 采用 提出 提供 实现
```
