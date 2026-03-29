// 理财收益计算器 - 前端逻辑

// DOM 元素
const elements = {
    principal: document.getElementById('principal'),
    startDate: document.getElementById('start_date'),
    endDate: document.getElementById('end_date'),
    incomeStart: document.getElementById('income_start'),
    incomeEnd: document.getElementById('income_end'),
    calculateBtn: document.getElementById('calculate_btn'),
    result: document.getElementById('result'),
    resDays: document.getElementById('res_days'),
    resTotal: document.getElementById('res_total'),
    resDaily: document.getElementById('res_daily'),
    resDaily10k: document.getElementById('res_daily_10k'),
    resAnnual: document.getElementById('res_annual'),
    recordsBody: document.getElementById('records_body'),
    emptyTip: document.getElementById('empty_tip')
};

// 显示提示消息
function showToast(message) {
    // 如果已存在 toast，先移除
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 延迟显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 3秒后自动隐藏
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 加载历史记录
async function loadRecords() {
    try {
        const res = await fetch('/records');
        const data = await res.json();
        
        elements.recordsBody.innerHTML = '';
        
        if (data.length === 0) {
            elements.emptyTip.style.display = 'block';
            return;
        }
        
        elements.emptyTip.style.display = 'none';
        
        data.forEach((record, index) => {
            const tr = document.createElement('tr');
            tr.style.animationDelay = `${index * 0.05}s`;
            tr.innerHTML = `
                <td>${record.principal}</td>
                <td>${record.start_date}</td>
                <td>${record.end_date}</td>
                <td>${record.days}</td>
                <td>${record.total_income}</td>
                <td>${record.daily_income}</td>
                <td>${record.daily_income_per_10k}</td>
                <td>${record.annual_return}%</td>
                <td><button class="btn-delete" data-id="${record.id}">删除</button></td>
            `;
            elements.recordsBody.appendChild(tr);
        });
        
        // 绑定删除按钮事件
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', function() {
                const row = this.closest('tr');
                row.style.animation = 'fadeOut 0.3s ease forwards';
                setTimeout(() => {
                    deleteRecord(parseInt(this.dataset.id));
                }, 300);
            });
        });
    } catch (err) {
        console.error('加载记录失败:', err);
        showToast('加载记录失败');
    }
}

// 验证输入
function validateInput() {
    const { principal, startDate, endDate, incomeStart, incomeEnd } = elements;
    
    if (!principal.value || !startDate.value || !endDate.value || 
        incomeStart.value === '' || incomeEnd.value === '') {
        alert('请填写所有字段');
        return false;
    }
    return true;
}

// 计算并保存
async function calculate() {
    if (!validateInput()) return;
    
    const btn = elements.calculateBtn;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 计算中...';
    
    try {
        const res = await fetch('/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                principal: parseFloat(elements.principal.value),
                start_date: elements.startDate.value,
                end_date: elements.endDate.value,
                income_start: parseFloat(elements.incomeStart.value),
                income_end: parseFloat(elements.incomeEnd.value)
            })
        });
        
        if (!res.ok) {
            const err = await res.json();
            alert(err.detail || '计算失败');
            return;
        }
        
        const data = await res.json();
        
        // 显示结果
        elements.resDays.textContent = data.days;
        elements.resTotal.textContent = data.total_income;
        elements.resDaily.textContent = data.daily_income;
        elements.resDaily10k.textContent = data.daily_income_per_10k;
        elements.resAnnual.textContent = data.annual_return + '%';
        elements.result.classList.add('show');
        
        // 刷新表格
        await loadRecords();
        
        showToast('计算成功！记录已保存');
        
    } catch (err) {
        alert('请求失败: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// 删除记录
async function deleteRecord(id) {
    try {
        const res = await fetch(`/records/${id}`, { method: 'DELETE' });
        if (res.ok) {
            await loadRecords();
            showToast('删除成功');
        } else {
            alert('删除失败');
        }
    } catch (err) {
        alert('删除失败: ' + err.message);
    }
}

// 初始化
function init() {
    elements.calculateBtn.addEventListener('click', calculate);
    
    // 绑定回车键提交
    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                calculate();
            }
        });
    });
    
    loadRecords();
}

// 添加淡出动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        to {
            opacity: 0;
            transform: translateX(-20px);
        }
    }
    tbody tr {
        animation: fadeInUp 0.4s ease forwards;
    }
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
