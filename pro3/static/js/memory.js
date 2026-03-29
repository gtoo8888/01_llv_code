// 内存相关

// 更新内存 - 带趋势图
function updateMemoryWithHistory(memData, historyData) {
    const memPercent = memData.percent;
    
    // 保存总内存
    memoryHistory.total = memData.total;
    
    // 如果后端有历史数据且前端未初始化，使用后端的
    if (historyData && historyData.memory && historyData.memory.length > 0 && !memoryHistory.initialized) {
        memoryHistory.data = [...historyData.memory];
        memoryHistory.initialized = true;
    } else {
        memoryHistory.data.push(memPercent);
    }
    
    // 确保不超过最大点数
    while (memoryHistory.data.length > memoryHistory.maxPoints) {
        memoryHistory.data.shift();
    }
    
    // 更新数值显示
    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
    document.getElementById('memory-used').textContent = memData.used;
    document.getElementById('memory-total').textContent = memData.total;
    
    // 绘制折线图
    drawMemoryChart();
}

// 重置内存当前点
function resetMemoryActivePoint() {
    memoryHistory.activeIndex = -1;
    drawMemoryChart();
}
