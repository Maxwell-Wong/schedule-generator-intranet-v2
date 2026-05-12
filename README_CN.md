# 排班表生成器 v2.0 (Windows版本)

基于AI的工单排班表自动生成工具。

## 功能特点

- ✅ 自动从Excel工单数据生成排班表
- ✅ 支持普通工作日和周末/特殊时间段
- ✅ AI智能提取系统缩写和人员信息
- ✅ 自动去重和数据验证
- ✅ 生成双sheet Excel文件（排班表 + 原始数据）

## 环境要求

```bash
pip install -r requirements.txt
```

主要依赖：
- Python 3.8+
- pandas
- openpyxl
- openai

## 配置说明

编辑 `config.ini` 文件：

```ini
[paths]
input_file = data/sheet_input.xlsx        # 输入文件路径
output_file = output_transformed.xlsx     # 输出文件路径
rules_file = prompts/transform_rules.md   # 规则文件

[api]
api_key = your_api_key_here               # NVIDIA API密钥
base_url = https://integrate.api.nvidia.com/v1
model = meta/llama-3.1-8b-instruct        # AI模型
max_tokens = 80000                        # 最大输出tokens

[settings]
enable_ai_modify = true
thursday_person_count = 6                 # 周四工单分配人数
```

## 使用方法

### 基本使用

```bash
python main.py
```

程序将自动：
1. 读取输入Excel文件
2. 过滤无效数据
3. 调用AI处理并生成JSON
4. 生成双sheet Excel文件

### 输入文件格式

输入Excel文件应包含以下列：
- 工單號
- 變更名稱
- 變更系統名稱匯總
- 提單人
- 計劃開始時間
- 計劃結束時間

程序会自动过滤：
- 工单状态 = '已撤銷'
- 提單人所屬團隊 in ['安全內控團隊', '前端網路團隊', '系統平臺團隊']

### 输出文件格式

生成两个sheet：

**Sheet 1: 0507 - 變更人員時間安排表**
- 按日期分组的排班表
- 自动识别周末和特殊时间段
- 显示所有工单和人员信息

**Sheet 2: 变更明细数据报表**
- 过滤后的原始数据
- 保留所有字段

## 文件结构

```
schedule-gen-win-v2/
├── main.py                      # 主程序入口
├── data_processor.py            # 数据处理模块
├── ai_client.py                 # AI调用模块
├── excel_generator.py           # Excel生成模块
├── formatters.py                # 格式化工具
├── output_metadata.py           # 输出元数据
├── config.ini                   # 配置文件
├── requirements.txt             # Python依赖
├── data/
│   └── sheet_input.xlsx        # 输入数据文件
└── prompts/
    ├── transform_rules.md      # 转换规则
    └── ai_prompt_*.txt         # AI提示词模板
```

## 常见问题

### 1. API超时
- 检查网络连接
- 减少 `data_processor.py` 中的输出字段数量
- 增加AI调用超时时间

### 2. JSON解析失败
- AI可能返回不完整JSON，程序会自动尝试修复
- 如果失败，检查AI模型是否支持
- 尝试更换更大的模型（如 llama-3.1-70b-instruct）

### 3. 工单遗漏
- AI模型可能在处理大量数据时遗漏个别工单
- 这是LLM的正常行为，建议检查输出完整性
- 关键人员（陳智龍、楊行健等）应该能正确识别

## 版本历史

### v2.0 (2026-05-12)
- ✅ 修复数据缺失日期信息的问题
- ✅ 改进AI提示词，提高准确性
- ✅ 增加数据验证和后处理
- ✅ 支持完整的日期分组

## 技术架构

- **数据处理**: pandas + openpyxl
- **AI模型**: NVIDIA API (Llama 3.1 8B)
- **输出格式**: Excel (双sheet)
- **语言**: Python 3.8+

## 许可证

内部使用工具
