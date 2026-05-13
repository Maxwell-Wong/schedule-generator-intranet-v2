#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据处理器（第4部分）
将Excel数据转换为AI友好的文本格式
"""

import pandas as pd
import sys
import os


def get_base_dir():
    """获取程序运行的基础目录，兼容 PyInstaller 打包后的环境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        # 优先返回当前工作目录（用于查找 config.ini 等用户配置文件）
        cwd = os.getcwd()
        if os.path.exists(os.path.join(cwd, 'config.ini')):
            return cwd

        # 如果当前目录没有 config.ini，尝试 _MEIPASS 临时目录
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass and os.path.exists(meipass):
            return meipass
        # 如果 _MEIPASS 不存在，返回可执行文件所在目录
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))


def load_config(config_file='config.ini'):
    """加载配置文件"""
    import configparser
    config = configparser.ConfigParser()

    base_dir = get_base_dir()
    config_path = os.path.join(base_dir, config_file)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found at {config_path}")

    config.read(config_path, encoding='utf-8')

    # 读取过滤规则配置
    removed_status = config.get('filter', 'removed_status', fallback='已撤銷')
    removed_teams_str = config.get('filter', 'removed_teams', fallback='安全內控團隊,前端網路團隊,系統平臺團隊')
    removed_teams = [t.strip() for t in removed_teams_str.split(',') if t.strip()]
    remove_serial_column = config.getboolean('filter', 'remove_serial_column', fallback=True)

    return {
        'base_dir': base_dir,
        'input_file': os.path.join(base_dir, config.get('paths', 'input_file')),
        'output_file': os.path.join(base_dir, config.get('paths', 'output_file')),
        'api_key': config.get('api', 'api_key'),
        'base_url': config.get('api', 'base_url'),
        'model': config.get('api', 'model'),
        'max_tokens': config.getint('api', 'max_tokens', fallback=32768),
        'thursday_person_count': config.getint('settings', 'thursday_person_count', fallback=6),
        # 过滤规则
        'removed_status': removed_status,
        'removed_teams': removed_teams,
        'remove_serial_column': remove_serial_column
    }


def process_source_data(source_file, config=None):
    """
    处理源数据：
    1. 读取Excel文件
    2. 根据配置移除指定列
    3. 根据配置过滤工单状态
    4. 根据配置过滤提单所属团队
    5. 返回过滤后的数据

    Args:
        source_file: 输入Excel文件路径
        config: 配置字典（从load_config()获取）

    Returns:
        DataFrame: 过滤后的数据
    """
    print(f"[1/5] Processing source data: {source_file}")

    try:
        # 尝试读取"变更明细数据报表"sheet，如果不存在则读取第一个sheet
        xls = pd.ExcelFile(source_file)
        sheet_name = '变更明细数据报表'
        if sheet_name in xls.sheet_names:
            df = pd.read_excel(source_file, sheet_name=sheet_name)
            print(f"  [OK] Reading sheet: {sheet_name}")
        else:
            df = pd.read_excel(source_file)
            print(f"  [OK] Reading first sheet: {xls.sheet_names[0]}")
    except Exception as e:
        print(f"[ERROR] Failed to read Excel file: {e}")
        raise

    print(f"  Original shape: {df.shape}")

    # 从配置获取过滤规则
    if config is None:
        config = load_config()

    # 移除指定列（如'序号'）
    if config.get('remove_serial_column', True):
        if '序号' in df.columns:
            df = df.drop(columns=['序号'])
            print(f"  [OK] Removed '序号' column (per config)")

    # 过滤工单状态（从配置读取）
    removed_status = config.get('removed_status', '已撤銷')
    if removed_status and '工单状态' in df.columns:
        initial_rows = len(df)
        df = df[df['工单状态'] != removed_status]
        removed_rows = initial_rows - len(df)
        print(f"  [OK] Removed {removed_rows} rows with '工单状态' = '{removed_status}' (per config)")

    # 过滤提单所属团队（从配置读取）
    removed_teams = config.get('removed_teams', [])
    if removed_teams and '提單人所屬團隊' in df.columns:
        initial_rows = len(df)
        df = df[~df['提單人所屬團隊'].isin(removed_teams)]
        removed_rows = initial_rows - len(df)
        print(f"  [OK] Removed {removed_rows} rows with '提單人所屬團隊' in {removed_teams} (per config)")

    print(f"  Final shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")

    return df


def excel_to_ai_format(df):
    """
    将DataFrame转换为AI友好的文本格式（简化版，减少token使用）

    Args:
        df: pandas DataFrame，源数据

    Returns:
        str: AI友好的文本格式
    """
    text = f"工单数据({len(df)}行):\n\n"

    # 只输出关键字段，减少token使用
    key_fields = ['工單號', '變更名稱', '變更系統名稱匯總', '提單人', '計劃開始時間', '計劃結束時間']

    for idx, row in df.iterrows():
        text += f"工单{idx + 1}:\n"
        for col in key_fields:
            if col in df.columns:
                value = row[col]
                if pd.notna(value):
                    # 输出完整值（包括日期）
                    text += f"{col}: {value}\n"
        text += "\n"

    return text


def load_and_process_excel(input_file, config=None):
    """
    加载并处理Excel文件

    Args:
        input_file: 输入Excel文件路径
        config: 配置字典（可选，如果为None则自动加载）

    Returns:
        tuple: (filtered_df, ai_text)
            - filtered_df: 过滤后的DataFrame
            - ai_text: AI友好的文本格式
    """
    # 加载配置（如果未提供）
    if config is None:
        config = load_config()

    # 处理源数据（使用配置中的过滤规则）
    df_filtered = process_source_data(input_file, config)

    # 转换为AI格式
    ai_text = excel_to_ai_format(df_filtered)

    return df_filtered, ai_text


if __name__ == "__main__":
    # 测试代码
    config = load_config()
    df, text = load_and_process_excel(config['input_file'])

    print("\n" + "=" * 60)
    print("AI Text Preview (first 500 chars):")
    print("=" * 60)
    print(text[:500])
    print("...")
