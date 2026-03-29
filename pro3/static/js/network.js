// 网络信息

function updateNetworkInfo(networkData) {
    const container = document.getElementById('network-container');
    
    if (!networkData || !networkData.interfaces || networkData.interfaces.length === 0) {
        container.innerHTML = '<p>暂无网络数据</p>';
        return;
    }
    
    container.innerHTML = networkData.interfaces.map(net => `
        <div class="network-item">
            <div class="network-header">
                <span class="network-interface">${net.interface}</span>
            </div>
            <div class="network-speeds">
                <div class="speed-item up">
                    <span class="speed-icon">↑</span>
                    <span class="speed-value">${net.sent_speed} MB/s</span>
                </div>
                <div class="speed-item down">
                    <span class="speed-icon">↓</span>
                    <span class="speed-value">${net.recv_speed} MB/s</span>
                </div>
            </div>
            <div class="network-total">
                <span>总发送: ${net.total_sent} MB</span>
                <span>总接收: ${net.total_recv} MB</span>
            </div>
        </div>
    `).join('');
}
