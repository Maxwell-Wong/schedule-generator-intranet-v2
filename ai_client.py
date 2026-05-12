#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI客户端
调用AI API（Qwen27B或其他模型）处理排班规则
"""

import json
import os
import pandas as pd
from openai import OpenAI


def load_prompt_template(template_file='prompts/ai_prompt_ultra_short.txt'):
    """
    加载prompt模板文件

    Args:
        template_file: 模板文件路径

    Returns:
        str: 模板内容
    """
    # 获取基础目录
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.join(base_dir, template_file)

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Prompt template file not found: {template_path}")

    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def assemble_prompt(rules_text, ai_data_text, thursday_count):
    """
    组装发送给AI的完整Prompt

    Args:
        rules_text: 转换规则（Markdown格式）
        ai_data_text: Excel数据文本
        thursday_count: 周四人数参数

    Returns:
        str: 完整的prompt
    """
    # 加载模板
    template = load_prompt_template()

    # 使用简单的字符串替换，避免花括号冲突
    prompt = template.replace('{RULES_TEXT}', rules_text)
    prompt = prompt.replace('{DATA_TEXT}', ai_data_text)
    prompt = prompt.replace('{THURSDAY_COUNT}', str(thursday_count))

    return prompt


def call_ai_api(api_key, base_url, model, prompt, max_tokens=32768):
    """
    调用AI API

    Args:
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        prompt: 发送给AI的prompt

    Returns:
        str: AI的响应内容
    """
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=600.0  # 10分钟超时
    )

    print(f"\n[2/5] Calling AI API...")
    print(f"  Model: {model}")
    print(f"  Base URL: {base_url}")
    print(f"  Prompt length: {len(prompt)} characters ({len(prompt)//4} estimated tokens)")

    # 检查提示词长度，避免超过模型限制
    estimated_tokens = len(prompt) // 4  # 粗略估算：1 token ≈ 4 字符
    if estimated_tokens > 100000:
        print(f"  ⚠ Warning: Prompt is very long ({estimated_tokens} tokens)")
        print(f"  This might exceed model context limits")
        response = input(f"  Continue anyway? (y/n): ")
        if response.lower() != 'y':
            raise ValueError("User cancelled due to long prompt")

    try:
        print(f"  Sending request to API (this may take 1-3 minutes)...")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个专业的排班助手。

任务：根据输入数据生成 JSON 格式的排班表。

严格要求：
1. 立即开始输出 JSON，不要有任何开场白、解释或推理过程
2. 第一个字符必须是 {，最后一个字符必须是 }
3. 不要输出"让我分析"、"首先"、"接下来"等内容
4. 不要使用 markdown 代码块
5. 确保 JSON 格式正确且完整

开始输出："""
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            top_p=0.1,
            max_tokens=max_tokens,  # 使用配置的max_tokens值
            stream=False,
            presence_penalty=0.0,
            frequency_penalty=0.0
        )

        # 获取响应内容
        if hasattr(completion, 'choices') and len(completion.choices) > 0:
            message = completion.choices[0].message

            # 打印所有可用字段用于调试
            print(f"  🔍 Inspecting response fields...")
            content_candidates = []

            # 检查所有可能的字段
            for attr in ['content', 'reasoning_content', 'text', 'refusal']:
                if hasattr(message, attr):
                    val = getattr(message, attr)
                    if val:  # 只记录非空值
                        content_candidates.append((attr, val))
                        print(f"    - {attr}: {len(val)} chars")

            # 检测是否所有内容都是推理过程（没有 JSON）
            has_json = False
            for attr, val in content_candidates:
                if '{' in val and '}' in val:
                    has_json = True
                    break

            if not has_json and len(content_candidates) > 0:
                print(f"  ⚠ WARNING: No JSON found in any content field!")
                print(f"  ⚠ The model appears to be stuck in a reasoning loop.")

                # 检查是否有重复模式
                if 'reasoning_content' in [attr for attr, _ in content_candidates]:
                    reasoning = next(val for attr, val in content_candidates if attr == 'reasoning_content')

                    # 检测重复内容
                    lines = reasoning.split('\n')
                    unique_lines = set(lines)
                    if len(lines) > 100 and len(unique_lines) < len(lines) * 0.3:
                        print(f"  ⚠ Detected repetitive content (possible loop)")
                        print(f"     - Total lines: {len(lines)}")
                        print(f"     - Unique lines: {len(unique_lines)}")
                        print(f"     - Repetition rate: {100 * (1 - len(unique_lines)/len(lines)):.1f}%")

                print(f"  💡 SUGGESTION:")
                print(f"     1. The minimax-m2.7 model may not be suitable for this task")
                print(f"     2. Try using a different model (e.g., 'meta/llama-3.1-70b-instruct')")
                print(f"     3. Simplify the prompt or reduce input data size")

            # 如果 reasoning_content 存在且看起来像推理过程（不包含 JSON）
            # 则尝试使用 content（即使它看起来为空，可能是空字符串而不是 None）
            if len(content_candidates) == 0:
                print(f"  ⚠ All content fields are empty or None")
                # 尝试获取空字符串
                if hasattr(message, 'content'):
                    content = message.content or ""
                    print(f"  ✓ Using empty content field")
                else:
                    raise ValueError("API returned empty response")

            elif len(content_candidates) == 1:
                # 只有一个字段有内容
                attr, content = content_candidates[0]
                print(f"  ✓ Using {attr} ({len(content)} chars)")

            else:
                # 多个字段都有内容，需要判断哪个是最终结果
                # reasoning_content 通常是推理过程，content 是最终结果
                if hasattr(message, 'content') and message.content:
                    content = message.content
                    print(f"  ✓ Using content field (final result)")
                elif hasattr(message, 'text') and message.text:
                    content = message.text
                    print(f"  ✓ Using text field")
                else:
                    # 使用第一个非空的
                    attr, content = content_candidates[0]
                    print(f"  ⚠ Multiple fields found, using {attr}")

            # 检查内容是否以 JSON 标记开头
            if content and not content.strip().startswith(('{', '```', '[')):
                print(f"  ⚠ Warning: Content doesn't look like JSON")
                print(f"  Content preview: {content[:200]}")

                # 如果 reasoning_content 看起来像推理过程
                if '让我分析' in content or '首先' in content or '接下来' in content:
                    print(f"  ⚠ This appears to be reasoning process, not final JSON")
                    print(f"  💡 Suggestion: The model may be in 'thinking mode'")
                    print(f"  💡 Try: Add stronger instructions to output JSON directly")

            if not content or len(content.strip()) == 0:
                raise ValueError("API returned empty content")

            print(f"  ✓ API call successful")
            print(f"  Response length: {len(content)} characters")
            return content.strip()
        else:
            raise ValueError("Invalid API response format")

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        print(f"  ✗ API call failed: {error_type}: {error_msg}")

        # 针对不同错误类型给出建议
        if 'timeout' in error_msg.lower() or 'Timeout' in error_type:
            print(f"  💡 Suggestion: The request timed out. Possible reasons:")
            print(f"     - Prompt is too long ({len(prompt)} characters)")
            print(f"     - API server is overloaded")
            print(f"     - Network connection is slow")
            print(f"  💡 Try: Reduce prompt size or increase timeout parameter")
        elif 'rate limit' in error_msg.lower():
            print(f"  💡 Suggestion: Rate limit exceeded. Wait a moment and try again")
        elif 'context' in error_msg.lower():
            print(f"  💡 Suggestion: Prompt exceeds model context window")
            print(f"  💡 Try: Reduce input data or use a model with larger context")

        raise


