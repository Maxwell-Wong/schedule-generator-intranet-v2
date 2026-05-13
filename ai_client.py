#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI客户端
调用AI API（Qwen27B或其他模型）处理排班规则
"""

import json
import os
import pandas as pd
from datetime import datetime
from openai import OpenAI
import data_processor


def load_prompt_template(template_file='prompts/ai_prompt_ultra_short.txt'):
    """
    加载prompt模板文件

    Args:
        template_file: 模板文件路径

    Returns:
        str: 模板内容
    """
    # 使用统一的路径查找逻辑
    base_dir = data_processor.get_base_dir()
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


def call_ai_api(api_key, base_url, model, prompt, max_tokens=32768, max_retries=3):
    """
    调用AI API（带重试机制）

    Args:
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        prompt: 发送给AI的prompt
        max_tokens: 最大输出tokens
        max_retries: 最大重试次数（默认：3）

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
        print(f"  [WARNING] Warning: Prompt is very long ({estimated_tokens} tokens)")
        print(f"  This might exceed model context limits")
        response = input(f"  Continue anyway? (y/n): ")
        if response.lower() != 'y':
            raise ValueError("User cancelled due to long prompt")

    # 重试循环
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"  [RETRY] Attempt {attempt + 1}/{max_retries}...")

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
                    print(f"  [WARNING] WARNING: No JSON found in any content field!")
                    print(f"  [WARNING] The model appears to be stuck in a reasoning loop.")

                    # 检查是否有重复模式
                    if 'reasoning_content' in [attr for attr, _ in content_candidates]:
                        reasoning = next(val for attr, val in content_candidates if attr == 'reasoning_content')

                        # 检测重复内容
                        lines = reasoning.split('\n')
                        unique_lines = set(lines)
                        if len(lines) > 100 and len(unique_lines) < len(lines) * 0.3:
                            print(f"  [WARNING] Detected repetitive content (possible loop)")
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
                    print(f"  [WARNING] All content fields are empty or None")
                    # 尝试获取空字符串
                    if hasattr(message, 'content'):
                        content = message.content or ""
                        print(f"  [OK] Using empty content field")
                    else:
                        raise ValueError("API returned empty response")

                elif len(content_candidates) == 1:
                    # 只有一个字段有内容
                    attr, content = content_candidates[0]
                    print(f"  [OK] Using {attr} ({len(content)} chars)")

                else:
                    # 多个字段都有内容，需要判断哪个是最终结果
                    # reasoning_content 通常是推理过程，content 是最终结果
                    if hasattr(message, 'content') and message.content:
                        content = message.content
                        print(f"  [OK] Using content field (final result)")
                    elif hasattr(message, 'text') and message.text:
                        content = message.text
                        print(f"  [OK] Using text field")
                    else:
                        # 使用第一个非空的
                        attr, content = content_candidates[0]
                        print(f"  [WARNING] Multiple fields found, using {attr}")

                # 检查内容是否以 JSON 标记开头
                if content and not content.strip().startswith(('{', '```', '[')):
                    print(f"  [WARNING] Warning: Content doesn't look like JSON")
                    print(f"  Content preview: {content[:200]}")

                    # 如果 reasoning_content 看起来像推理过程
                    if '让我分析' in content or '首先' in content or '接下来' in content:
                        print(f"  [WARNING] This appears to be reasoning process, not final JSON")
                        print(f"  💡 Suggestion: The model may be in 'thinking mode'")
                        print(f"  💡 Try: Add stronger instructions to output JSON directly")

                if not content or len(content.strip()) == 0:
                    raise ValueError("API returned empty content")

                print(f"  [OK] API call successful")
                print(f"  Response length: {len(content)} characters")
                return content.strip()
            else:
                raise ValueError("Invalid API response format")

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            # 检查是否应该重试
            should_retry = False
            retry_reason = ""

            if '504' in error_msg or 'timeout' in error_msg.lower() or 'Timeout' in error_type:
                should_retry = True
                retry_reason = "Gateway timeout or request timeout"
            elif '502' in error_msg or '503' in error_msg:
                should_retry = True
                retry_reason = "Server error or service unavailable"
            elif 'rate limit' in error_msg.lower():
                should_retry = True
                retry_reason = "Rate limit exceeded"

            # 如果应该重试且还有重试次数
            if should_retry and attempt < max_retries - 1:
                print(f"  [WARNING] API call failed: {error_type}: {error_msg}")
                print(f"  [RETRY] {retry_reason} - Retrying in 5 seconds...")
                import time
                time.sleep(5)
                continue
            else:
                # 不重试或重试次数用完，抛出异常
                print(f"  [ERROR] API call failed: {error_type}: {error_msg}")

                if should_retry and attempt >= max_retries - 1:
                    print(f"  [ERROR] Max retries ({max_retries}) exceeded")

                # 针对不同错误类型给出建议
                if 'timeout' in error_msg.lower() or 'Timeout' in error_type or '504' in error_msg:
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

                print(f"  💡 SUGGESTION:")
                print(f"     1. The minimax-m2.7 model may not be suitable for this task")
                print(f"     2. Try using a different model (e.g., 'meta/llama-3.1-70b-instruct')")
                print(f"     3. Simplify the prompt or reduce input data size")

            # 如果 reasoning_content 存在且看起来像推理过程（不包含 JSON）
            # 则尝试使用 content（即使它看起来为空，可能是空字符串而不是 None）
            if len(content_candidates) == 0:
                print(f"  [WARNING] All content fields are empty or None")
                # 尝试获取空字符串
                if hasattr(message, 'content'):
                    content = message.content or ""
                    print(f"  [OK] Using empty content field")
                else:
                    raise ValueError("API returned empty response")

            elif len(content_candidates) == 1:
                # 只有一个字段有内容
                attr, content = content_candidates[0]
                print(f"  [OK] Using {attr} ({len(content)} chars)")

            else:
                # 多个字段都有内容，需要判断哪个是最终结果
                # reasoning_content 通常是推理过程，content 是最终结果
                if hasattr(message, 'content') and message.content:
                    content = message.content
                    print(f"  [OK] Using content field (final result)")
                elif hasattr(message, 'text') and message.text:
                    content = message.text
                    print(f"  [OK] Using text field")
                else:
                    # 使用第一个非空的
                    attr, content = content_candidates[0]
                    print(f"  [WARNING] Multiple fields found, using {attr}")

            # 检查内容是否以 JSON 标记开头
            if content and not content.strip().startswith(('{', '```', '[')):
                print(f"  [WARNING] Warning: Content doesn't look like JSON")
                print(f"  Content preview: {content[:200]}")

                # 如果 reasoning_content 看起来像推理过程
                if '让我分析' in content or '首先' in content or '接下来' in content:
                    print(f"  [WARNING] This appears to be reasoning process, not final JSON")
                    print(f"  💡 Suggestion: The model may be in 'thinking mode'")
                    print(f"  💡 Try: Add stronger instructions to output JSON directly")

            if not content or len(content.strip()) == 0:
                raise ValueError("API returned empty content")

            print(f"  [OK] API call successful")
            print(f"  Response length: {len(content)} characters")
            return content.strip()
            else:
                raise ValueError("Invalid API response format")

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            # 检查是否应该重试
            should_retry = False
            retry_reason = ""

            if '504' in error_msg or 'timeout' in error_msg.lower() or 'Timeout' in error_type:
                should_retry = True
                retry_reason = "Gateway timeout or request timeout"
            elif '502' in error_msg or '503' in error_msg:
                should_retry = True
                retry_reason = "Server error or service unavailable"
            elif 'rate limit' in error_msg.lower():
                should_retry = True
                retry_reason = "Rate limit exceeded"

            # 如果应该重试且还有重试次数
            if should_retry and attempt < max_retries - 1:
                print(f"  [WARNING] API call failed: {error_type}: {error_msg}")
                print(f"  [RETRY] {retry_reason} - Retrying in 5 seconds...")
                import time
                time.sleep(5)
                continue
            else:
                # 不重试或重试次数用完，抛出异常
                print(f"  [ERROR] API call failed: {error_type}: {error_msg}")

                if should_retry and attempt >= max_retries - 1:
                    print(f"  [ERROR] Max retries ({max_retries}) exceeded")

                # 针对不同错误类型给出建议
                if 'timeout' in error_msg.lower() or 'Timeout' in error_type or '504' in error_msg:
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
        print(f"  [WARNING] Warning: JSON appears to be truncated (more {{ than }})")
        print(f"  [WARNING] Attempting to fix truncated JSON...")

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

                print(f"  [OK] Attempting to parse fixed JSON...")
                data = json.loads(truncated_json)
                print(f"  [OK] Parsed truncated JSON successfully")
                print(f"  [WARNING] Note: Some data may be missing due to truncation")
                return data
        except Exception as e:
            print(f"  [ERROR] Failed to fix truncated JSON: {e}")

    # 如果响应文本包含推理过程，尝试从中提取 JSON
    if response_text and ('让我分析' in response_text or '首先' in response_text or '接下来' in response_text):
        print(f"  [WARNING] Response contains reasoning text, attempting to extract JSON...")

        # 尝试找到 JSON 开始的位置（查找 { 或 ```json）
        json_start = -1

        # 方法1: 查找 ```json 代码块
        if '```json' in response_text:
            json_start = response_text.find('```json')
            json_end = response_text.find('```', json_start + 7)
            if json_end > json_start:
                json_str = response_text[json_start + 7:json_end].strip()
                print(f"  [OK] Found JSON code block")
                try:
                    data = json.loads(json_str)
                    print(f"  [OK] JSON parsed successfully")
                    return data
                except json.JSONDecodeError as e:
                    print(f"  [ERROR] Failed to parse JSON from code block: {e}")

        # 方法2: 查找第一个 { 和最后一个 }
        if '{' in response_text and '}' in response_text:
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')

            # 尝试从这个范围提取 JSON
            json_str = response_text[first_brace:last_brace + 1]
            print(f"  [OK] Extracting JSON from position {first_brace} to {last_brace}")

            try:
                data = json.loads(json_str)
                print(f"  [OK] JSON parsed successfully")
                return data
            except json.JSONDecodeError as e:
                print(f"  [ERROR] Failed to parse extracted JSON: {e}")
                print(f"  Trying to fix common JSON issues...")

                # 尝试修复：移除注释和多余的逗号
                import re
                # 移除 // 注释
                json_str = re.sub(r'//.*?\n', '\n', json_str)
                # 移除 /* */ 注释
                json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

                try:
                    data = json.loads(json_str)
                    print(f"  [OK] JSON parsed successfully after cleanup")
                    return data
                except:
                    pass

        # 如果都失败了，抛出错误
        print(f"  [ERROR] Could not extract valid JSON from reasoning text")
        print(f"  Response preview (first 500 chars):")
        print(f"  {response_text[:500]}")
        raise ValueError("Could not extract valid JSON from AI reasoning response")

    # 尝试直接解析
    try:
        data = json.loads(response_text)
        print(f"  [OK] JSON parsed successfully")
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
                print(f"  [OK] JSON parsed from markdown code block")
                return data
            except json.JSONDecodeError as e:
                print(f"  [ERROR] Failed to parse JSON: {e}")
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
                print(f"  [OK] JSON parsed from code block")
                return data
            except json.JSONDecodeError as e:
                print(f"  [ERROR] Failed to parse JSON: {e}")
                raise

    print(f"  [ERROR] No valid JSON found in response")
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
        print(f"  [ERROR] Root is not an object")
        return False

    if 'schedule' not in data:
        print(f"  [ERROR] Missing 'schedule' field")
        return False

    if not isinstance(data['schedule'], list):
        print(f"  [ERROR] 'schedule' is not an array")
        return False

    if 'filtered_source_data' not in data:
        print(f"  [ERROR] Missing 'filtered_source_data' field")
        return False

    # 验证schedule数组
    for i, day in enumerate(data['schedule']):
        if not isinstance(day, dict):
            print(f"  [ERROR] Schedule item {i} is not an object")
            return False

        # 只检查必需的核心字段
        required_fields = ['date', 'type', 'work_orders']
        for field in required_fields:
            if field not in day:
                print(f"  [ERROR] Schedule item {i} missing field '{field}'")
                return False

        if day['type'] not in ['normal', 'special']:
            print(f"  [ERROR] Schedule item {i} has invalid type '{day['type']}'")
            return False

        if day['type'] == 'normal' and 'time_range' not in day:
            print(f"  [ERROR] Normal schedule item {i} missing 'time_range'")
            return False

        if day['type'] == 'special' and 'time_points' not in day:
            print(f"  [ERROR] Special schedule item {i} missing 'time_points'")
            return False

    print(f"  [OK] JSON schema validation passed")
    print(f"  - Schedule items: {len(data['schedule'])}")
    print(f"  - Source data rows: {len(data['filtered_source_data'])}")

    return True


