#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
格式化规则（硬编码部分1）
定义排班表的所有格式化设置
"""

from openpyxl.styles import Font, Alignment


# ==================== 标题行格式 ====================
TITLE_FORMAT = {
    "font": Font(name='新宋体', size=30, bold=True),
    "alignment": Alignment(horizontal='center', vertical='center'),
    "merge_range": "A1:F1"
}

# ==================== 日期行格式 ====================
DATE_ROW_FORMAT = {
    "font": Font(name='新宋体', size=26),
    "alignment": Alignment(horizontal='center', vertical='center')
}

# ==================== 时间行格式 ====================
TIME_ROW_FORMAT = {
    "font": Font(name='新宋体', size=14),
    "alignment": Alignment(horizontal='center', vertical='center')
}

# ==================== 数据行格式 ====================
DATA_ROW_FORMAT = {
    "font": Font(name='新宋体', size=14),
    "alignment": {
        "normal": Alignment(horizontal='left', vertical='top', wrap_text=True),
        "special": Alignment(horizontal='center', vertical='center', wrap_text=True)
    }
}

# ==================== 列宽和行高 ====================
COLUMN_WIDTH = 33
ROW_HEIGHT = 90

# ==================== 第二个Sheet的格式 ====================
DATA_SHEET_TITLE_FORMAT = {
    "font": Font(name='新宋体', size=14, bold=True)
}

DATA_SHEET_HEADER_FORMAT = {
    "font": Font(name='新宋体', size=11, bold=True),
    "alignment": Alignment(horizontal='center', vertical='center')
}

DATA_SHEET_CELL_FORMAT = {
    "alignment": Alignment(horizontal='left', vertical='center', wrap_text=True)
}

DATA_SHEET_COLUMN_WIDTH = 15


def get_title_format():
    """获取标题行格式"""
    return TITLE_FORMAT


def get_date_row_format():
    """获取日期行格式"""
    return DATE_ROW_FORMAT


def get_time_row_format():
    """获取时间行格式"""
    return TIME_ROW_FORMAT


def get_data_row_format(row_type='normal'):
    """获取数据行格式"""
    return {
        "font": DATA_ROW_FORMAT["font"],
        "alignment": DATA_ROW_FORMAT["alignment"][row_type]
    }


def get_column_width():
    """获取列宽"""
    return COLUMN_WIDTH


def get_row_height():
    """获取行高"""
    return ROW_HEIGHT


def get_data_sheet_title_format():
    """获取第二个sheet标题格式"""
    return DATA_SHEET_TITLE_FORMAT


def get_data_sheet_header_format():
    """获取第二个sheet列头格式"""
    return DATA_SHEET_HEADER_FORMAT


def get_data_sheet_cell_format():
    """获取第二个sheet单元格格式"""
    return DATA_SHEET_CELL_FORMAT


def get_data_sheet_column_width():
    """获取第二个sheet列宽"""
    return DATA_SHEET_COLUMN_WIDTH
