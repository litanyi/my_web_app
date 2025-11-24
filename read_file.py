# -*- coding: utf-8 -*-
from tool import *
from flask import Flask, render_template, request, redirect, url_for, flash
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
import os
import numpy as np
from collections import defaultdict
import pandas as pd
from openpyxl.utils.dataframe import dataframe_to_rows

# ...existing code...

def read_temperature_file_v1(file_path):
    """
    根据文件后缀自动选择读取方式，解析温度-时间数据
    输入：file_path（本地文件路径）
    """
    # 步骤1：获取文件后缀，判断文件类型
    print(file_path)
    file_ext = file_path.rsplit('.', 1)[1].lower()  # 提取后缀（小写）
    time_data = []
    temp_data = []

    if file_ext == 'csv':
        # 情况2：CSV文件 → 读取CSV数据，写入临时Excel，返回临时Sheet
        try:
            # 1. 用pandas读取CSV（处理编码、空行）
            df = pd.read_csv(
                file_path,
                encoding_errors='ignore',  # 忽略编码异常
                skip_blank_lines=True  # 跳过空行
            )
            print(f"成功读取CSV文件：{os.path.basename(file_path)}，数据行数：{len(df)}")

            # 2. 创建临时Excel工作簿（in_memory=True：内存中创建，无物理文件残留）
            wb_temp = openpyxl.Workbook()
            sheet_temp = wb_temp.active  # 临时Sheet（默认名称Sheet）
            sheet_temp.title = "CSV_Data"  # 重命名临时Sheet，便于识别
            # 3. 将CSV数据写入临时Sheet（保留表头，按行写入）
            for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
                # r_idx：Excel行号（从1开始）；row：CSV的一行数据
                for c_idx, value in enumerate(row, 1):
                    # c_idx：Excel列号（从1开始）；value：单元格值
                    sheet_temp.cell(row=r_idx, column=c_idx, value=value)

            print(f"CSV数据已写入临时Sheet：{sheet_temp.title}，表头行：{list(df.columns)}")
            sheet = sheet_temp
        except Exception as e:
            raise RuntimeError(f"CSV文件转换为Sheet失败：{str(e)}")
    elif file_ext == 'xlsx':
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active
    else:
        print('Unknown File Type')
        sheet = []
    return sheet

# ...existing code...

if 1:
    # 步骤1：选择本地Excel文件（已移除 GUI 文件选择，直接使用测试路径或替换为你的路径）
    #file_path = 'test/2rol_TG600S3-1-City-65.csv'
    file_path = 'C:/webframeworks/version_1/models/custom/Temperature.csv'
    # 若需要从命令行或其他方式获取路径，请在此处替换 file_path

    # 步骤2：读取并解析Excel文件
    try:
        # 加载本地Excel文件（替换原网页的request.files）
        sheet = read_temperature_file_v1(file_path)
        print(f"成功读取文件：{os.path.basename(file_path)}（工作表：{getattr(sheet, 'title', 'N/A')}）")

        # 解析温度-时间数据
        sorted_time, sorted_temp = parse_temperature_data(sheet)
        print('sorted_temp', sorted_temp)
        print(f"成功解析 {len(sorted_temp)} 个有效温度-时间数据点")

        # 步骤3：雨流计数
        rainflow_results = rainflow_counting(sorted_temp,plot_flag=True)
        # 损伤度计算（新增接收usage_multiple）
        total_damage, damage_details, usage_multiple = calculate_damage(rainflow_results)
        usage_multiple = int(usage_multiple)
        print(rainflow_results)
        # 损伤状态提示（新增使用次数倍数说明）
        if total_damage >= 1.0:
            print(f'总损伤度 {total_damage}（≥1.0）：材料已达到疲劳失效阈值！')
            print(f'1/损伤度（剩余使用倍数）：{usage_multiple}（表示仅能承受当前损伤量的{usage_multiple}倍，已失效）')
        else:
            print(f'总损伤度 {total_damage}（<1.0）：材料当前处于安全状态')
            print(f'1/损伤度（预估使用倍数）：{usage_multiple}（表示还能承受当前温度循环模式的{usage_multiple}倍）')
    except InvalidFileException:
        print("错误: 无效的Excel文件（可能是文件损坏或版本不兼容）")
    except ValueError as ve:
        print(f"错误: 数据处理错误：{str(ve)}")
    except Exception as e:
        print(f"系统错误：{str(e)}（请检查文件格式是否正确）")