def parse_ai_response(response_text):
    """
    解析AI的响应，提取JSON

    Args:
        response_text: AI的响应文本

    Returns:
        dict: 解析后的JSON数据
    """
    print(f"\n[3/5] Parsing AI response...")

    # 检测JSON是否被截断
    if response_text.count('{') > response_text.count('}'):
        print(f"  ⚠ Warning: JSON appears to be truncated (more {{ than }})")
        print(f"  ⚠ Attempting to fix truncated JSON...")

        # 尝试补全JSON
        try:
            # 找到最后一个完整的对象
            last_complete_obj = -1
            brace_count = 0
            for i, char in enumerate(response_text):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_complete_obj = i

            if last_complete_obj > 0:
                # 截取到最后一个完整对象
                truncated_json = response_text[:last_complete_obj + 1]

                # 检查是否是数组的一部分
                if '"schedule":[' in truncated_json:
                    # schedule数组可能被截断，尝试补全
                    if not truncated_json.rstrip().endswith(']'):
                        # 补全schedule数组和对象
                        if truncated_json.rstrip().endswith('}'):
                            truncated_json = truncated_json.rstrip() + ']'
                        elif truncated_json.rstrip().endswith('},'):
                            truncated_json = truncated_json.rstrip()[:-1] + ']'

                # 补全整个JSON对象
                if not truncated_json.rstrip().endswith('}'):
                    # 需要添加filtered_source_data（如果缺失）
                    if 'filtered_source_data' not in truncated_json:
                        if truncated_json.rstrip().endswith(']'):
                            truncated_json = truncated_json.rstrip() + ',"filtered_source_data":[]}'
                        else:
                            truncated_json = truncated_json.rstrip() + '],"filtered_source_data":[]}'
                    else:
                        # filtered_source_data存在但被截断
                        if truncated_json.rstrip().endswith('['):
                            truncated_json = truncated_json.rstrip() + ']}'
                        else:
                            truncated_json = truncated_json.rstrip() + ']}'

                print(f"  ✓ Attempting to parse fixed JSON...")
                data = json.loads(truncated_json)
                print(f"  ✓ Parsed truncated JSON successfully")
                print(f"  ⚠ Note: Some data may be missing due to truncation")
                return data
        except Exception as e:
            print(f"  ✗ Failed to fix truncated JSON: {e}")

    # 如果响应文本包含推理过程，尝试从中提取 JSON
    if response_text and ('让我分析' in response_text or '首先' in response_text or '接下来' in response_text):
        print(f"  ⚠ Response contains reasoning text, attempting to extract JSON...")

        # 尝试找到 JSON 开始的位置（查找 { 或 ```json）
        json_start = -1

        # 方法1: 查找 ```json 代码块
        if '```json' in response_text:
            json_start = response_text.find('```json')
            json_end = response_text.find('```', json_start + 7)
            if json_end > json_start:
                json_str = response_text[json_start + 7:json_end].strip()
                print(f"  ✓ Found JSON code block")
                try:
                    data = json.loads(json_str)
                    print(f"  ✓ JSON parsed successfully")
                    return data
                except json.JSONDecodeError as e:
                    print(f"  ✗ Failed to parse JSON from code block: {e}")

        # 方法2: 查找第一个 { 和最后一个 }
        if '{' in response_text and '}' in response_text:
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')

            # 尝试从这个范围提取 JSON
            json_str = response_text[first_brace:last_brace + 1]
            print(f"  ✓ Extracting JSON from position {first_brace} to {last_brace}")

            try:
                data = json.loads(json_str)
                print(f"  ✓ JSON parsed successfully")
                return data
            except json.JSONDecodeError as e:
                print(f"  ✗ Failed to parse extracted JSON: {e}")
                print(f"  Trying to fix common JSON issues...")

                # 尝试修复：移除注释和多余的逗号
                import re
                # 移除 // 注释
                json_str = re.sub(r'//.*?\n', '\n', json_str)
                # 移除 /* */ 注释
                json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

                try:
                    data = json.loads(json_str)
                    print(f"  ✓ JSON parsed successfully after cleanup")
                    return data
                except:
                    pass

        # 如果都失败了，抛出错误
        print(f"  ✗ Could not extract valid JSON from reasoning text")
        print(f"  Response preview (first 500 chars):")
        print(f"  {response_text[:500]}")
        raise ValueError("Could not extract valid JSON from AI reasoning response")

    # 尝试直接解析
    try:
        data = json.loads(response_text)
        print(f"  ✓ JSON parsed successfully")
        return data
    except json.JSONDecodeError:
        pass

    # 尝试提取markdown代码块
    if "```json" in response_text:
        # 提取 ```json 和 ``` 之间的内容
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        if end > start:
            json_str = response_text[start:end].strip()
            try:
                data = json.loads(json_str)
                print(f"  ✓ JSON parsed from markdown code block")
                return data
            except json.JSONDecodeError as e:
                print(f"  ✗ Failed to parse JSON: {e}")
                raise
    elif "```" in response_text:
        # 提取第一个 ``` 和 ``` 之间的内容
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        if end > start:
            json_str = response_text[start:end].strip()
            # 移除可能的语言标记（如 "json"）
            lines = json_str.split('\n')
            if lines and lines[0].strip() in ['json', 'JSON']:
                json_str = '\n'.join(lines[1:])
            try:
                data = json.loads(json_str)
                print(f"  ✓ JSON parsed from code block")
                return data
            except json.JSONDecodeError as e:
                print(f"  ✗ Failed to parse JSON: {e}")
                raise

    print(f"  ✗ No valid JSON found in response")
    print(f"  Response preview (first 200 chars):")
    print(f"  {response_text[:200]}")
    raise ValueError("Could not extract valid JSON from AI response")


