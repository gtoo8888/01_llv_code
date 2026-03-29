# 指数行情页面优化记录

本文档记录指数行情页面开发过程中的技术优化点。

---

## 1. 滚动条闪烁问题优化

### 问题描述
页面加载或数据刷新时，表格底部滚动条频繁出现/消失，导致视觉闪烁。

### 解决方案

#### CSS 优化

```css
/* 表格容器 */
.table-container {
    overflow-x: auto;
    overflow-y: visible;
    scrollbar-gutter: stable;  /* 预留滚动条空间，防止抖动 */
}

/* 数据表格 */
.data-table {
    min-width: 800px;           /* 固定最小宽度 */
    table-layout: fixed;        /* 固定列宽布局 */
}
```

**优化说明：**
- `overflow-y: visible` - 让容器不因为内容高度变化而产生垂直滚动条
- `scrollbar-gutter: stable` - 浏览器预留滚动条空间，内容区宽度保持稳定
- `min-width` + `table-layout: fixed` - 防止表格宽度因内容计算而频繁变化

---

## 2. DOM 渲染性能优化

### 问题描述
每次刷新或排序时，逐行插入 DOM 导致页面闪烁和性能问题。

### 解决方案

使用 `DocumentFragment` 批量插入 DOM：

```javascript
function renderTable() {
    const tbody = document.getElementById('indices-tbody');
    
    // 创建文档片段（内存中，不影响 DOM）
    const fragment = document.createDocumentFragment();
    
    currentData.forEach(row => {
        const tr = document.createElement('tr');
        // ... 设置 tr 内容 ...
        fragment.appendChild(tr);
    });
    
    // 一次性替换，性能更好
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
}
```

**优化说明：**
- `DocumentFragment` 是轻量级文档对象，在插入 DOM 前在内存中操作
- 一次性 `appendChild` 比多次 append 减少重排（reflow）次数
- 适用于表格、列表等批量数据渲染场景

---

## 3. 注意事项

### 何时使用这些优化

| 场景 | 推荐做法 |
|------|----------|
| 大量数据表格 | DocumentFragment + 虚拟滚动 |
| 固定布局表格 | table-layout: fixed |
| 防止滚动条抖动 | scrollbar-gutter: stable |
| 响应式表格 | 考虑横向滚动 vs 缩放 |

### 兼容性问题

- `scrollbar-gutter` 兼容性良好，现代浏览器都支持
- `table-layout: fixed` 需要确保每列有明确的宽度设置

---

## 4. 相关文件

| 文件 | 说明 |
|------|------|
| `static/css/indices.css` | 页面样式（含优化） |
| `static/js/indices.js` | 页面逻辑（含优化） |
| `static/indices.html` | 页面结构 |

---

*文档创建时间: 2026-03-11*
