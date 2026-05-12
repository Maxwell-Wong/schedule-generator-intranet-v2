@echo off
chcp 65001 >nul
echo ========================================
echo   排班表生成器 - Windows EXE 构建脚本
echo ========================================
echo.
echo 此脚本将使用 PyInstaller 生成 Windows 可执行文件
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python
    echo 请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 安装依赖...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)
echo ✓ 依赖安装完成

echo.
echo [2/3] 安装 PyInstaller...
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo 错误: PyInstaller 安装失败
    pause
    exit /b 1
)
echo ✓ PyInstaller 安装完成

echo.
echo [3/3] 开始构建 EXE 文件...
pyinstaller --onefile --clean ^
    --add-data "config.ini;." ^
    --add-data "prompts;prompts" ^
    --add-data "data;data" ^
    --hidden-import openpyxl ^
    --hidden-import pandas ^
    --hidden-import openai ^
    --hidden-import configparser ^
    --name ScheduleGenerator ^
    --console ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo   构建失败！
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo   构建成功！
echo ========================================
echo.
echo 可执行文件位置: dist\ScheduleGenerator.exe
echo.
echo 提示:
echo 1. 将 dist\ScheduleGenerator.exe 复制到任意文件夹
echo 2. 确保同目录下有 config.ini、prompts/ 和 data/ 文件夹
echo 3. 双击运行 ScheduleGenerator.exe
echo.

pause
