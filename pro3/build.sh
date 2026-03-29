#!/bin/bash

# Linux Dashboard 打包脚本
# 使用 PyInstaller 将应用打包成单一可执行文件

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================"
echo "  Linux Dashboard 打包工具"
echo "========================================"

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "安装 PyInstaller..."
    pip install pyinstaller
fi

# 清理旧构建
echo "清理旧构建..."
rm -rf build dist __pycache__

# 打包
echo "开始打包..."
pyinstaller dashboard.spec

echo ""
echo "========================================"
echo "  打包完成！"
echo "========================================"
echo ""
echo "可执行文件位置: dist/linux_dashboard"
echo ""
echo "使用方法:"
echo "  1. 将 dist/linux_dashboard 复制到目标服务器"
echo "  2. 将 static 目录也一起复制（如果使用外部 static）"
echo "  3. 运行: ./linux_dashboard"
echo "  4. 访问: http://<IP>:8000"
echo ""
