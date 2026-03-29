# Linux 系统监控仪表盘

一个实时展示 Linux 系统运行状况的 Web 仪表盘。

## 功能特性

- **CPU 监控**
  - 总使用率折线图
  - 每个 CPU 核心使用率（颜色区分）
  - 系统负载

- **内存监控**
  - 使用率折线图
  - 已用/总量 GB 显示

- **磁盘监控**
  - 主要磁盘（/ 和 /data_sdb）重点展示
  - 其他磁盘可折叠查看

- **网络监控**
  - 上传/下载速度
  - 总流量统计

- **其他**
  - 动态调整刷新间隔（1/2/3/5/10秒）
  - 系统信息缓存（减少不必要请求）

## 技术栈

- **后端**: Python FastAPI + psutil
- **前端**: 原生 HTML + CSS + JavaScript
- **图表**: Canvas 绘制（无第三方库）

## 目录结构

```
pro3/
├── app.py                  # FastAPI 主程序
├── test_cpu.py            # CPU 占用测试工具
├── test_memory.py         # 内存占用测试工具
├── auto_run.sh           # 服务管理脚本
├── README.md              # 项目说明
├── doc/
│   └── DEVELOPMENT.md    # 开发规范
├── todo.md                # 开发计划
└── static/
    ├── index.html         # 前端页面
    ├── css/
    │   └── style.css     # 样式
    └── js/
        ├── constants.js  # 常量配置
        ├── api.js        # API 调用
        ├── cpu.js        # CPU 数据处理
        ├── memory.js     # 内存数据处理
        ├── charts.js     # 折线图绘制
        ├── disk.js       # 磁盘数据处理
        ├── network.js    # 网络数据处理
        ├── events.js     # 事件处理
        └── main.js       # 入口
```

## 快速开始

### 1. 安装依赖

```bash
conda activate linux_dashboard
pip install fastapi uvicorn psutil
```

### 2. 启动服务

```bash
cd /data_sdb/openclaw/02_llv_generated/01_llv_code/pro3
python app.py
```

或使用管理脚本：

```bash
./auto_run.sh run      # 启动
./auto_run.sh stop     # 停止
./auto_run.sh restart  # 重启
./auto_run.sh status   # 状态
./auto_run.sh logs    # 查看日志
```

### 3. 访问

- 本地: http://localhost:8000
- 局域网: http://<IP>:8000

## 前端交互

### 折线图

- 鼠标悬停：显示具体数值（百分比 + GB）
- 点击某个点：锁定该点为当前点
- 5秒无操作：自动恢复显示最新点

### CPU 核心颜色

| 使用率 | 颜色   |
| ------ | ------ |
| < 30%  | 🟢 绿色 |
| 30-60% | 🟡 黄色 |
| 60-85% | 🔴 红色 |
| > 85%  | 🟣 紫色 |

### 刷新间隔

- 页面底部可动态调整刷新间隔
- 支持：1秒、2秒、3秒、5秒、10秒
- 设置自动保存到浏览器本地存储

## 测试工具

### CPU 占用测试

```bash
python test_cpu.py
# 输入要占用的核心数
```

### 内存占用测试

```bash
python test_memory.py
# 输入要占用的内存大小 (MB)
```

## 配置

### 修改历史数据点数

后端 `app.py`：

```python
MAX_HISTORY_POINTS = 20  # 默认20个点
```

前端 `static/js/constants.js`：

```javascript
maxPoints: 20
```

### 修改主要监控磁盘

后端 `app.py`：

```python
primary_mounts = ['/', '/data_sdb']  # 可修改为其他挂载点
```

## 打包发布

### 打包命令

```bash
./build.sh
```

或者手动执行：

```bash
pyinstaller dashboard.spec
```

### 打包产物

```
dist/linux_dashboard  # 单一可执行文件（约 21MB）
```

### 部署到新服务器

1. 将 `dist/linux_dashboard` 复制到目标服务器
2. 赋予执行权限：`chmod +x linux_dashboard`
3. 运行：`./linux_dashboard`
4. 访问：`http://<IP>:8000`

**无需安装 Python 或任何依赖**，开箱即用！

### 重新打包

如果修改了代码，需要重新打包：

```bash
# 清理旧构建
rm -rf build dist __pycache__

# 重新打包
pyinstaller dashboard.spec
```

### 注意事项

- 打包需要在 Linux 环境下进行
- 打包产物只能用于相同架构的服务器（x86_64 → x86_64）
- 打包产物约 21MB

## 开发规范

参见 [doc/DEVELOPMENT.md](doc/DEVELOPMENT.md)
