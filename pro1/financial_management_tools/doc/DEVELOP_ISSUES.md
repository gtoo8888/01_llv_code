# 指数行情开发问题记录

本文档记录开发指数行情功能过程中遇到的问题及解决方案。

---

## 1. akshare 数据获取问题

### 问题：中证红利数据日期异常

**现象：** 获取中证红利(000922)时，返回的数据日期是2019年，而不是当前日期。

**原因：** akshare 接口数据异常

**解决方案：** 在 INDICES_LIST 中标记 `disabled: true`，前端显示为 "--"

```python
{ 'code': '000922', 'name': '中证红利', 'symbol': 'sh000922', 'disabled': True }
```

---

## 2. akshare 日期格式问题

**现象：** 
```
TypeError: strptime() argument 1 must be str, not datetime.date
```

**原因：** akshare 返回的日期字段可能是 `datetime.date` 类型，不是字符串

**解决方案：** 在返回数据时进行类型判断和转换

```python
'date': today['date'].strftime('%Y-%m-%d') if isinstance(today['date'], date) else str(today['date'])
```

---

## 3. 数据库模型 DateTime 导入问题

**现象：**
```
NameError: name 'DateTime' is not defined. Did you mean: 'datetime'?
```

**原因：** SQLAlchemy 的 DateTime 类型需要从 sqlalchemy 导入，不是从 datetime

**解决方案：**

```python
# 错误
from datetime import datetime, date, DateTime

# 正确
from sqlalchemy import create_engine, Column, Integer, Float, String, Date, DateTime
```

---

## 4. 滚动条闪烁问题

**现象：** 表格在页面底部时，滚动条频繁出现/消失，导致视觉闪烁

**解决方案：**

1. CSS 优化
```css
.table-container {
    overflow-x: auto;
    overflow-y: visible;
    scrollbar-gutter: stable;
}

.data-table {
    min-width: 800px;
    table-layout: fixed;
}
```

2. JS 优化 - 使用 DocumentFragment 批量插入 DOM
```javascript
const fragment = document.createDocumentFragment();
// ... 添加内容 ...
tbody.appendChild(fragment);
```

---

## 5. 防反爬策略

**要求：** 每个指数获取间隔1秒

**实现：**
```python
# 获取数据后间隔1秒
time.sleep(1)
```

**影响：** 10个指数需要约10秒完成抓取

---

## 6. 前端自动抓取问题

**现象：** 页面加载时自动调用 API，导致每次进入页面都要等待10秒

**解决方案：**
1. 页面加载时显示 "等待数据抓取" 提示
2. 点击刷新按钮才调用 API

```javascript
// 页面加载时
function showWaiting() {
    const tbody = document.getElementById('indices-tbody');
    tbody.innerHTML = `<tr><td colspan="7">📡 等待数据抓取...</td></tr>`;
}
```

---

## 7. 空数据排序问题

**现象：** 当某些指数数据为空时，排序会出现 null 值排序异常

**解决方案：** 在排序函数中处理 null 值

```javascript
currentData.sort((a, b) => {
    let valA = a[field];
    let valB = b[field];
    
    // null 值排到最后
    if (valA === null && valB === null) return 0;
    if (valA === null) return 1;
    if (valB === null) return -1;
    // ... 正常排序
});
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `app/routers/indices.py` | 指数行情路由，包含数据获取和存储逻辑 |
| `app/services/akshare_helper.py` | Akshare 数据抓取工具 |
| `app/models.py` | 数据库模型（Record, IndexQuote） |
| `static/indices.html` | 指数行情页面 |
| `static/js/indices.js` | 前端逻辑 |
| `static/css/indices.css` | 页面样式 |
| `database.db` | SQLite 数据库 |

---

## 8. 日历控件优化

**问题：** 原生 `<input type="date">` 样式丑陋

**解决方案：** 使用 Flatpickr 日历控件

### 引入资源

```html
<!-- CSS -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr@4.6.13/dist/flatpickr.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr@4.6.13/dist/themes/material_blue.css">

<!-- JS -->
<script src="https://cdn.jsdelivr.net/npm/flatpickr@4.6r@4.6.13/dist/l10n/zh.js"></script>
```

### 使用方法

```javascript
flatpickr('#date-picker', {
    dateFormat: "Y-m-d",           // 日期格式
    maxDate: "2026-03-12",         // 最大日期
    locale: "zh",                  // 中文
    theme: "material_blue",        // 主题
    onChange: function(selectedDates, dateStr) {
        // 选择日期后的回调
    }
});
```

### 可用主题

| 主题名称 | 说明 |
|----------|------|
| `material_blue` | 蓝色 Material 风格（默认推荐） |
| `dark` | 暗黑主题 |
| `light` | 浅色主题 |
| `confetti` | 彩色主题 |

---

*文档创建时间: 2026-03-12*
*最后更新: 2026-03-12*
