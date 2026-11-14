// 网络信息

// 字节/秒 自适应单位
function fmtBps(v) {
    v = v || 0;
    if (v < 1024) return v.toFixed(0) + ' B/s';
    if (v < 1024 * 1024) return (v / 1024).toFixed(1) + ' KB/s';
    return (v / 1048576).toFixed(2) + ' MB/s';
}

// 累计字节 自适应单位
function fmtBytes(v) {
    v = v || 0;
    if (v < 1024 * 1024) return (v / 1024).toFixed(0) + ' KB';
    if (v < 1024 * 1024 * 1024) return (v / 1048576).toFixed(1) + ' MB';
    return (v / 1073741824).toFixed(2) + ' GB';
}

function updateNetworkInfo(networkData) {
    const container = document.getElementById('network-container');

    if (!networkData || !networkData.interfaces || networkData.interfaces.length === 0) {
        container.innerHTML = '<p>采集中…</p>';
        return;
    }

    let html = networkData.interfaces.map(net => `
        <div class="network-item">
            <div class="network-header">
                <span class="network-interface">${net.interface}</span>
                ${net.link_speed ? `<span class="net-speed-cap">${net.link_speed} Mbps</span>` : ''}
            </div>
            <div class="network-speeds">
                <div class="speed-item up">
                    <span class="speed-icon">↑</span>
                    <span class="speed-value">${fmtBps(net.send_bps)}</span>
                </div>
                <div class="speed-item down">
                    <span class="speed-icon">↓</span>
                    <span class="speed-value">${fmtBps(net.recv_bps)}</span>
                </div>
            </div>
            <div class="network-total">
                <span>总发送: ${fmtBytes(net.total_sent)}</span>
                <span>总接收: ${fmtBytes(net.total_recv)}</span>
            </div>
        </div>
    `).join('');

    const links = networkData.links || [];
    if (links.length > 0) {
        html += `
        <div class="network-item net-links">
            <div class="network-header">
                <span class="network-interface">链路</span>
            </div>
            ${links.map(l => `
                <div class="net-link-row">
                    <span class="net-link-label" title="${l.peer}">${l.label}</span>
                    <span class="net-link-peer">${l.peer}</span>
                    <span class="net-link-rate up">↑${fmtBps(l.send_bps)}</span>
                    <span class="net-link-rate down">↓${fmtBps(l.recv_bps)}</span>
                </div>
            `).join('')}
        </div>`;
    }

    container.innerHTML = html;
}
