// 指数行情 JS

// 当前数据
let currentData = [];

// 当前选中的日期（默认为今天）
let selectedDate = new Date();

// 排序状态
let sortState = {
    field: 'order',
    direction: 'asc'
};

// 格式化日期为 YYYY-MM-DD
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// 格式化日期为中文显示
function formatDateChinese(date) {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    const weekday = weekdays[date.getDay()];
    return `${year}年${month}月${day}日 ${weekday}`;
}

// 初始化日期选择器
function initDatePicker() {
    const datePicker = document.getElementById('date-picker');
    const dateHint = document.getElementById('date-hint');
    
    // 设置默认值为今天
    const today = new Date();
    selectedDate = today;
    const todayStr = formatDate(today);
    datePicker.value = todayStr;
    dateHint.textContent = formatDateChinese(today);
    
    // 使用 Flatpickr 初始化日期选择器
    flatpickr(datePicker, {
        dateFormat: "Y-m-d",
        maxDate: todayStr,  // 不能选今天之后
        locale: "zh",       // 中文
        theme: "material_blue",  // 主题
        onChange: function(selectedDates, dateStr) {
            if (selectedDates.length > 0) {
                selectedDate = selectedDates[0];
                dateHint.textContent = formatDateChinese(selectedDate);
                // 选择新日期后，显示等待抓取提示
                showWaiting();
            }
        }
    });
}

// 显示等待状态
function showWaiting() {
    const tbody = document.getElementById('indices-tbody');
    const selectedDateStr = formatDateChinese(selectedDate);
    tbody.innerHTML = `
        <tr>
            <td colspan="7" style="text-align: center; padding: 40px; color: #6b7280;">
                <span>📡 已选择日期: ${selectedDateStr}，点击"刷新数据"按钮抓取数据</span>
            </td>
        </tr>
    `;
    document.getElementById('update-time').textContent = '--';
}

// 显示加载状态
function showLoading() {
    const tbody = document.getElementById('indices-tbody');
    const selectedDateStr = formatDateChinese(selectedDate);
    tbody.innerHTML = `
        <tr>
            <td colspan="7" style="text-align: center; padding: 40px; color: #6b7280;">
                <span>⏳ 正在获取 ${selectedDateStr} 的数据...</span>
            </td>
        </tr>
    `;
    // 显示进度条
    document.getElementById('progress-container').style.display = 'flex';
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('progress-text').textContent = '0%';
}

// 停止进度轮询
let progressPollingInterval = null;

function stopProgressPolling() {
    if (progressPollingInterval) {
        clearInterval(progressPollingInterval);
        progressPollingInterval = null;
    }
    // 隐藏进度条
    setTimeout(() => {
        document.getElementById('progress-container').style.display = 'none';
    }, 500);
}

// 轮询获取进度
function startProgressPolling() {
    stopProgressPolling();
    
    progressPollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/indices/progress?t=' + Date.now());  // 添加时间戳防止缓存
            const progress = await response.json();
            
            const percent = progress.percent;
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');
            
            if (progressFill && progressText) {
                progressFill.style.width = `${percent}%`;
                progressText.textContent = `${percent}% (${progress.current}/${progress.total})`;
            }
            
            // 如果完成，停止轮询
            if (progress.status === 'completed') {
                stopProgressPolling();
            }
        } catch (error) {
            console.error('获取进度失败:', error);
        }
    }, 500);  // 改为500ms轮询
}

