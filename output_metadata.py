#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
输出元数据（硬编码部分3）
定义输出的文件名、Sheet名称、标题等内容
"""


# ==================== 输出文件配置 ====================
OUTPUT_CONFIG = {
    "filename": "output_transformed.xlsx",
    "sheets": [
        {
            "name": "0507 - 變更人員時間安排表",
            "title": "应用變更人員時間安排表0507",
            "title_merge": "A1:F1"
        },
        {
            "name": "变更明细数据报表",
            "title": "中台工單",
            "title_cell": "A1"
        }
    ]
}


def get_output_filename():
    """获取输出文件名"""
    return OUTPUT_CONFIG["filename"]


def get_sheets_config():
    """获取所有Sheet配置"""
    return OUTPUT_CONFIG["sheets"]


def get_schedule_sheet_config():
    """获取排班表Sheet配置"""
    return OUTPUT_CONFIG["sheets"][0]


def get_data_sheet_config():
    """获取数据明细Sheet配置"""
    return OUTPUT_CONFIG["sheets"][1]
