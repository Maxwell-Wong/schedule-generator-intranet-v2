# GitHub Actions 自动构建指南

## 🎯 功能说明

现在项目已配置 GitHub Actions，可以**自动构建可执行文件**！

### ✅ 自动触发构建

**方式1: 持续集成（推荐）**
- 每次推送代码到 `main` 分支
- 自动构建 Windows 可执行文件
- 构建时间：约 3-5 分钟
- 产物保留 30 天

**方式2: Release 发布**
- 创建 GitHub Release
- 同时构建三个平台：
  - Windows (exe)
  - macOS (可执行文件)
  - Linux (可执行文件)
- 自动上传到 Release 页面

## 📥 下载自动构建的 exe

### 方法1: 从 Actions 下载（最新版本）

1. 访问 GitHub 仓库: https://github.com/Maxwell-Wong/schedule-generator-intranet-v2
2. 点击 **Actions** 标签
3. 选择最近的 **"Build Windows Executable"** workflow
4. 滚动到底部的 **Artifacts** 区域
5. 下载 `ScheduleGenerator-Windows` （完整部署包）或 `ScheduleGenerator-exe-only` （仅 exe 文件）

### 方法2: 从 Release 下载（稳定版本）

1. 访问仓库的 **Releases** 页面
2. 选择最新版本
3. 下载对应平台的压缩包：
   - `ScheduleGenerator-Windows.zip`
   - `ScheduleGenerator-macOS.zip`
   - `ScheduleGenerator-Linux.tar.gz`

## 🚀 创建新 Release（自动构建多平台）

### 使用网页界面

1. 访问 GitHub 仓库
2. 点击 **Releases** → **Draft a new release**
3. 填写信息：
   - **Tag version**: `v2.1.0`（示例）
   - **Release title**: `v2.1.0 - 新功能描述`
   - **Description**: 更新内容说明
4. 点击 **Publish release**
5. 等待 5-10 分钟，Actions 会自动构建并上传三个平台的可执行文件

### 使用 GitHub CLI

```bash
# 安装 GitHub CLI（如果没有）
# macOS: brew install gh
# Windows: scoop install gh

# 登录
gh auth login

# 创建 release（自动触发构建）
gh release create v2.1.0 \
  --title "v2.1.0 - 新功能" \
  --notes "更新内容：
- 新功能1
- 新功能2
- Bug修复"
```

## 📊 查看构建状态

### 在仓库主页
- 仓库主页会显示绿色✅或红色❌徽章
- 点击可查看最新构建状态

### 在 Actions 页面
- 完整的构建历史
- 每次构建的详细日志
- 失败原因分析

## 🔧 配置说明

### GitHub Actions 文件

**`.github/workflows/build-windows.yml`**
- 持续集成构建
- 每次 push 到 main 分支时触发
- 只构建 Windows 版本

**`.github/workflows/release.yml`**
- Release 发布构建
- 创建 release 时触发
- 同时构建三个平台

### 自定义构建

如需修改构建选项，编辑对应的 workflow 文件：

```yaml
# 修改 Python 版本
python-version: '3.11'

# 修改 PyInstaller 参数
pyinstaller --onefile --clean \
  --name YourAppName \
  --console \
  main.py
```

## ⏱️ 构建时间

- **Windows**: 约 3-5 分钟
- **macOS**: 约 2-4 分钟
- **Linux**: 约 2-3 分钟

**同时构建三个平台**: 约 5-10 分钟（并行执行）

## 🎁 下载后使用

### 解压部署包

```bash
# Windows
# 解压 ScheduleGenerator-Windows.zip
# 直接双击运行 ScheduleGenerator.exe

# macOS/Linux
unzip ScheduleGenerator-macOS.zip  # 或 tar -xzf ScheduleGenerator-Linux.tar.gz
chmod +x ScheduleGenerator
./ScheduleGenerator
```

### 首次使用

1. 编辑 `config.ini` 配置 API 密钥
2. 将工单数据放入 `data/sheet_input.xlsx`
3. 运行 `ScheduleGenerator`
4. 查看生成的 `output_transformed.xlsx`

## 🐛 常见问题

### Q: 如何知道构建是否成功？

A: 访问 Actions 页面，绿色✅表示成功，红色❌表示失败

### Q: 构建失败怎么办？

A:
1. 点击失败的 workflow run
2. 查看错误日志
3. 修复代码后重新 push

### Q: Artifacts 下载链接过期了怎么办？

A: Artifacts 默认保留 30 天，过期后需要重新构建。建议使用 Release 版本（永久保留）。

### Q: 能否修改构建产物保留时间？

A: 可以，在 workflow 文件中修改 `retention-days` 参数

## 📋 最佳实践

1. **开发阶段**: 使用 Actions Artifacts 下载最新版本
2. **发布版本**: 创建 GitHub Release，自动构建多平台版本
3. **版本管理**: 使用语义化版本号（v1.0.0, v2.0.0）
4. **更新日志**: 在 Release 中详细说明更新内容

## 🔗 相关链接

- GitHub Actions 文档: https://docs.github.com/en/actions
- 仓库地址: https://github.com/Maxwell-Wong/schedule-generator-intranet-v2
- Actions 页面: https://github.com/Maxwell-Wong/schedule-generator-intranet-v2/actions

---

**提示**: 现在您不需要手动构建，GitHub Actions 会自动完成所有工作！🎉
