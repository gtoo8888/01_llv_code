"""
Linux 系统监控仪表盘 - 后端
使用 FastAPI + psutil
"""

import psutil
import platform
import os
import locale
from datetime import timedelta
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import sys

# PyInstaller 打包后的资源路径
def get_static_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'static')


STATIC_PATH = get_static_path()


# 获取系统信息
def get_system_info():
    # 发行版
    distro = "Linux"
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    distro = line.split('=')[1].strip().strip('"')
                    break
    except:
        pass
    
    return {
        "hostname": platform.node(),
        "os": distro,
        "kernel": platform.uname().release,
        "arch": platform.machine(),
        "locale": os.environ.get('LANG', 'en_US.UTF-8'),
        "timezone": os.popen('cat /etc/timezone 2>/dev/null').read().strip() or "UTC",
        "cpu_model": platform.processor() or "Unknown",
    }


# 创建 FastAPI 应用
app = FastAPI(title="Linux 系统监控")

# 挂载静态文件目录（支持 PyInstaller 打包）
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

# 网络速度计算（保存上一次的数据）
_net_io_prev = None
_net_io_time_prev = None

# 历史数据缓存
MAX_HISTORY_POINTS = 20
_history = {
    "cpu": [],
    "memory": []
}
_cpu_initialized = False

# 系统信息缓存（固定值）
_system_cache = get_system_info()


# 数据模型
class SystemStatus(BaseModel):
    cpu: dict
    memory: dict
    disk: dict
    network: dict
    system: dict
    history: dict


# API: 获取系统状态
@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """获取系统状态数据"""
    
    # CPU 信息 - 首次阻塞获取基准，后续非阻塞
    global _cpu_initialized
    if not _cpu_initialized:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        _cpu_initialized = True
    else:
        cpu_percent = psutil.cpu_percent(interval=None)
    
    cpu_count = psutil.cpu_count()
    cpu_percents = psutil.cpu_percent(interval=None, percpu=True)  # 每个核心的使用率
    load_avg = psutil.getloadavg()  # (1min, 5min, 15min)
    
    # 内存信息
    mem = psutil.virtual_memory()
    
    # 更新历史缓存
    _history["cpu"].append(cpu_percent)
    _history["memory"].append(mem.percent)
    if len(_history["cpu"]) > MAX_HISTORY_POINTS:
        _history["cpu"].pop(0)
        _history["memory"].pop(0)
    
    # 磁盘信息 - 区分主要和其他
    primary_mounts = ['/', '/data_sdb']
    disk_primary = []
    disk_others = []
    
    for partition in psutil.disk_partitions():
        if partition.fstype and 'tmpfs' not in partition.fstype:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info = {
                    "mountpoint": partition.mountpoint,
                    "used": round(usage.used / (1024**3), 2),
                    "total": round(usage.total / (1024**3), 2),
                    "percent": usage.percent
                }
                if partition.mountpoint in primary_mounts:
                    disk_primary.append(disk_info)
                else:
                    disk_others.append(disk_info)
            except PermissionError:
                continue
    
    # 网络信息 - 计算速度
    import time
    global _net_io_prev, _net_io_time_prev
    
    net_io_current = psutil.net_io_counters(pernic=True)
    current_time = time.time()
    
    network_data = {"interfaces": []}
    
    if _net_io_prev is not None and _net_io_time_prev is not None:
        time_diff = current_time - _net_io_time_prev
        if time_diff > 0:
            for iface, stats in net_io_current.items():
                if iface == 'lo':  # 跳过回环
                    continue
                prev_stats = _net_io_prev.get(iface)
                if prev_stats:
                    sent_speed = (stats.bytes_sent - prev_stats.bytes_sent) / time_diff / 1024 / 1024  # MB/s
                    recv_speed = (stats.bytes_recv - prev_stats.bytes_recv) / time_diff / 1024 / 1024  # MB/s
                    if sent_speed > 0 or recv_speed > 0 or stats.bytes_sent > 0 or stats.bytes_recv > 0:
                        network_data["interfaces"].append({
                            "interface": iface,
                            "sent_speed": round(sent_speed, 2),
                            "recv_speed": round(recv_speed, 2),
                            "total_sent": round(stats.bytes_sent / 1024 / 1024, 2),  # MB
                            "total_recv": round(stats.bytes_recv / 1024 / 1024, 2)   # MB
                        })
    
    # 更新全局变量
    _net_io_prev = net_io_current
    _net_io_time_prev = current_time
    
    # 系统信息
    boot_time = psutil.boot_time()
    uptime_seconds = timedelta(seconds=int(psutil.time.time() - boot_time))
    
    return SystemStatus(
        cpu={
            "percent": cpu_percent,
            "cores": cpu_count,
            "per_cpu": cpu_percents,
            "load": f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
        },
        memory={
            "used": round(mem.used / (1024**3), 2),  # GB
            "total": round(mem.total / (1024**3), 2),  # GB
            "percent": mem.percent
        },
        disk={
            "primary": disk_primary,
            "others": disk_others
        },
        network=network_data,
        system={
            "hostname": _system_cache["hostname"],
            "os": _system_cache["os"],
            "kernel": _system_cache["kernel"],
            "arch": _system_cache["arch"],
            "locale": _system_cache["locale"],
            "timezone": _system_cache["timezone"],
            "cpu_model": _system_cache["cpu_model"],
            "cpu_cores": f"{psutil.cpu_count(logical=False)} 核 / {psutil.cpu_count(logical=True)} 线程",
            "uptime": str(uptime_seconds).split('.')[0]
        },
        history=_history.copy()
    )


# 首页
@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    with open(os.path.join(STATIC_PATH, "index.html"), "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
