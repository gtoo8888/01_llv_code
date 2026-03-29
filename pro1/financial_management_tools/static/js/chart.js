// 获取图表数据并初始化
async function initChart() {
    const chartDom = document.getElementById('chart-container');
    if (!chartDom) return;
    
    const myChart = echarts.init(chartDom);
    
    try {
        // 从后端获取数据
        const response = await fetch('/api/chart-data');
        const testData = await response.json();
        
        const days = testData.map(d => d.days);
        const totalIncomes = testData.map(d => d.total_income);
        
        const option = {
            title: {
                text: '总收益走势',
                left: 'center'
            },
            tooltip: {
                trigger: 'axis',
                formatter: function(params) {
                    const data = params[0];
                    return `持有天数: ${data.name} 天<br/>总收益: ¥${data.value.toFixed(2)}`;
                }
            },
            grid: {
                left: '10%',
                right: '10%',
                bottom: '10%',
                top: '15%'
            },
            xAxis: {
                type: 'category',
                name: '持有天数 (天)',
                nameLocation: 'middle',
                nameGap: 30,
                data: days,
                axisLabel: {
                    interval: 'auto'
                }
            },
            yAxis: {
                type: 'value',
                name: '总收益 (元)',
                axisLabel: {
                    formatter: '¥{value}'
                }
            },
            series: [
                {
                    name: '总收益',
                    type: 'line',
                    data: totalIncomes,
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 8,
                    lineStyle: {
                        color: '#4a90d9',
                        width: 3
                    },
                    itemStyle: {
                        color: '#4a90d9'
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(74, 144, 217, 0.5)' },
                            { offset: 1, color: 'rgba(74, 144, 217, 0.1)' }
                        ])
                    }
                }
            ]
        };
        
        myChart.setOption(option);
    } catch (error) {
        console.error('获取数据失败:', error);
        chartDom.innerHTML = '<p style="text-align:center;color:#666;">数据加载失败</p>';
    }
    
    // 窗口大小变化时自适应
    window.addEventListener('resize', function() {
        myChart.resize();
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initChart);
