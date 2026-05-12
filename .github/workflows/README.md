# GitHub Actions 自动构建说明

本项目使用 GitHub Actions 自动构建可执行文件。

## 🔄 自动构建

### 持续集成构建

触发条件：
- 推送到 `main` 分支
- 修改了 Python 文件、配置文件或 workflow 文件

构建产物：
- Windows 可执行文件包
- 单独的 exe 文件

下载位置：
- GitHub Actions 页面
- 选择最近的 workflow run
- 下载 Artifacts

### Release 发布构建

触发条件：
- 创建新的 Release

自动构建：
- Windows exe
- macOS 可执行文件
- Linux 可执行文件

下载位置：
- Release 页面的 Assets 区域

## 📥 下载自动构建的 exe

### 方法1: 从 Actions 下载

1. 访问 GitHub 仓库
2. 点击 "Actions" 标签
3. 选择最近的 "Build Windows Executable" run
4. 滚动到页面底部的 "Artifacts" 区域
5. 下载 `ScheduleGenerator-Windows` 或 `ScheduleGenerator-exe-only`

### 方法2: 从 Release 下载

1. 访问 GitHub 仓库
2. 点击 "Releases" 标签
3. 选择最新版本
4. 下载对应平台的压缩包

## 🚀 创建新 Release

### 自动构建多平台版本

```bash
# 使用 GitHub CLI
gh release create v2.0.0 --title "v2.0.0" --notes "Release notes"

# 或者在网页上：
# 1. 点击 "Releases"
# 2. 点击 "Draft a new release"
# 3. 填写版本号和说明
# 4. 点击 "Publish release"
```

Actions 会自动构建并上传：
- `ScheduleGenerator-Windows.zip`
- `ScheduleGenerator-macOS.zip`
- `ScheduleGenerator-Linux.tar.gz`

## 🔧 工作流文件

### build-windows.yml

持续集成构建，每次 push 到 main 分支时触发。

### release.yml

Release 发布构建，创建 release 时触发，同时构建三个平台。

## 📊 构建状态

查看 Actions 构建状态：
- GitHub 仓库主页会显示构建徽章
- Actions 页面显示所有构建历史

## ⚙️ 自定义构建

### 修改构建选项

编辑 `.github/workflows/build-windows.yml`：

```yaml
- name: Build executable with PyInstaller
  run: |
    pyinstaller --onefile --clean `
      --add-data "config.ini;." `
      --add-data "prompts;prompts" `
      --add-data "data;data" `
      --name ScheduleGenerator `
      --console `
      main.py
```

### 添加新的构建步骤

在 workflow 文件中添加新的 step：

```yaml
- name: Your custom step
  run: |
    # Your commands here
```

## 🐛 故障排查

### 构建失败

1. 查看 Actions 日志
2. 检查错误信息
3. 修复后重新 push

### 下载失败

1. 确认构建成功
2. 检查 Artifacts 是否过期（默认30天）
3. 尝试重新构建

## 📝 最佳实践

1. **版本管理**: 使用 Git tags 和 Releases
2. **测试**: 在合并前先在 PR 中测试构建
3. **文档**: 更新 README 说明新功能
4. **清理**: 定期删除旧的 Artifacts 和 Releases

## 🔗 相关链接

- GitHub Actions 文档: https://docs.github.com/en/actions
- PyInstaller 文档: https://pyinstaller.org/en/stable/
- 仓库地址: https://github.com/Maxwell-Wong/schedule-generator-intranet-v2