def distribute_workorders_evenly_with_grouping(items, target_count):
    """
    将工单均匀分配到指定数量的单元格中

    Args:
        items: 工单信息列表，每个元素包含 {'content': 工单文本, 'person': 人员姓名}
        target_count: 目标单元格数量（来自配置的 thursday_person_count）

    Returns:
        list: 分配后的工单列表
    """
    if not items or target_count <= 0:
        return items

    # 提取所有不重复的人员
    persons = {}
    for item in items:
        person = item.get('person', '')
        if person not in persons:
            persons[person] = []
        persons[person].append(item)

    unique_persons = list(persons.keys())
    num_persons = len(unique_persons)

    # 情况1：如果 target_count >= 人员数 → 直接均匀分配（不合并同一人的工单）
    if target_count >= num_persons:
        # 计算每组多少人
        base_size = num_persons // target_count
        extra = num_persons % target_count

        distributed = []
        person_idx = 0

        for i in range(target_count):
            # 这一组的工单
            group_size = base_size + (1 if i < extra else 0)
            group_work_orders = []

            for j in range(group_size):
                if person_idx < num_persons:
                    person = unique_persons[person_idx]
                    # 添加这个人的所有工单
                    group_work_orders.extend(persons[person])
                    person_idx += 1

            # 如果有多个人，合并他们的工单到一个单元格
            if group_work_orders:
                if len(group_work_orders) == 1:
                    distributed.append(group_work_orders[0])
                else:
                    # 合并多个人的工单
                    merged_content = '\n'.join([wo.get('content', '') for wo in group_work_orders])
                    # 使用第一个人的名字作为代表（或者可以合并名字）
                    merged_person = group_work_orders[0].get('person', '')
                    distributed.append({
                        'person': merged_person,
                        'content': merged_content
                    })

        return distributed

    # 情况2：如果 target_count < 人员数 → 同一人的工单合并，其他人均匀分配
    else:
        # 先合并同一人的工单
        merged_persons = {}
        for person, work_orders in persons.items():
            if len(work_orders) == 1:
                merged_persons[person] = work_orders[0]
            else:
                # 合并同一人的多个工单
                merged_content = '\n'.join([wo.get('content', '') for wo in work_orders])
                merged_persons[person] = {
                    'person': person,
                    'content': merged_content
                }

        # 现在有 num_persons 个合并后的工单，需要分配到 target_count 个单元格
        merged_items = list(merged_persons.values())

        # 计算每组多少人
        base_size = num_persons // target_count
        extra = num_persons % target_count

        distributed = []
        person_idx = 0

        for i in range(target_count):
            # 这一组的工单数
            group_size = base_size + (1 if i < extra else 0)
            group_work_orders = []

            for j in range(group_size):
                if person_idx < len(merged_items):
                    group_work_orders.append(merged_items[person_idx])
                    person_idx += 1

            # 如果有多个人的工单，合并到一个单元格
            if group_work_orders:
                if len(group_work_orders) == 1:
                    distributed.append(group_work_orders[0])
                else:
                    # 合并多个人的工单
                    merged_content = '\n'.join([wo.get('content', '') for wo in group_work_orders])
                    merged_person = group_work_orders[0].get('person', '')
                    distributed.append({
                        'person': merged_person,
                        'content': merged_content
                    })

        return distributed


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

    print(f"  [OK] Deduplicated and sorted dates: {len(unique_schedule)} unique dates")

    # 2.5 工单去重（每个日期内，按完整内容去重，而不是只按工单号）
    # 因为可能有不同的任务在同一个日期，所以只有完全相同的content才去重
    for schedule_item in data['schedule']:
        work_orders = schedule_item.get('work_orders', [])

        # 检查work_orders是否是列表
        if not isinstance(work_orders, list):
            print(f"  [WARNING] Warning: work_orders is not a list for date {schedule_item.get('date')}")
            continue

        seen_contents = {}
        unique_work_orders = []

        for work_order in work_orders:
            # 检查work_order是否是字典
            if not isinstance(work_order, dict):
                print(f"  [WARNING] Warning: work_order is not a dict in deduplication, type: {type(work_order)}")
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
            print(f"  [WARNING] Date {schedule_item['date']}: removed {original_count - final_count} duplicate work orders")

    print(f"  [OK] Deduplicated work orders within each date")

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
                print(f"  [WARNING] Warning: work_orders is not a list for date {schedule_item.get('date')}, type: {type(work_orders)}")
                continue

            for work_order in work_orders:
                # 检查work_order是否是字典
                if not isinstance(work_order, dict):
                    print(f"  [WARNING] Warning: work_order is not a dict, type: {type(work_order)}, value: {work_order}")
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

        print(f"  [OK] Fixed English abbreviations in work orders")

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
        print(f"  [OK] filtered_source_data has {len(first_row_cols)} columns")

        # 确保所有行都有相同的列
        for i, row in enumerate(data['filtered_source_data']):
            row_cols = set(row.keys())
            if row_cols != first_row_cols:
                print(f"  [WARNING] Warning: Row {i} has different columns")

    print(f"  [OK] Post-processing completed")

    return data


