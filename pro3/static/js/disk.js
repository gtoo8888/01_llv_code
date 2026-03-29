// 磁盘信息

function updateDiskInfo(diskData) {
    const primaryContainer = document.getElementById('disk-primary-container');
    const othersContainer = document.getElementById('disk-others-container');
    
    // 渲染主要磁盘
    if (diskData.primary && diskData.primary.length > 0) {
        primaryContainer.innerHTML = diskData.primary.map(disk => `
            <div class="disk-item disk-primary">
                <div class="disk-header">
                    <span class="disk-mountpoint">${disk.mountpoint}</span>
                    <span class="disk-percent">${disk.percent.toFixed(1)}%</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${disk.percent}%"></div>
                </div>
                <div class="disk-info">
                    <span>已用: ${disk.used} GB</span>
                    <span>总量: ${disk.total} GB</span>
                </div>
            </div>
        `).join('');
    } else {
        primaryContainer.innerHTML = '<p>暂无主要磁盘信息</p>';
    }
    
    // 渲染其他磁盘
    if (diskData.others && diskData.others.length > 0) {
        othersContainer.innerHTML = diskData.others.map(disk => `
            <div class="disk-item disk-other">
                <div class="disk-header">
                    <span class="disk-mountpoint">${disk.mountpoint}</span>
                    <span class="disk-percent">${disk.percent.toFixed(1)}%</span>
                </div>
                <div class="progress-bar-container small">
                    <div class="progress-bar" style="width: ${disk.percent}%"></div>
                </div>
                <div class="disk-info">
                    <span>${disk.used} / ${disk.total} GB</span>
                </div>
            </div>
        `).join('');
    } else {
        othersContainer.innerHTML = '';
    }
}
