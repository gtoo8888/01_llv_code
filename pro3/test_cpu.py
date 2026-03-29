"""
CPU 占用测试工具
运行此脚本可以占用 CPU 资源，用于测试监控界面
"""

import time
import multiprocessing
import psutil
import os


def cpu_task(duration, result_list):
    """持续占用 CPU 的任务"""
    start_time = time.time()
    count = 0
    while time.time() - start_time < duration:
        # 做些计算
        _ = sum(i * i for i in range(10000))
        count += 1
    result_list.append(count)


def get_cpu_usage():
    """获取当前 CPU 使用率"""
    return psutil.cpu_percent(interval=0.5)


if __name__ == "__main__":
    print("=" * 50)
    print("CPU 占用测试工具")
    print("=" * 50)
    
    # 显示当前 CPU 信息
    print(f"\nCPU 核心数: {psutil.cpu_count()}")
    print(f"当前 CPU 使用率: {get_cpu_usage()}%")
    
    print("\n使用方法:")
    print("  1. 输入要使用的核心数 (1-N)")
    print("  2. 按 Ctrl+C 停止")
    print()
    
    try:
        num_cores = input("请输入要占用的核心数 (1-{}, 默认 2): ".format(psutil.cpu_count())).strip()
        if not num_cores:
            num_cores = 2
        else:
            num_cores = int(num_cores)
            num_cores = max(1, min(num_cores, psutil.cpu_count()))
        
        print(f"\n正在占用 {num_cores} 个 CPU 核心...")
        print("按 Ctrl+C 停止")
        print()
        
        # 使用多进程占用 CPU
        processes = []
        for i in range(num_cores):
            p = multiprocessing.Process(target=cpu_task, args=(999999, []))
            p.start()
            processes.append(p)
            print(f"  进程 {i+1} 已启动 (PID: {p.pid})")
        
        print(f"\n已启动 {num_cores} 个进程持续占用 CPU")
        print(f"当前 CPU 使用率: {get_cpu_usage()}%")
        print("\n保持此窗口运行...")
        print("按 Ctrl+C 释放并退出...")
        
        # 保持运行
        while True:
            time.sleep(1)
            print(f"\rCPU 使用率: {get_cpu_usage()}%", end='', flush=True)
            
    except KeyboardInterrupt:
        print("\n\n正在停止所有进程...")
        for p in processes:
            p.terminate()
            p.join()
        print("已全部停止")
        print(f"停止后 CPU 使用率: {get_cpu_usage()}%")