// 从后端获取指数数据
async function fetchIndicesData() {
    // 显示加载状态
    showLoading();
    
    try {
        const dateStr = formatDate(selectedDate);
        
        // 先启动轮询（不等待）
        startProgressPolling();
        
        // 再调用 API
        const response = await fetch(`/api/indices?date=${dateStr}`);
        const result = await response.json();
        
        if (result.data) {
            currentData = result.data;
            // 更新时间
            document.getElementById('update-time').textContent = result.updateTime || formatDateChinese(selectedDate);
            renderTable();
        }
    } catch (error) {
        console.error('获取指数数据失败:', error);
        const tbody = document.getElementById('indices-tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: #dc2626;">
                    <span>❌ 获取数据失败，请刷新重试</span>
                </td>
            </tr>
        `;
    }
}

// 从后端获取指数数据
async function fetchIndicesData() {
    // 显示加载状态
    showLoading();
    
    try {
        const dateStr = formatDate(selectedDate);
        const response = await fetch(`/api/indices?date=${dateStr}`);
        const result = await response.json();
        
        if (result.data) {
            currentData = result.data;
            // 更新时间
            document.getElementById('update-time').textContent = result.updateTime || formatDateChinese(selectedDate);
            renderTable();
        }
    } catch (error) {
        console.error('获取指数数据失败:', error);
        const tbody = document.getElementById('indices-tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: #dc2626;">
                    <span>❌ 获取数据失败，请刷新重试</span>
                </td>
            </tr>
        `;
    }
}

// 渲染表格（使用 DocumentFragment 减少重排）
function renderTable() {
    const tbody = document.getElementById('indices-tbody');
    
    // 使用 DocumentFragment 一次性插入
    const fragment = document.createDocumentFragment();
    
    currentData.forEach(row => {
        const tr = document.createElement('tr');
        
        // 处理空数据
        const current = row.current !== null ? row.current : '--';
        const change = row.change !== null ? row.change : '--';
        const changeAmt = row.changeAmt !== null ? row.changeAmt : '--';
        const volume = row.volume !== null ? row.volume : '--';
        
        // 涨跌幅样式
        let changeClass = 'neutral';
        let changeSign = '';
        
        if (row.change !== null) {
            if (row.change > 0) changeClass = 'positive';
            else if (row.change < 0) changeClass = 'negative';
            changeSign = row.change > 0 ? '+' : '';
        }
        
        // 格式化数值
        const currentStr = typeof current === 'number' 
            ? current.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})
            : current;
        const volumeStr = typeof volume === 'number'
            ? volume.toLocaleString('zh-CN')
            : volume;
        
        tr.innerHTML = `
            <td>${row.order}</td>
            <td>${row.code}</td>
            <td>${row.name}</td>
            <td class="numeric">${currentStr}</td>
            <td class="numeric ${changeClass}">${change === '--' ? change : changeSign}${change === '--' ? '' : change.toFixed(2)}%</td>
            <td class="numeric ${changeClass}">${change === '--' ? change : changeSign}${change === '--' ? '' : changeAmt.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="numeric">${volumeStr}</td>
        `;
        
        fragment.appendChild(tr);
    });
    
    // 一次性替换，避免闪烁
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    
    // 更新表头排序状态
    updateSortHeaders();
}

// 更新表头排序状态
function updateSortHeaders() {
    document.querySelectorAll('.data-table th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.dataset.sort === sortState.field) {
            th.classList.add(sortState.direction === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });
}

// 排序
function sortData(field) {
    if (sortState.field === field) {
        // 切换方向
        sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
    } else {
        // 新字段，默认升序（序号除外，默认按序号）
        sortState.field = field;
        sortState.direction = field === 'order' ? 'asc' : 'asc';
    }
    
    // 排序（null 值排到最后）
    currentData.sort((a, b) => {
        let valA = a[field];
        let valB = b[field];
        
        // null 值处理
        if (valA === null && valB === null) return 0;
        if (valA === null) return 1;
        if (valB === null) return -1;
        
        if (typeof valA === 'string') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
        }
        
        if (valA < valB) return sortState.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortState.direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    // 重新渲染（不重置序号，保持原顺序）
    renderTableKeepOrder();
}

// 保持序号顺序的渲染（排序后序号不变）
function renderTableKeepOrder() {
    const tbody = document.getElementById('indices-tbody');
    
    const fragment = document.createDocumentFragment();
    
    currentData.forEach(row => {
        const tr = document.createElement('tr');
        
        // 处理空数据
        const current = row.current !== null ? row.current : '--';
        const change = row.change !== null ? row.change : '--';
        const changeAmt = row.changeAmt !== null ? row.changeAmt : '--';
        const volume = row.volume !== null ? row.volume : '--';
        
        // 涨跌幅样式
        let changeClass = 'neutral';
        let changeSign = '';
        
        if (row.change !== null) {
            if (row.change > 0) changeClass = 'positive';
            else if (row.change < 0) changeClass = 'negative';
            changeSign = row.change > 0 ? '+' : '';
        }
        
        // 格式化数值
        const currentStr = typeof current === 'number' 
            ? current.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})
            : current;
        const volumeStr = typeof volume === 'number'
            ? volume.toLocaleString('zh-CN')
            : volume;
        
        tr.innerHTML = `
            <td>${row.order}</td>
            <td>${row.code}</td>
            <td>${row.name}</td>
            <td class="numeric">${currentStr}</td>
            <td class="numeric ${changeClass}">${change === '--' ? change : changeSign}${change === '--' ? '' : change.toFixed(2)}%</td>
            <td class="numeric ${changeClass}">${change === '--' ? change : changeSign}${change === '--' ? '' : changeAmt.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="numeric">${volumeStr}</td>
        `;
        
        fragment.appendChild(tr);
    });
    
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    
    updateSortHeaders();
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化日期选择器
    initDatePicker();
    
    // 页面加载时显示等待提示，不自动抓取
    showWaiting();
    
    // 刷新按钮 - 重新从后端获取数据
    document.getElementById('refresh-btn').addEventListener('click', function() {
        fetchIndicesData();
    });
    
    // 表头排序点击
    document.querySelectorAll('.data-table th.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const field = this.dataset.sort;
            sortData(field);
        });
    });
});
