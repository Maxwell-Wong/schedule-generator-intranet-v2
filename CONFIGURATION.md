# 配置说明

## 首次使用

1. 从 `config.ini.example` 复制一份配置文件：
   ```bash
   cp config.ini.example config.ini
   ```

2. 编辑 `config.ini`，配置你的 AI API 信息

## AI API 配置

程序支持多种 AI 模型，你只需要修改 `[api]` 部分的配置。

### 示例1：内网 Qwen 模型

```ini
[api]
api_key = your_internal_api_key
base_url = http://your-internal-server:8000/v1
model = Qwen/Qwen3.5-27B
```

### 示例2：Nvidia API

```ini
[api]
api_key = nvapi-xxxxxxxxxxxx
base_url = https://integrate.api.nvidia.com/v1
model = meta/llama-3.1-8b-instruct
```

### 示例3：OpenAI API

```ini
[api]
api_key = sk-xxxxxxxxxxxx
base_url = https://api.openai.com/v1
model = gpt-4
```

### 示例4：其他兼容 OpenAI API 的服务

```ini
[api]
api_key = your_api_key
base_url = https://your-api-endpoint/v1
model = your_model_name
```

## 参数说明

- `api_key`: API 密钥
- `base_url`: API 端点地址
- `model`: 模型名称
- `max_tokens`: 最大输出 token 数（默认：80000）

## 文件路径配置

在 `[paths]` 部分配置输入输出文件：

```ini
[paths]
input_file = data/sheet_input.xlsx
output_file = output_transformed.xlsx
```

## 其他配置

- `thursday_person_count`: 周四工单分配的人数（默认：6）
- `removed_status`: 要过滤的工单状态（默认：已撤銷）
- `removed_teams`: 要过滤的团队（逗号分隔）

## 注意事项

⚠️ **重要**：
- 不要将 `config.ini` 提交到 Git 仓库（已添加到 .gitignore）
- `config.ini` 包含敏感信息（API 密钥）
- 只提交 `config.ini.example` 作为模板
- 每个用户需要自己创建和配置 `config.ini`
