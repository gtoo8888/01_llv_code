// API 调用

// 更新数据函数 - 调用真实 API
async function updateData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // 更新 CPU
        updateCPUWithHistory(data.cpu, data.history);

        // 更新内存
        updateMemoryWithHistory(data.memory, data.history);

        // 更新磁盘
        updateDiskInfo(data.disk);

        // 更新网络
        updateNetworkInfo(data.network);

        // 更新系统信息（只在首次加载时更新）
        updateSystemInfo(data.system);

        // 更新时间
        const now = new Date();
        document.getElementById('last-update').textContent = now.toLocaleString('zh-CN');
        
    } catch (error) {
        console.error('获取数据失败:', error);
    }
}

// 更新系统信息
let systemInfoInitialized = false;
function updateSystemInfo(systemData) {
    if (!systemInfoInitialized) {
        document.getElementById('hostname').textContent = systemData.hostname;
        document.getElementById('os').textContent = systemData.os;
        document.getElementById('kernel').textContent = systemData.kernel;
        document.getElementById('arch').textContent = systemData.arch;
        document.getElementById('cpu_model').textContent = systemData.cpu_model;
        document.getElementById('cpu_cores').textContent = systemData.cpu_cores;
        document.getElementById('locale').textContent = systemData.locale;
        document.getElementById('timezone').textContent = systemData.timezone;
        systemInfoInitialized = true;
    }
    document.getElementById('uptime').textContent = systemData.uptime;
}
