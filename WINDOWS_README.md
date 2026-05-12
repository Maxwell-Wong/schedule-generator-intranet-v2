# Windows EXE 版本使用说明

## 📦 生成 Windows 可执行文件

### 方法1: 使用构建脚本（推荐）

1. **双击运行** `BUILD_EXE.bat`
2. 等待构建完成（约2-5分钟）
3. 生成的 `ScheduleGenerator.exe` 位于 `dist/` 目录

### 方法2: 手动构建

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 PyInstaller
pip install pyinstaller

# 3. 构建可执行文件
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
```

## 📂 部署结构

构建完成后，将以下文件复制到目标文件夹：

```
目标文件夹/
├── ScheduleGenerator.exe    # 主程序（从 dist/ 复制）
├── config.ini                # 配置文件
├── prompts/                  # 提示词目录
│   ├── transform_rules.md
│   └── ai_prompt_ultra_short.txt
└── data/                     # 数据目录
    └── sheet_input.xlsx     # 输入数据文件
```

**重要**: 必须确保 `config.ini`、`prompts/` 和 `data/` 与 `ScheduleGenerator.exe` 在同一目录！

## 🚀 使用方法

### 1. 准备数据

将工单数据放入 `data/sheet_input.xlsx`

### 2. 配置 API 密钥

编辑 `config.ini`，填入 NVIDIA API 密钥：

```ini
[api]
api_key = your_api_key_here
```

### 3. 运行程序

双击 `ScheduleGenerator.exe` 或在命令行运行：

```bash
ScheduleGenerator.exe
```

### 4. 查看结果

生成的排班表位于：`output_transformed.xlsx`

## ⚠️ 注意事项

### 首次运行

Windows 可能会提示 "Windows 已保护你的电脑"，点击"更多信息" → "仍要运行"

### 防火墙/杀毒软件

如果杀毒软件拦截，需要添加到白名单

### 缺少依赖

如果运行时提示缺少 DLL 文件：
1. 安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 或使用完整的 Python 环境

## 🔧 故障排查

### 问题1: 提示找不到 config.ini

**原因**: 文件结构不正确

**解决**: 确保目录结构如下：
```
ScheduleGenerator.exe
config.ini
prompts/
data/
```

### 问题2: API 调用失败

**原因**: 网络问题或 API 密钥错误

**解决**:
1. 检查网络连接
2. 验证 config.ini 中的 api_key 是否正确
3. 检查 base_url 是否可访问

### 问题3: 生成的 Excel 文件打不开

**原因**: 可能是数据格式问题或程序异常退出

**解决**:
1. 查看程序输出的错误信息
2. 检查输入数据格式是否正确
3. 尝试重新运行程序

## 📊 文件大小说明

- **ScheduleGenerator.exe**: 约 50-80 MB（包含所有依赖）
- 首次运行可能需要一些时间加载
- 内存占用: 约 200-500 MB

## 🎯 优势

✅ **无需安装 Python**
✅ **双击即可运行**
✅ **包含所有依赖**
✅ **可在无网络的机器上使用**（配置好API后）

## 📝 版本信息

- 版本: v2.0
- 构建工具: PyInstaller 6.20.0
- Python 版本: 3.8+
- 平台: Windows 10/11

## 🆘 获取帮助

如遇到问题，请检查：
1. 程序输出的错误信息
2. output_transformed.xlsx 是否正常生成
3. config.ini 配置是否正确
4. 网络连接是否正常

更多信息请参考: README_CN.md