def validate_and_fix_data_completeness(data, ai_data_text):
    """
    验证数据完整性，自动补充遗漏的工单

    Args:
        data: AI返回的数据
        ai_data_text: AI输入的文本数据

    Returns:
        dict: 修复后的数据
    """
    print(f"\n[4.6/5] Validating and fixing data completeness...")

    import re
    from datetime import datetime

    # 提取系统缩写的辅助函数
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

    # 从ai_data_text中提取所有工单信息
    work_orders_input = []
    current_order = {}
    lines = ai_data_text.split('\n')

    for line in lines:
        if '工單號:' in line:
            if current_order:  # 保存上一个工单
                work_orders_input.append(current_order)
            # 开始新工单
            current_order = {'工單號': line.split(':', 1)[1].strip()}
        elif current_order and line.strip():
            key_val = line.split(':', 1)
            if len(key_val) == 2:
                key = key_val[0].strip()
                value = key_val[1].strip()
                current_order[key] = value

    if current_order:
        work_orders_input.append(current_order)

    # 为每个工单添加到对应的日期
    for wo in work_orders_input:
        if '計劃開始時間' in wo:
            try:
                dt = datetime.strptime(wo['計劃開始時間'], '%Y-%m-%d %H:%M:%S')
                date_str = f"{dt.month}月{dt.day:02d}日"
                wo['date'] = date_str
                wo['datetime'] = dt
            except:
                pass

    print(f"  [OK] Found {len(work_orders_input)} work orders in input")

    # 检查schedule中遗漏的工单
    schedule_by_date = {}
    for item in data.get('schedule', []):
        date = item['date']
        schedule_by_date[date] = item
        # 记录已有的工单号
        item['existing_work_orders'] = set()
        for wo in item.get('work_orders', []):
            content = wo.get('content', '')
            # 提取工单号后4位
            match = re.search(r'(\d{4})', content)
            if match:
                item['existing_work_orders'].add(match.group(1))

    # 找出遗漏的工单并补充
    added_count = 0
    for wo in work_orders_input:
        wo_num = wo['工單號'][-4:]
        date = wo.get('date', '')

        if date in schedule_by_date:
            schedule_item = schedule_by_date[date]
            existing = schedule_item.get('existing_work_orders', set())

            if wo_num not in existing:
                # 这个工单被遗漏了，需要添加
                print(f"  [WARNING] Adding missing work order: {wo_num} ({wo.get('提單人', 'N/A')}) to {date}")

                # 提取系统缩写
                system_name = wo.get('變更系統名稱匯總', '')
                change_name = wo.get('變更名稱', '')
                abbr = extract_english_abbr(system_name, change_name)

                # 提取姓名
                submitter = wo.get('提單人', '')
                match = re.match(r'([^/]+)', submitter)
                chinese_name = match.group(1) if match else submitter

                # 创建work_order对象
                new_work_order = {
                    'person': chinese_name,
                    'content': f"(中台) {wo_num} {abbr} {chinese_name}"
                }

                # 如果是special类型，需要添加time_start和time_end
                if schedule_item['type'] == 'special':
                    try:
                        dt_start = wo.get('datetime')
                        dt_end = datetime.strptime(wo['計劃結束時間'], '%Y-%m-%d %H:%M:%S')
                        time_start = dt_start.strftime('%H:%M')
                        time_end = dt_end.strftime('%H:%M')
                        new_work_order['time_start'] = time_start
                        new_work_order['time_end'] = time_end
                    except:
                        pass

                schedule_item['work_orders'].append(new_work_order)
                added_count += 1

    if added_count > 0:
        print(f"  [OK] Added {added_count} missing work orders to schedule")
    else:
        print(f"  [OK] All work orders are present in schedule")

    return data


