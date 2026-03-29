"""
内存占用测试工具
运行此脚本可以占用大量内存，用于测试监控界面
"""

import time
import psutil
import os


def allocate_memory(size_mb: int):
    """分配指定大小的内存"""
    print(f"正在分配 {size_mb} MB 内存...")
    # 创建一个列表来占用内存
    # 每个字符占用1字节，每个字符串占用约1MB
    data = []
    for i in range(size_mb):
        data.append(' ' * 1024 * 1024)  # 1MB
        if (i + 1) % 100 == 0:
            print(f"已分配 {(i+1)} MB...")
    return data


def get_current_memory():
    """获取当前进程内存使用"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # MB


if __name__ == "__main__":
    print("=" * 50)
    print("内存占用测试工具")
    print("=" * 50)
    
    # 显示当前内存
    print(f"\n当前进程内存: {get_current_memory():.1f} MB")
    print(f"系统可用内存: {psutil.virtual_memory().available / 1024 / 1024 / 1024:.2f} GB")
    
    # 让用户输入要占用的内存大小
    print("\n使用方法:")
    print("  1. 运行脚本")
    print("  2. 输入要占用的内存大小 (MB)")
    print("  3. 按 Ctrl+C 释放内存并退出")
    print()
    
    try:
        size = input("请输入要占用的内存大小 (MB, 默认 1000): ").strip()
        if not size:
            size = 1000
        else:
            size = int(size)
        
        allocated_data = allocate_memory(size)
        
        print(f"\n已成功分配 {size} MB 内存")
        print(f"当前进程内存: {get_current_memory():.1f} MB")
        print(f"系统内存使用率: {psutil.virtual_memory().percent}%")
        
        print("\n保持此窗口运行，内存将持续被占用")
        print("按 Ctrl+C 释放内存并退出...")
        
        # 保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n释放内存...")
        del allocated_data
        time.sleep(1)
        print(f"释放后内存: {get_current_memory():.1f} MB")
        print("已退出")