def validate_json_schema(data):
    """
    验证JSON数据是否符合schema

    Args:
        data: 解析后的JSON数据

    Returns:
        bool: 验证是否通过
    """
    print(f"\n[4/5] Validating JSON schema...")

    # 基本结构验证
    if not isinstance(data, dict):
        print(f"  ✗ Root is not an object")
        return False

    if 'schedule' not in data:
        print(f"  ✗ Missing 'schedule' field")
        return False

    if not isinstance(data['schedule'], list):
        print(f"  ✗ 'schedule' is not an array")
        return False

    if 'filtered_source_data' not in data:
        print(f"  ✗ Missing 'filtered_source_data' field")
        return False

    # 验证schedule数组
    for i, day in enumerate(data['schedule']):
        if not isinstance(day, dict):
            print(f"  ✗ Schedule item {i} is not an object")
            return False

        # 只检查必需的核心字段
        required_fields = ['date', 'type', 'work_orders']
        for field in required_fields:
            if field not in day:
                print(f"  ✗ Schedule item {i} missing field '{field}'")
                return False

        if day['type'] not in ['normal', 'special']:
            print(f"  ✗ Schedule item {i} has invalid type '{day['type']}'")
            return False

        if day['type'] == 'normal' and 'time_range' not in day:
            print(f"  ✗ Normal schedule item {i} missing 'time_range'")
            return False

        if day['type'] == 'special' and 'time_points' not in day:
            print(f"  ✗ Special schedule item {i} missing 'time_points'")
            return False

    print(f"  ✓ JSON schema validation passed")
    print(f"  - Schedule items: {len(data['schedule'])}")
    print(f"  - Source data rows: {len(data['filtered_source_data'])}")

    return True