def save_ai_response(data, raw_response=None, base_dir=None):
    """
    保存 AI 返回的 JSON 数据到文件

    Args:
        data: AI 返回的 JSON 数据（解析后）
        raw_response: AI 的原始响应文本（用于调试）
        base_dir: 基础目录（如果为 None，使用 get_base_dir()）
    """
    if base_dir is None:
        base_dir = data_processor.get_base_dir()

    # 创建输出目录
    output_dir = os.path.join(base_dir, 'ai_responses')
    os.makedirs(output_dir, exist_ok=True)

    # 生成文件名（使用时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'ai_response_{timestamp}.json'
    filepath = os.path.join(output_dir, filename)

    # 保存解析后的 JSON 文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] Parsed JSON saved to: {filepath}")

    # 保存原始响应（如果提供）
    if raw_response:
        raw_filename = f'ai_response_raw_{timestamp}.txt'
        raw_filepath = os.path.join(output_dir, raw_filename)
        with open(raw_filepath, 'w', encoding='utf-8') as f:
            f.write(raw_response)
        print(f"[INFO] Raw response saved to: {raw_filepath}")
        print(f"[INFO] Raw response length: {len(raw_response)} characters")

    # 同时保存最新版本（方便访问）
    latest_path = os.path.join(output_dir, 'ai_response_latest.json')
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Latest response saved to: {latest_path}")

    return filepath


