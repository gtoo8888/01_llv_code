// CPU 相关

// 更新 CPU - 带趋势图
function updateCPUWithHistory(cpuData, historyData) {
    const cpuPercent = cpuData.percent;
    
    // 如果后端有历史数据且前端未初始化，使用后端的
    if (historyData && historyData.cpu && historyData.cpu.length > 0 && !cpuHistory.initialized) {
        cpuHistory.data = [...historyData.cpu];
        cpuHistory.initialized = true;
    } else {
        cpuHistory.data.push(cpuPercent);
    }
    
    // 确保不超过最大点数
    while (cpuHistory.data.length > cpuHistory.maxPoints) {
        cpuHistory.data.shift();
    }
    
    // 更新数值显示
    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
    document.getElementById('cpu-load').textContent = cpuData.load;
    
    // 更新每个核心的显示
    updateCPUCores(cpuData.per_cpu);
    
    // 绘制折线图
    drawCPUChart();
}

// 更新每个 CPU 核心的显示
function updateCPUCores(perCpuData) {
    const container = document.getElementById('cpu-cores-container');
    
    if (!perCpuData || perCpuData.length === 0) return;
    
    container.innerHTML = perCpuData.map((percent, index) => {
        const color = getCpuColor(percent);
        return `
            <div class="cpu-core-item">
                <span class="cpu-core-label">CPU${index}</span>
                <div class="cpu-core-bar-container">
                    <div class="cpu-core-bar" style="width: ${percent}%; background: ${color}"></div>
                </div>
                <span class="cpu-core-percent">${percent.toFixed(0)}%</span>
            </div>
        `;
    }).join('');
}

// 根据 CPU 使用率获取颜色
function getCpuColor(percent) {
    if (percent < 30) return '#2ecc71';
    if (percent < 60) return '#f39c12';
    if (percent < 85) return '#e74c3c';
    return '#9b59b6';
}

// 重置 CPU 当前点
function resetCpuActivePoint() {
    cpuHistory.activeIndex = -1;
    drawCPUChart();
}
