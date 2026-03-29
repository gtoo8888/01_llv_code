// 主入口

document.addEventListener('DOMContentLoaded', function() {
    // 首次加载数据
    updateData();
    
    // 初始化事件
    initCPUChartEvents();
    initMemoryChartEvents();
    initRefreshInterval();
    initResizeEvent();
});