def process_with_ai(api_key, base_url, model, rules_text, ai_data_text, thursday_count, max_tokens=32768, save_response=True, max_retries=3):
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
    response = call_ai_api(api_key, base_url, model, prompt, max_tokens, max_retries=max_retries)

    # 解析响应
    data = parse_ai_response(response)

    # 检查解析后的数据是否完整
    if isinstance(data, dict) and 'schedule' in data:
        schedule = data['schedule']
        if isinstance(schedule, list) and len(schedule) > 0:
            last_item = schedule[-1]
            # 检查最后一项是否完整
            is_truncated = False

            # 检查是否有未闭合的字段
            for key, value in last_item.items():
                # 如果字段值是字符串且看起来像被截断
                if isinstance(value, str) and len(value) > 0:
                    # 检查是否以不完整的字符结尾
                    if value.rstrip().endswith(('...', '、', ',', '、')):
                        is_truncated = True
                        break

                # 检查是否有应该是列表但不是的字段
                if key in ['work_orders', 'existing_work_orders', 'time_points']:
                    if not isinstance(value, list):
                        is_truncated = True
                        print(f"  [ERROR] Field '{key}' should be a list but got: {type(value).__name__}")
                        break

            if is_truncated:
                print(f"  [ERROR] AI response was TRUNCATED!")
                print(f"  [ERROR] Last schedule item: {json.dumps(last_item, ensure_ascii=False)[:300]}")
                print(f"  [ERROR]")
                print(f"  [ERROR] Possible causes:")
                print(f"  [ERROR] 1. max_tokens setting is too low (current: {max_tokens})")
                print(f"  [ERROR] 2. AI model has output size limit")
                print(f"  [ERROR] 3. Input data is too large")
                print(f"  [ERROR]")
                print(f"  [ERROR] Solutions:")
                print(f"  [ERROR] - Increase max_tokens in config.ini (try 200000 or higher)")
                print(f"  [ERROR] - Check your AI model's maximum output size")
                print(f"  [ERROR] - Reduce input data size")
                print(f"  [ERROR] - Check raw response in ai_responses/ai_response_raw_*.txt")

                # 不抛出错误，让程序继续运行
                print(f"  [WARNING] Continuing with truncated data...")

    # 保存 AI 响应（包含原始响应）
    if save_response:
        try:
            save_ai_response(data, raw_response=response)
        except Exception as e:
            print(f"  [WARNING] Failed to save AI response: {e}")

    # 验证schema
    if not validate_json_schema(data):
        raise ValueError("JSON schema validation failed")

    # 后处理数据（修复常见问题）
    data = post_process_json_data(data)

    # 验证数据完整性
    data = validate_and_fix_data_completeness(data, ai_data_text)

    # 应用工单分配逻辑（后处理验证和优化）
    if thursday_count is not None:
        print(f"\n[4.7/5] Applying work order distribution (post-processing validation)...")

        import re
        from datetime import datetime

        for schedule_item in data['schedule']:
            work_orders = schedule_item.get('work_orders', [])

            if not isinstance(work_orders, list) or len(work_orders) == 0:
                continue

            # 判断是否需要应用分配逻辑
            needs_distribution = False
            target_count = None

            # 提取日期判断是周几
            date_str = schedule_item['date']
            date_match = re.match(r'(\d+)月(\d+)日', date_str)

            if date_match:
                try:
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    # 使用2026年（根据示例数据）
                    date_obj = datetime(2026, month, day)
                    weekday = date_obj.weekday()  # 0=周一, 3=周四, 5=周六, 6=周日

                    # 周四（weekday=3）且工单数 > thursday_count
                    if weekday == 3 and len(work_orders) > thursday_count:
                        needs_distribution = True
                        target_count = thursday_count

                except Exception as e:
                    print(f"  [WARNING] Warning: Could not parse date {date_str}: {e}")

            # 应用分配逻辑
            if needs_distribution and target_count:
                print(f"  [WARNING] Applying distribution for {schedule_item['date']}: {len(work_orders)} work orders → {target_count} cells")

                # 重新分配工单
                distributed_orders = distribute_workorders_evenly_with_grouping(
                    work_orders,
                    target_count
                )

                schedule_item['work_orders'] = distributed_orders
                print(f"  [OK] Distribution completed: now {len(distributed_orders)} cells")

        print(f"  [OK] Work order distribution completed")

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
