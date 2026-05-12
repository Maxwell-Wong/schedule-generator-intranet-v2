@echo off
chcp 65001 >nul
setlocal

echo ========================================
echo   创建部署包
echo ========================================
echo.

REM 创建部署目录
set DEPLOY_DIR=deployment
if exist "%DEPLOY_DIR%" rmdir /s /q "%DEPLOY_DIR%"
mkdir "%DEPLOY_DIR%"
mkdir "%DEPLOY_DIR%\prompts"
mkdir "%DEPLOY_DIR%\data"

echo [1/5] 复制可执行文件...
if exist "dist\ScheduleGenerator.exe" (
    copy "dist\ScheduleGenerator.exe" "%DEPLOY_DIR%\" >nul
    echo ✓ ScheduleGenerator.exe
) else (
    echo ⚠ 警告: 未找到 dist\ScheduleGenerator.exe
    echo 请先运行 BUILD_EXE.bat 构建可执行文件
)

echo.
echo [2/5] 复制配置文件...
copy "config.ini" "%DEPLOY_DIR%\" >nul
echo ✓ config.ini

echo.
echo [3/5] 复制提示词文件...
copy "prompts\transform_rules.md" "%DEPLOY_DIR%\prompts\" >nul
copy "prompts\ai_prompt_ultra_short.txt" "%DEPLOY_DIR%\prompts\" >nul
echo ✓ prompts\transform_rules.md
echo ✓ prompts\ai_prompt_ultra_short.txt

echo.
echo [4/5] 复制数据文件...
if exist "data\sheet_input.xlsx" (
    copy "data\sheet_input.xlsx" "%DEPLOY_DIR%\data\" >nul
    echo ✓ data\sheet_input.xlsx
) else (
    echo ⚠ 警告: 未找到 data\sheet_input.xlsx
)

echo.
echo [5/5] 复制文档...
copy "README_CN.md" "%DEPLOY_DIR%\" >nul
copy "WINDOWS_README.md" "%DEPLOY_DIR%\" >nul
echo ✓ README_CN.md
echo ✓ WINDOWS_README.md

echo.
echo ========================================
echo   部署包创建完成！
echo ========================================
echo.
echo 部署目录: %DEPLOY_DIR%\
echo.
echo 部署目录内容:
dir /b "%DEPLOY_DIR%"
echo.
echo 部署目录\prompts:
dir /b "%DEPLOY_DIR%\prompts"
echo.
echo 部署目录\data:
dir /b "%DEPLOY_DIR%\data"
echo.

REM 计算大小
for /f "tokens=3" %%a in ('dir /s "%DEPLOY_DIR%" ^| find "个文件"') do set SIZE=%%a
echo 总大小: %SIZE%

echo.
echo 提示:
echo 1. 将 deployment\ 文件夹复制到目标机器
echo 2. 编辑 config.ini 配置 API 密钥
echo 3. 将工单数据放入 data\sheet_input.xlsx
echo 4. 双击运行 ScheduleGenerator.exe
echo.

pause
