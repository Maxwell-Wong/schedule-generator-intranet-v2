#!/usr/bin/env python3
# -*- co·ding: utf-8 -*-

"""
主入口
整合所有模块，生成排班表
"""

import os
import sys

import data_processor
import ai_client
import excel_generator


def main():
    """主函数"""
    print("=" * 60)
    print("AI-Driven Schedule Generator v2.0")
    print("=" * 60)

    # 加载配置
    try:
        config = data_processor.load_config()
    except Exception as e:
        print(f"\n[ERROR] Configuration file loading failed: {e}")
        print("Please ensure config.ini file exists and is correctly formatted")
        return 1

    print(f"\nConfiguration loaded:")
    print(f"  Input file: {config['input_file']}")
    print(f"  Output file: {config['output_file']}")
    print(f"  Model: {config['model']}")

    # 检查输入文件是否存在
    if not os.path.exists(config['input_file']):
        print(f"\n[ERROR] Input file not found: {config['input_file']}")
        return 1

    # 读取转换规则
    rules_file = os.path.join(config['base_dir'], 'prompts', 'transform_rules.md')
    if not os.path.exists(rules_file):
        print(f"\n[ERROR] Rules file not found: {rules_file}")
        return 1

    with open(rules_file, 'r', encoding='utf-8') as f:
        rules_text = f.read()

    print(f"  Rules file: {rules_file}")

    # 加载并处理Excel数据
    try:
        df_filtered, ai_data_text = data_processor.load_and_process_excel(config['input_file'])
    except Exception as e:
        print(f"\n[ERROR] Failed to load Excel file: {e}")
        return 1

    # 调用AI处理数据
    try:
        json_data = ai_client.process_with_ai(
            config['api_key'],
            config['base_url'],
            config['model'],
            rules_text,
            ai_data_text,
            config['thursday_person_count'],
            config.get('max_tokens', 40000)
        )
    except Exception as e:
        print(f"\n[ERROR] AI processing failed: {e}")
        return 1

    # 生成Excel文件
    try:
        excel_generator.generate_excel(json_data, config['output_file'], df_filtered)
    except Exception as e:
        print(f"\n[ERROR] Excel generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print(f"\n[SUCCESS] All tasks completed successfully!")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        # input("\nPress Enter to exit...")  # Commented out for non-interactive use
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