def post_process_json_data(data):
    """
    后处理JSON数据，修复常见问题

    Args:
        data: 解析后的JSON数据

    Returns:
        dict: 修复后的数据
    """
    print(f"\n[4.5/5] Post-processing JSON data...")

    import re
    from collections import defaultdict

    # 1. 提取系统缩写的辅助函数（与intranet版本一致）
    def extract_english_abbr(system_name, change_name):
        """从系统名称或变更名称中提取英文缩写"""
        if pd.isna(system_name) if hasattr(pd, 'isna') else system_name is None:
            system_name = ""
        if pd.isna(change_name) if hasattr(pd, 'isna') else change_name is None:
            change_name = ""

        system_name = str(system_name).strip()
        change_name = str(change_name).strip()

        # 正则表达式：匹配2个或更多连续的大写字母
        pattern = r'([A-Z]{2,})'

        # 1. 先从 change_name 中查找
        match = re.search(pattern, change_name)
        if match:
            return match.group(1)

        # 2. 再从 system_name 中查找
        match = re.search(pattern, system_name)
        if match:
            return match.group(1)

        return "XXX"

    # 2. 日期去重和排序
    seen_dates = {}
    unique_schedule = []

    for item in data['schedule']:
        date_str = item['date']

        if date_str in seen_dates:
            # 合并到已存在的日期
            existing_item = seen_dates[date_str]
            # 合并work_orders
            existing_item['work_orders'].extend(item['work_orders'])
        else:
            seen_dates[date_str] = item
            unique_schedule.append(item)

    # 按日期排序
    def parse_chinese_date(date_str):
        """Parse Chinese date string like '5月07日'"""
        match = re.match(r'(\d+)月(\d+)日', date_str)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (999, 999)

    unique_schedule.sort(key=lambda x: parse_chinese_date(x['date']))
    data['schedule'] = unique_schedule

    print(f"  ✓ Deduplicated and sorted dates: {len(unique_schedule)} unique dates")

    # 2.5 工单去重（每个日期内，按完整内容去重，而不是只按工单号）
    # 因为可能有不同的任务在同一个日期，所以只有完全相同的content才去重
    for schedule_item in data['schedule']:
        work_orders = schedule_item.get('work_orders', [])

        # 检查work_orders是否是列表
        if not isinstance(work_orders, list):
            print(f"  ⚠ Warning: work_orders is not a list for date {schedule_item.get('date')}")
            continue

        seen_contents = {}
        unique_work_orders = []

        for work_order in work_orders:
            # 检查work_order是否是字典
            if not isinstance(work_order, dict):
                print(f"  ⚠ Warning: work_order is not a dict in deduplication, type: {type(work_order)}")
                continue

            content = work_order.get('content', '')

            # 使用完整content作为key，而不是只用工单号
            # 这样可以保留不同的任务，即使工单号相同
            if content not in seen_contents:
                seen_contents[content] = work_order
                unique_work_orders.append(work_order)
            # else: 重复的content，跳过

        original_count = len(work_orders)
        schedule_item['work_orders'] = unique_work_orders
        final_count = len(unique_work_orders)

        if original_count != final_count:
            print(f"  ⚠ Date {schedule_item['date']}: removed {original_count - final_count} duplicate work orders")

    print(f"  ✓ Deduplicated work orders within each date")

    # 3. 修复work_order内容格式（只修复缩写，不重新分配工单）
    if 'filtered_source_data' in data and len(data['filtered_source_data']) > 0:
        # 创建工单完整号到源数据的映射（使用完整工单号而不是后4位）
        source_data_map = {}
        for row in data['filtered_source_data']:
            work_order = str(row.get('工單號', ''))
            # 使用完整工单号和提單人组合作为key，避免冲突
            submitter = str(row.get('提單人', ''))
            key = f"{work_order}_{submitter}"
            source_data_map[key] = row

        # 创建工单号后4位到完整信息的映射（用于查找正确的缩写）
        abbr_map = {}
        for row in data['filtered_source_data']:
            work_order = str(row.get('工單號', ''))
            last_4_digits = work_order[-4:] if len(work_order) >= 4 else work_order
            change_name = str(row.get('變更名稱', ''))
            system_name = str(row.get('變更系統名稱匯總', ''))

            # 提取正确的系统缩写
            abbr = extract_english_abbr(system_name, change_name)

            # 存储缩写（使用工单号后4位作为key）
            if last_4_digits not in abbr_map:
                abbr_map[last_4_digits] = abbr

        # 只修复content中的英文缩写部分，不改变工单的日期分配
        for schedule_item in data['schedule']:
            work_orders = schedule_item.get('work_orders', [])

            # 检查work_orders是否是列表
            if not isinstance(work_orders, list):
                print(f"  ⚠ Warning: work_orders is not a list for date {schedule_item.get('date')}, type: {type(work_orders)}")
                continue

            for work_order in work_orders:
                # 检查work_order是否是字典
                if not isinstance(work_order, dict):
                    print(f"  ⚠ Warning: work_order is not a dict, type: {type(work_order)}, value: {work_order}")
                    continue

                content = work_order.get('content', '')

                # 检查格式是否正确
                pattern = r'^\(中台\)\s+(\d{4})\s+([A-Z]{2,})\s+([\u4e00-\u9fa5]+)'

                match = re.match(pattern, content)
                if match:
                    # 格式正确，但可能缩写不对
                    last_4_digits = match.group(1)
                    current_abbr = match.group(2)
                    chinese_name = match.group(3)

                    # 如果有更正确的缩写，使用它
                    if last_4_digits in abbr_map and abbr_map[last_4_digits] != current_abbr:
                        correct_abbr = abbr_map[last_4_digits]
                        # 更新content，只替换缩写部分
                        new_content = f"(中台) {last_4_digits} {correct_abbr} {chinese_name}"
                        work_order['content'] = new_content
                else:
                    # 格式完全错误，尝试修复
                    # 提取工单号后4位
                    match = re.search(r'(\d{4})', content)
                    if match:
                        last_4_digits = match.group(1)

                        # 从abbr_map获取正确的缩写
                        if last_4_digits in abbr_map:
                            correct_abbr = abbr_map[last_4_digits]

                            # 提取中文姓名（如果有的话）
                            name_match = re.search(r'([\u4e00-\u9fa5]+)', content)
                            chinese_name = name_match.group(1) if name_match else "Unknown"

                            # 重新生成content
                            new_content = f"(中台) {last_4_digits} {correct_abbr} {chinese_name}"
                            work_order['content'] = new_content
                            work_order['person'] = chinese_name

        print(f"  ✓ Fixed English abbreviations in work orders")

    # 4. 对于special类型，确保time_points去重和排序
    for schedule_item in data['schedule']:
        if schedule_item['type'] == 'special' and 'time_points' in schedule_item:
            time_points = schedule_item['time_points']

            # 去重
            seen = set()
            unique_points = []
            for tp in time_points:
                if tp not in seen:
                    seen.add(tp)
                    unique_points.append(tp)

            # 排序
            def parse_time(time_str):
                """Parse time string like '01:00' to minutes"""
                try:
                    parts = str(time_str).strip().split(':')
                    return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
                except:
                    return 0

            unique_points.sort(key=parse_time)
            schedule_item['time_points'] = unique_points

    # 5. 确保filtered_source_data包含所有列
    if 'filtered_source_data' in data and len(data['filtered_source_data']) > 0:
        # 检查第一行的列数
        first_row_cols = set(data['filtered_source_data'][0].keys())
        print(f"  ✓ filtered_source_data has {len(first_row_cols)} columns")

        # 确保所有行都有相同的列
        for i, row in enumerate(data['filtered_source_data']):
            row_cols = set(row.keys())
            if row_cols != first_row_cols:
                print(f"  ⚠ Warning: Row {i} has different columns")

    print(f"  ✓ Post-processing completed")

    return data


