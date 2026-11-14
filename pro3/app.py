"""
Linux 系统监控仪表盘 - 后端
使用 FastAPI + psutil
"""

import psutil
import platform
import os
import locale
import time
import threading
import subprocess
import socket
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

# ---------------------------------------------------------------- 网络采集
# 由后台线程固定 1s 采样，请求只读快照。
# 速度单位为 字节/秒（前端自适应格式化为 B/s、KB/s、MB/s）。

NET_TICK = 1.0                      # 采样节拍（秒）
IFACE_SKIP = ("lo", "docker", "br-", "veth", "tun", "tap", "virbr", "wg")
MAX_LINKS = 6                       # 链路表最多展示条数

# 链路别名：按对端 IP:端口 起名，剩下的自动归类
LINK_LABELS = {
    "192.168.5.5:7898": "代理(yfinance)",
    "192.168.5.5:7897": "代理(备用)",
    "192.168.5.5:7890": "代理(直连口)",
}

_net_state = {"interfaces": [], "links": [], "ts": None}
_net_ready = False
_prev_iface = {}
_prev_link = {}


def _local_ips():
    """本机所有 IPv4 地址，用于过滤本机内部连接。"""
    ips = {"127.0.0.1"}
    try:
        for addrs in psutil.net_if_addrs().values():
            for a in addrs:
                if a.family == socket.AF_INET:
                    ips.add(a.address)
    except Exception:
        pass
    return ips


LOCAL_IPS = _local_ips()


def _read_links():
    """解析 ss -tni，按对端聚合每条 TCP 连接的累计收发字节。"""
    try:
        out = subprocess.run(["ss", "-tni"], capture_output=True,
                             text=True, timeout=3).stdout
    except Exception:
        return {}

    agg, peer = {}, None
    for line in out.splitlines():
        if not line.strip():
            continue
        # 不以空白开头 = 一条连接的标题行
        if line[0] not in " \t":
            f = line.split()
            if len(f) >= 5 and ":" in f[3] and ":" in f[4] and f[0] != "State":
                peer = f[4]
                agg.setdefault(peer, [0, 0])
            else:
                peer = None
            continue
        if peer is None:
            continue
        for tok in line.split():
            if tok.startswith("bytes_sent:"):
                try:
                    agg[peer][0] += int(tok.split(":", 1)[1])
                except ValueError:
                    pass
            elif tok.startswith("bytes_received:"):
                try:
                    agg[peer][1] += int(tok.split(":", 1)[1])
                except ValueError:
                    pass
    return {k: (v[0], v[1]) for k, v in agg.items()}


def _link_label(peer):
    if peer in LINK_LABELS:
        return LINK_LABELS[peer]
    ip = peer.rsplit(":", 1)[0]
    if ip.startswith("127."):
        return "本机"
    if ip.startswith("192.168.5."):
        return "内网"
    return "直连"


def _rate(prev, cur, dt):
    if prev is None or dt <= 0:
        return 0.0, 0.0
    return max(0.0, (cur[0] - prev[0]) / dt), max(0.0, (cur[1] - prev[1]) / dt)


def _net_sampler():
    """后台采样线程：网卡吞吐 + 链路吞吐，无常驻阻塞。"""
    global _net_state, _net_ready, _prev_iface, _prev_link, _prev_ts
    while True:
        t = time.time()
        try:
            counters = psutil.net_io_counters(pernic=True)
            stats = psutil.net_if_stats()
        except Exception:
            counters, stats = {}, {}

        dt = 0.0
        if _prev_iface:
            dt = t - _prev_ts

        interfaces = []
        for name, c in counters.items():
            if name.startswith(IFACE_SKIP):
                continue
            st = stats.get(name)
            if not (st and st.isup):
                continue
            up, down = _rate(_prev_iface.get(name), (c.bytes_sent, c.bytes_recv), dt)
            _prev_iface[name] = (c.bytes_sent, c.bytes_recv)
            interfaces.append({
                "interface": name,
                "send_bps": up,
                "recv_bps": down,
                "total_sent": c.bytes_sent,
                "total_recv": c.bytes_recv,
                "link_speed": st.speed,
            })
        interfaces.sort(key=lambda x: x["send_bps"] + x["recv_bps"], reverse=True)

        raw = _read_links()
        links = []
        for peer, (sent, recv) in raw.items():
            if peer.rsplit(":", 1)[0] in LOCAL_IPS:
                continue
            up, down = _rate(_prev_link.get(peer), (sent, recv), dt)
            links.append({
                "peer": peer,
                "label": _link_label(peer),
                "send_bps": up,
                "recv_bps": down,
                "total_sent": sent,
                "total_recv": recv,
            })
        links.sort(key=lambda x: x["send_bps"] + x["recv_bps"], reverse=True)

        _prev_ts = t
        _prev_link = dict(raw)
        _net_state = {"interfaces": interfaces[:4],
                      "links": links[:MAX_LINKS],
                      "ts": t}
        _net_ready = True
        time.sleep(NET_TICK)


_prev_ts = 0.0
threading.Thread(target=_net_sampler, name="net-sampler", daemon=True).start()

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
    
    # 网络信息 - 直接读取后台采样线程的快照
    network_data = _net_state

    # 系统信息
    boot_time = psutil.boot_time()
    uptime_seconds = timedelta(seconds=int(time.time() - boot_time))
    
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
