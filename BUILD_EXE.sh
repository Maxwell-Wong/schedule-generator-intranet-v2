#!/bin/bash

echo "========================================"
echo "  排班表生成器 - macOS/Linux 构建脚本"
echo "========================================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    echo "请先安装 Python 3.8+"
    exit 1
fi

echo "[1/3] 安装依赖..."
pip3 install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "错误: 依赖安装失败"
    exit 1
fi
echo "✓ 依赖安装完成"

echo ""
echo "[2/3] 安装 PyInstaller..."
pip3 install pyinstaller -q
if [ $? -ne 0 ]; then
    echo "错误: PyInstaller 安装失败"
    exit 1
fi
echo "✓ PyInstaller 安装完成"

echo ""
echo "[3/3] 开始构建可执行文件..."
pyinstaller --onefile --clean \
    --add-data "config.ini:." \
    --add-data "prompts:prompts" \
    --add-data "data:data" \
    --hidden-import openpyxl \
    --hidden-import pandas \
    --hidden-import openai \
    --hidden-import configparser \
    --name ScheduleGenerator \
    --console \
    main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "  构建失败！"
    echo "========================================"
    exit 1
fi

echo ""
echo "========================================"
echo "  构建成功！"
echo "========================================"
echo ""
echo "可执行文件位置: dist/ScheduleGenerator"
echo ""
echo "提示:"
echo "1. 将 dist/ScheduleGenerator 复制到任意文件夹"
echo "2. 确保同目录下有 config.ini、prompts/ 和 data/ 文件夹"
echo "3. 运行 ./ScheduleGenerator"
echo ""

# 测试生成的可执行文件
echo "测试运行..."
if [ -f "dist/ScheduleGenerator" ]; then
    chmod +x dist/ScheduleGenerator
    echo "✓ 可执行文件已生成并设置执行权限"
else
    echo "⚠ 警告: 可执行文件未找到"
fi
