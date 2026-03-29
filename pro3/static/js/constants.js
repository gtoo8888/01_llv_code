// 常量配置

// 历史数据
const cpuHistory = {
    data: [],
    maxPoints: 20,
    activeIndex: -1,
    initialized: false
};

const memoryHistory = {
    data: [],
    maxPoints: 20,
    total: 0,
    activeIndex: -1,
    initialized: false
};

// 刷新间隔
const REFRESH_INTERVAL_KEY = 'dashboard_refresh_interval';
let refreshTimer = null;

// 定时器
let cpuResetTimer = null;
let memoryResetTimer = null;
