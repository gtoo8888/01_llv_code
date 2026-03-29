// 折线图绘制

// 绘制 CPU 折线图
function drawCPUChart() {
    const canvas = document.getElementById('cpu-chart');
    const ctx = canvas.getContext('2d');
    
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = 180;
    
    const width = canvas.width;
    const height = canvas.height;
    const padding = 15;
    
    ctx.clearRect(0, 0, width, height);
    
    // 背景网格
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    
    for (let i = 0; i <= 4; i++) {
        const y = padding + (height - 2 * padding) * i / 4;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    if (cpuHistory.data.length < 2) return;
    
    const data = cpuHistory.data;
    const xStep = (width - 2 * padding) / (cpuHistory.maxPoints - 1);
    
    // 渐变填充
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(78, 205, 196, 0.4)');
    gradient.addColorStop(1, 'rgba(78, 205, 196, 0.0)');
    
    ctx.beginPath();
    ctx.moveTo(padding, height - padding);
    
    for (let i = 0; i < data.length; i++) {
        const x = padding + i * xStep;
        const y = height - padding - (height - 2 * padding) * data[i] / 100;
        ctx.lineTo(x, y);
    }
    
    ctx.lineTo(padding + (data.length - 1) * xStep, height - padding);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // 绘制折线
    ctx.beginPath();
    ctx.strokeStyle = '#4ecdc4';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    for (let i = 0; i < data.length; i++) {
        const x = padding + i * xStep;
        const y = height - padding - (height - 2 * padding) * data[i] / 100;
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
    
    // 绘制所有数据点
    for (let i = 0; i < data.length; i++) {
        const x = padding + i * xStep;
        const y = height - padding - (height - 2 * padding) * data[i] / 100;
        
        const isActive = (cpuHistory.activeIndex === -1 && i === data.length - 1) || cpuHistory.activeIndex === i;
        
        if (isActive) {
            ctx.beginPath();
            ctx.arc(x, y, 8, 0, Math.PI * 2);
            ctx.fillStyle = '#4ecdc4';
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            ctx.beginPath();
            ctx.arc(x, y, 14, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(78, 205, 196, 0.4)';
            ctx.fill();
        } else {
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#4ecdc4';
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
    }
}

// 绘制内存折线图
function drawMemoryChart() {
    const canvas = document.getElementById('memory-chart');
    const ctx = canvas.getContext('2d');
    
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = 180;
    
    const width = canvas.width;
    const height = canvas.height;
    const padding = 15;
    
    ctx.clearRect(0, 0, width, height);
    
    // 背景网格
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    
    for (let i = 0; i <= 4; i++) {
        const y = padding + (height - 2 * padding) * i / 4;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    if (memoryHistory.data.length < 2) return;
    
    const data = memoryHistory.data;
    const xStep = (width - 2 * padding) / (memoryHistory.maxPoints - 1);
    
    // 渐变填充
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(102, 126, 234, 0.4)');
    gradient.addColorStop(1, 'rgba(102, 126, 234, 0.0)');
    
    ctx.beginPath();
    ctx.moveTo(padding, height - padding);
    
    for (let i = 0; i < data.length; i++) {
        const x = padding + i * xStep;
        const y = height - padding - (height - 2 * padding) * data[i] / 100;
        ctx.lineTo(x, y);
    }
    
    ctx.lineTo(padding + (data.length - 1) * xStep, height - padding);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // 绘制折线
    ctx.beginPath();
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    for (let i = 0; i < data.length; i++) {
        const x = padding + i * xStep;
        const y = height - padding - (height - 2 * padding) * data[i] / 100;
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
    
    // 绘制所有数据点
    for (let i = 0; i < data.length; i++) {
        const x = padding + i * xStep;
        const y = height - padding - (height - 2 * padding) * data[i] / 100;
        
        const isActive = (memoryHistory.activeIndex === -1 && i === data.length - 1) || memoryHistory.activeIndex === i;
        
        if (isActive) {
            ctx.beginPath();
            ctx.arc(x, y, 8, 0, Math.PI * 2);
            ctx.fillStyle = '#667eea';
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            ctx.beginPath();
            ctx.arc(x, y, 14, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(102, 126, 234, 0.4)';
            ctx.fill();
        } else {
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#667eea';
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
    }
}