def validate_and_fix_data_completeness(data, ai_data_text):
    """
    验证数据完整性，确保没有遗漏工单

    Args:
        data: AI返回的数据
        ai_data_text: AI输入的文本数据

    Returns:
        dict: 修复后的数据
    """
    print(f"\n[4.6/5] Validating data completeness...")

    # 从ai_data_text中提取工单号列表
    import re
    work_orders_in_input = set()

    # 查找所有工單號
    matches = re.findall(r'工單號:\s*([A-Z]+-\d+)', ai_data_text)
    for match in matches:
        work_orders_in_input.add(match)

    # 从filtered_source_data中提取工单号
    work_orders_in_output = set()
    if 'filtered_source_data' in data:
        for row in data['filtered_source_data']:
            work_order = row.get('工單號', '')
            if work_order:
                work_orders_in_output.add(work_order)

    # 检查是否有遗漏
    missing_work_orders = work_orders_in_input - work_orders_in_output
    if missing_work_orders:
        print(f"  ⚠ Warning: {len(missing_work_orders)} work orders may be missing")
        for wo in list(missing_work_orders)[:5]:
            print(f"     - {wo}")
        if len(missing_work_orders) > 5:
            print(f"     - ... and {len(missing_work_orders) - 5} more")
    else:
        print(f"  ✓ All work orders are present")

    # 从schedule中统计工单数量
    total_work_orders_in_schedule = 0
    for schedule_item in data.get('schedule', []):
        total_work_orders_in_schedule += len(schedule_item.get('work_orders', []))

    print(f"  ✓ Total work orders in schedule: {total_work_orders_in_schedule}")
    print(f"  ✓ Total rows in filtered_source_data: {len(data.get('filtered_source_data', []))}")

    return data


