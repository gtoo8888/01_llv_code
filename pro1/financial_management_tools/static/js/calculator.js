// 收益率计算器 - 前端逻辑

// 显示提示消息
function showToast(message) {
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 显示结果
function showResult(resultDiv, show = true) {
    if (show) {
        resultDiv.classList.add('show');
    } else {
        resultDiv.classList.remove('show');
    }
}

// 5. 数字格式化（千分位）
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// 显示加载动画
function showLoading(btn) {
    const originalText = btn.innerHTML;
    btn.dataset.originalText = originalText;
    btn.innerHTML = '<span class="loading"></span> 计算中...';
    btn.disabled = true;
    return originalText;
}

// 隐藏加载动画
function hideLoading(btn, originalText) {
    btn.innerHTML = originalText;
    btn.disabled = false;
}

// 1. 基本收益率计算
function calculateBasic() {
    const principal = parseFloat(document.getElementById('basic_principal').value);
    const income = parseFloat(document.getElementById('basic_income').value);
    const btn = document.querySelector('#basic_result').previousElementSibling;
    
    if (isNaN(principal) || isNaN(income)) {
        alert('请填写本金和收益');
        return;
    }
    
    if (principal === 0) {
        alert('本金不能为0');
        return;
    }
    
    showLoading(btn);
    
    // 模拟计算延迟（实际项目中可去掉）
    setTimeout(() => {
        const rate = (income / principal) * 100;
        document.getElementById('basic_rate').textContent = rate.toFixed(2) + '%';
        showResult(document.getElementById('basic_result'));
        hideLoading(btn, btn.dataset.originalText);
        showToast('计算完成');
    }, 300);
}

// 2. 年化收益率计算
function calculateAnnual() {
    const principal = parseFloat(document.getElementById('annual_principal').value);
    const income = parseFloat(document.getElementById('annual_income').value);
    const days = parseFloat(document.getElementById('annual_days').value);
    const btn = document.querySelector('#annual_result').previousElementSibling;
    
    if (isNaN(principal) || isNaN(income) || isNaN(days)) {
        alert('请填写所有字段');
        return;
    }
    
    if (principal === 0 || days === 0) {
        alert('本金和天数不能为0');
        return;
    }
    
    showLoading(btn);
    
    setTimeout(() => {
        const annualRate = (income / principal) / days * 365 * 100;
        document.getElementById('annual_rate').textContent = annualRate.toFixed(2) + '%';
        showResult(document.getElementById('annual_result'));
        hideLoading(btn, btn.dataset.originalText);
        showToast('计算完成');
    }, 300);
}

// 3. 复利计算器
function calculateCompound() {
    const principal = parseFloat(document.getElementById('compound_principal').value);
    const rate = parseFloat(document.getElementById('compound_rate').value);
    const years = parseFloat(document.getElementById('compound_years').value);
    const btn = document.querySelector('#compound_result').previousElementSibling;
    
    if (isNaN(principal) || isNaN(rate) || isNaN(years)) {
        alert('请填写所有字段');
        return;
    }
    
    showLoading(btn);
    
    setTimeout(() => {
        // 复利公式: 终值 = 本金 × (1 + 年利率)^年限
        const finalValue = principal * Math.pow(1 + rate / 100, years);
        const totalIncome = finalValue - principal;
        
        document.getElementById('compound_final').textContent = '¥' + formatNumber(finalValue.toFixed(2));
        document.getElementById('compound_total').textContent = '¥' + formatNumber(totalIncome.toFixed(2));
        showResult(document.getElementById('compound_result'));
        hideLoading(btn, btn.dataset.originalText);
        showToast('计算完成');
    }, 300);
}

// 4. 定投计算器
function calculateDCA() {
    const monthlyAmount = parseFloat(document.getElementById('dca_amount').value);
    const annualRate = parseFloat(document.getElementById('dca_rate').value);
    const years = parseFloat(document.getElementById('dca_years').value);
    const btn = document.querySelector('#dca_result').previousElementSibling;
    
    if (isNaN(monthlyAmount) || isNaN(annualRate) || isNaN(years)) {
        alert('请填写所有字段');
        return;
    }
    
    showLoading(btn);
    
    setTimeout(() => {
        const months = years * 12;
        const monthlyRate = annualRate / 100 / 12;
        
        // 定投复利公式: S = P × [(1 + r)^n - 1] / r
        let finalValue;
        if (monthlyRate === 0) {
            finalValue = monthlyAmount * months;
        } else {
            finalValue = monthlyAmount * (Math.pow(1 + monthlyRate, months) - 1) / monthlyRate;
        }
        
        const totalPrincipal = monthlyAmount * months;
        const totalIncome = finalValue - totalPrincipal;
        const totalRate = (totalIncome / totalPrincipal) * 100;
        
        document.getElementById('dca_principal').textContent = '¥' + formatNumber(totalPrincipal.toFixed(2));
        document.getElementById('dca_final').textContent = '¥' + formatNumber(finalValue.toFixed(2));
        document.getElementById('dca_income').textContent = '¥' + formatNumber(totalIncome.toFixed(2));
        document.getElementById('dca_rate_result').textContent = totalRate.toFixed(2) + '%';
        showResult(document.getElementById('dca_result'));
        hideLoading(btn, btn.dataset.originalText);
        showToast('计算完成');
    }, 300);
}

// 绑定回车键
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const card = input.closest('.calculator-card');
                const btn = card.querySelector('.btn-calculate');
                btn.click();
            }
        });
    });
});
