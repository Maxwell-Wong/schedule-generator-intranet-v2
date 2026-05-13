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
                max_tokens=max_tokens,
                stream=False,
                presence_penalty=0.0,
                frequency_penalty=0.0
            )

            # 获取响应内容
            if hasattr(completion, 'choices') and len(completion.choices) > 0:
                message = completion.choices[0].message

                # 打印所有可用字段用于调试
                print(f"  [OK] API call successful")
                print(f"  Inspecting response fields...")
                content_candidates = []

                # 检查所有可能的字段
                for attr in ['content', 'reasoning_content', 'text', 'refusal']:
                    if hasattr(message, attr):
                        val = getattr(message, attr)
                        if val:
                            content_candidates.append((attr, val))
                            print(f"    - {attr}: {len(val)} chars")

                # 确定使用哪个字段
                if len(content_candidates) == 0:
                    print(f"  [WARNING] All content fields are empty")
                    if hasattr(message, 'content'):
                        content = message.content or ""
                    else:
                        raise ValueError("API returned empty response")
                elif len(content_candidates) == 1:
                    attr, content = content_candidates[0]
                    print(f"  [OK] Using {attr} ({len(content)} chars)")
                else:
                    # 多个字段，优先使用 content
                    if hasattr(message, 'content') and message.content:
                        content = message.content
                        print(f"  [OK] Using content field")
                    elif hasattr(message, 'text') and message.text:
                        content = message.text
                        print(f"  [OK] Using text field")
                    else:
                        attr, content = content_candidates[0]
                        print(f"  [WARNING] Using {attr}")

                if not content or len(content.strip()) == 0:
                    raise ValueError("API returned empty content")

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
                retry_reason = "Gateway timeout"
            elif '502' in error_msg or '503' in error_msg:
                should_retry = True
                retry_reason = "Server error"
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
                # 不重试或重试次数用完
                if should_retry and attempt >= max_retries - 1:
                    print(f"  [ERROR] Max retries ({max_retries}) exceeded")
                print(f"  [ERROR] API call failed: {error_type}: {error_msg}")
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

    # 尝试直接解析 JSON
    try:
        data = json.loads(response_text)
        print(f"  [OK] JSON parsed successfully")
        return data
    except json.JSONDecodeError:
        pass

    # 如果包含 ```json 代码块，提取并解析
    if "```json" in response_text:
        print(f"  [INFO] Found JSON code block, extracting...")
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        if end > start:
            json_str = response_text[start:end].strip()
            try:
                data = json.loads(json_str)
                print(f"  [OK] JSON parsed from markdown code block")
                return data
            except json.JSONDecodeError as e:
                print(f"  [ERROR] Failed to parse JSON from code block: {e}")

    # 提取第一个 { 和最后一个 } 之间的内容
    if '{' in response_text and '}' in response_text:
        first_brace = response_text.find('{')
        last_brace = response_text.rfind('}')
        json_str = response_text[first_brace:last_brace + 1]
        print(f"  [OK] Extracting JSON from position {first_brace} to {last_brace}")
        try:
            data = json.loads(json_str)
            print(f"  [OK] JSON parsed successfully")
            return data
        except json.JSONDecodeError as e:
            print(f"  [ERROR] Failed to parse extracted JSON: {e}")

    print(f"  [ERROR] No valid JSON found in response")
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

    # 验证schedule数组
    for i, day in enumerate(data['schedule']):
        if not isinstance(day, dict):
            print(f"  [ERROR] Schedule item {i} is not an object")
            return False

        required_fields = ['date', 'type', 'work_orders']
        for field in required_fields:
            if field not in day:
                print(f"  [ERROR] Schedule item {i} missing field '{field}'")
                return False

        if day['type'] not in ['normal', 'special']:
            print(f"  [ERROR] Schedule item {i} has invalid type '{day['type']}'")
            return False

    print(f"  [OK] JSON schema validation passed")
    return True


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
        save_response: 是否保存响应
        max_retries: 最大重试次数

    Returns:
        dict: AI返回的结构化数据
    """
    # 组装prompt
    prompt = assemble_prompt(rules_text, ai_data_text, thursday_count)

    # 调用AI API
    response = call_ai_api(api_key, base_url, model, prompt, max_tokens, max_retries=max_retries)

    # 解析响应
    data = parse_ai_response(response)

    # 验证schema
    if not validate_json_schema(data):
        raise ValueError("JSON schema validation failed")

    # 保存 AI 响应（包含原始响应）
    if save_response:
        try:
            save_ai_response(data, raw_response=response)
        except Exception as e:
            print(f"  [WARNING] Failed to save AI response: {e}")

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
        config['thursday_person_count'],
        config.get('max_tokens', 32768)
    )

    print("\n" + "=" * 60)
    print("AI Response:")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