def process_with_ai(api_key, base_url, model, rules_text, ai_data_text, thursday_count, max_tokens=32768):
    """
    使用AI处理数据

    Args:
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        rules_text: 转换规则
        ai_data_text: Excel数据文本
        thursday_count: 周四人数参数
        max_tokens: 最大输出tokens

    Returns:
        dict: AI返回的结构化数据
    """
    # 组装prompt
    prompt = assemble_prompt(rules_text, ai_data_text, thursday_count)

    # 调用AI API
    response = call_ai_api(api_key, base_url, model, prompt, max_tokens)

    # 解析响应
    data = parse_ai_response(response)

    # 验证schema
    if not validate_json_schema(data):
        raise ValueError("JSON schema validation failed")

    # 后处理数据（修复常见问题）
    data = post_process_json_data(data)

    # 验证数据完整性
    data = validate_and_fix_data_completeness(data, ai_data_text)

    return data


if __name__ == "__main__":
    # 测试代码
    from data_processor import load_config, load_and_process_excel

    config = load_config()

    # 读取规则文件
    rules_file = os.path.join(config['base_dir'], 'prompts', 'transform_rules.md')
    with open(rules_file, 'r', encoding='utf-8') as f:
        rules_text = f.read()

    # 加载数据
    df, ai_data_text = load_and_process_excel(config['input_file'])

    # 调用AI
    result = process_with_ai(
        config['api_key'],
        config['base_url'],
        config['model'],
        rules_text,
        ai_data_text,
        config['thursday_person_count']
    )

    print("\n" + "=" * 60)
    print("AI Response:")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2)[:500])
    print("...")
