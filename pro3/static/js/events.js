// 事件处理

// CPU 图表事件
function initCPUChartEvents() {
    const cpuCanvas = document.getElementById('cpu-chart');
    const cpuTooltip = { elem: null };
    
    // 创建 tooltip
    function createCPUTooltip() {
        const div = document.createElement('div');
        div.className = 'chart-tooltip';
        div.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.85);
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            z-index: 100;
            display: none;
            white-space: nowrap;
        `;
        document.body.appendChild(div);
        return div;
    }
    
    if (!cpuTooltip.elem) {
        cpuTooltip.elem = createCPUTooltip();
    }
    
    cpuCanvas.addEventListener('mousemove', function(e) {
        if (cpuHistory.data.length < 2) return;
        
        const rect = cpuCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const width = rect.width;
        const padding = 15;
        const xStep = (width - 2 * padding) / (cpuHistory.maxPoints - 1);
        
        const index = Math.round((x - padding) / xStep);
        
        if (index >= 0 && index < cpuHistory.data.length) {
            const percent = cpuHistory.data[index];
            cpuTooltip.elem.textContent = `${percent.toFixed(1)}%`;
            cpuTooltip.elem.style.display = 'block';
            cpuTooltip.elem.style.left = (e.clientX + 10) + 'px';
            cpuTooltip.elem.style.top = (e.clientY - 30) + 'px';
        }
    });
    
    cpuCanvas.addEventListener('mouseleave', function() {
        cpuTooltip.elem.style.display = 'none';
        if (cpuResetTimer) clearTimeout(cpuResetTimer);
        cpuResetTimer = setTimeout(resetCpuActivePoint, 5000);
    });
    
    cpuCanvas.addEventListener('click', function(e) {
        if (cpuHistory.data.length < 2) return;
        
        const rect = cpuCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const width = rect.width;
        const padding = 15;
        const xStep = (width - 2 * padding) / (cpuHistory.maxPoints - 1);
        
        const index = Math.round((x - padding) / xStep);
        
        if (index >= 0 && index < cpuHistory.data.length) {
            cpuHistory.activeIndex = index;
            drawCPUChart();
            if (cpuResetTimer) clearTimeout(cpuResetTimer);
        }
    });
}

// 内存图表事件
function initMemoryChartEvents() {
    const memCanvas = document.getElementById('memory-chart');
    const memTooltip = { elem: null };
    
    function createMemTooltip() {
        const div = document.createElement('div');
        div.className = 'chart-tooltip';
        div.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.85);
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            z-index: 100;
            display: none;
            white-space: nowrap;
        `;
        document.body.appendChild(div);
        return div;
    }
    
    if (!memTooltip.elem) {
        memTooltip.elem = createMemTooltip();
    }
    
    memCanvas.addEventListener('mousemove', function(e) {
        if (memoryHistory.data.length < 2) return;
        
        const rect = memCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const width = rect.width;
        const padding = 15;
        const xStep = (width - 2 * padding) / (memoryHistory.maxPoints - 1);
        
        const index = Math.round((x - padding) / xStep);
        
        if (index >= 0 && index < memoryHistory.data.length) {
            const percent = memoryHistory.data[index];
            const usedGB = (memoryHistory.total * percent / 100).toFixed(2);
            memTooltip.elem.innerHTML = `${percent.toFixed(1)}% <span style="color:#aaa">(${usedGB} GB)</span>`;
            memTooltip.elem.style.display = 'block';
            memTooltip.elem.style.left = (e.clientX + 10) + 'px';
            memTooltip.elem.style.top = (e.clientY - 30) + 'px';
        }
    });
    
    memCanvas.addEventListener('mouseleave', function() {
        memTooltip.elem.style.display = 'none';
        if (memoryResetTimer) clearTimeout(memoryResetTimer);
        memoryResetTimer = setTimeout(resetMemoryActivePoint, 5000);
    });
    
    memCanvas.addEventListener('click', function(e) {
        if (memoryHistory.data.length < 2) return;
        
        const rect = memCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const width = rect.width;
        const padding = 15;
        const xStep = (width - 2 * padding) / (memoryHistory.maxPoints - 1);
        
        const index = Math.round((x - padding) / xStep);
        
        if (index >= 0 && index < memoryHistory.data.length) {
            memoryHistory.activeIndex = index;
            drawMemoryChart();
            if (memoryResetTimer) clearTimeout(memoryResetTimer);
        }
    });
}

// 刷新间隔控制
function initRefreshInterval() {
    const select = document.getElementById('refresh-interval');
    const savedInterval = getRefreshInterval();
    
    select.value = savedInterval / 1000;
    document.getElementById('refresh-time-display').textContent = savedInterval / 1000;
    
    select.addEventListener('change', function() {
        const newInterval = parseInt(this.value) * 1000;
        setRefreshInterval(newInterval);
    });
    
    setRefreshInterval(savedInterval);
}

function getRefreshInterval() {
    const saved = localStorage.getItem(REFRESH_INTERVAL_KEY);
    return saved ? parseInt(saved) : 3000;
}

function setRefreshInterval(interval) {
    localStorage.setItem(REFRESH_INTERVAL_KEY, interval);
    document.getElementById('refresh-time-display').textContent = interval / 1000;
    
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(updateData, interval);
}

// 窗口大小变化
function initResizeEvent() {
    window.addEventListener('resize', function() {
        drawCPUChart();
        drawMemoryChart();
    });
}
