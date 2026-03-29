#!/bin/zsh

# 项目路径
PROJECT_DIR="/data_sdb/openclaw/02_llv_generated/01_llv_code/pro3"
PID_FILE="$PROJECT_DIR/app.pid"
LOG_FILE="$PROJECT_DIR/app.log"

# Python 解释器 (conda 环境)
PYTHON_BIN="$HOME/anaconda3/envs/linux_dashboard/bin/python"

# 端口配置
PORT=8000

# Colors
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; N='\033[0m'

# 获取运行中的 PID
get_pid() {
    [[ -f $PID_FILE ]] || return 1
    local pid=$(<$PID_FILE)
    if ps -p $pid >/dev/null 2>&1; then
        echo $pid
        return 0
    else
        rm -f $PID_FILE
        return 1
    fi
}

# 获取本机 IP
get_local_ip() {
    local ip=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1)
    if [ -z "$ip" ]; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    echo $ip
}

start() {
    cd "$PROJECT_DIR" || exit 1
    
    if pid=$(get_pid); then
        echo -e "${R}Service already running (PID: $pid)${N}"; exit 1
    fi
    
    LOCAL_IP=$(get_local_ip)
    
    echo -e "${Y}Starting service...${N}"
    nohup $PYTHON_BIN app.py >> "$LOG_FILE" 2>&1 &
    APP_PID=$!
    echo $APP_PID > "$PID_FILE"
    sleep 2
    
    if ps -p $APP_PID >/dev/null 2>&1; then
        echo -e "${G}Service started (PID: $APP_PID)${N}"
        echo "Access URL: http://${LOCAL_IP}:${PORT}"
    else
        echo -e "${R}Failed to start service${N}"; cat "$LOG_FILE"; rm -f "$PID_FILE"; exit 1
    fi
}

stop() {
    if ! pid=$(get_pid); then
        echo -e "${R}Service not running${N}"; exit 1
    fi
    echo -e "${Y}Stopping service (PID: $pid)...${N}"
    kill $pid
    for i in {1..10}; do
        ps -p $pid >/dev/null 2>&1 || { rm -f $PID_FILE; echo -e "${G}Service stopped${N}"; return; }
        sleep 0.5
    done
    kill -9 $pid 2>/dev/null || true
    rm -f $PID_FILE
    echo -e "${G}Service stopped${N}"
}

status() {
    if pid=$(get_pid); then
        echo -e "${G}Service running (PID: $pid)${N}"
    else
        echo -e "${R}Service not running${N}"
    fi
}

logs() {
    tail -f "$LOG_FILE" 2>/dev/null || echo "No logs available"
}

clean() {
    echo -e "${Y}Cleaning generated files...${N}"
    if pid=$(get_pid); then
        echo -e "${Y}Stopping service...${N}"; kill $pid 2>/dev/null; sleep 1; rm -f $PID_FILE
    fi
    rm -f "$LOG_FILE"
    rm -rf "$PROJECT_DIR"/__pycache__ "$PROJECT_DIR"/static/__pycache__ "$PROJECT_DIR"/.pytest_cache 2>/dev/null
    echo -e "${G}Cleanup complete${N}"
}

case $1 in
    run) start ;;
    stop) stop ;;
    status) status ;;
    logs) logs ;;
    restart) stop 2>/dev/null || true; start ;;
    clean) clean ;;
    *) 
        echo "Usage: $0 {run|stop|status|logs|restart|clean}"
        exit 1
        ;;
esac
