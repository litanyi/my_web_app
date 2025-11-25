# -*- coding: utf-8 -*-
import numpy as np
from collections import defaultdict

from flask import Flask, render_template, request, redirect, url_for, flash
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
import os
# 用于图形化文件选择框（PC本地选择）
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from openpyxl.utils.dataframe import dataframe_to_rows
from io import StringIO
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["SimHei"]  # 配置中文字体

# 雨流计数法
def rainflow_counting(temperature_data, plot_flag=False):
    """
    基于三点法思路的雨流计数法（温度循环）
    核心改进：新增序列拼接优化、二次峰谷提纯
    输入：温度时序数据列表（数值型）
    输出：字典{温度幅值: 循环次数}（幅值保留2位小数，次数为整数）
    """
    # ----------------------
    # 步骤1：初始数据校验（避免数据量不足）
    # ----------------------
    n = len(temperature_data)
    if n < 3:
        return {}  # 至少3个数据点才能识别循环
    # 转换为numpy数组（便于后续计算，兼容原列表输入）
    temp_data = np.array(temperature_data, dtype=float)

    # ----------------------
    # 步骤2：第一次峰谷提纯（对应三点法步骤一）
    # 目的：移除非极值点，保留纯峰谷交替序列
    # ----------------------
    # 初始化极值点列表（默认保留首尾点）
    turning_points = [temp_data[0]]
    # 遍历中间点，判断是否为峰/谷
    for i in range(1, n - 1):
        prev_val = temp_data[i - 1]
        curr_val = temp_data[i]
        next_val = temp_data[i + 1]

        # 峰点：当前值 > 前后值；谷点：当前值 < 前后值（严格不等，避免平缓段）
        is_peak = (curr_val > prev_val) and (curr_val > next_val)
        is_valley = (curr_val < prev_val) and (curr_val < next_val)

        if is_peak or is_valley:
            turning_points.append(curr_val)
    # 补充最后一个点（确保序列完整）
    if turning_points[-1] != temp_data[-1]:
        turning_points.append(temp_data[-1])


    # 校验第一次提纯后的序列长度（至少2个点才继续，否则无循环）
    if len(turning_points) < 2:
        return {}

    # ----------------------
    # 步骤3：序列拼接优化（对应MATLAB三点法步骤二）
    # 目的：从最值（绝对值最大的峰/谷）拆分拼接，确保首尾均为极值
    # ----------------------
    # 找到绝对值最大的极值点（优先用最大绝对值，而非单纯最大值，更符合MATLAB思路）
    abs_turning = np.abs(turning_points)
    max_abs_idx = np.argmax(abs_turning)  # 绝对值最大点的索引
    # 拆分序列：从最值点拆分为前后两段，再拼接（前半段+后半段）
    B1 = turning_points[max_abs_idx:]  # 最值点到序列末尾
    B2 = turning_points[:max_abs_idx + 1]  # 序列开头到最值点（包含最值点）
    optimized_points = B1 + B2  # 新序列：从最值开始，到最值结束

    # ----------------------
    # 步骤4：第二次峰谷提纯（对应MATLAB三点法步骤三）
    # 目的：消除拼接处可能产生的非极值点，确保序列纯峰谷交替
    # ----------------------
    final_turning = [optimized_points[0]]  # 初始化最终极值点列表
    m = len(optimized_points)
    # 遍历拼接后的中间点，二次校验峰谷
    for i in range(1, m - 1):
        prev_val = optimized_points[i - 1]
        curr_val = optimized_points[i]
        next_val = optimized_points[i + 1]

        is_peak = (curr_val > prev_val) and (curr_val > next_val)
        is_valley = (curr_val < prev_val) and (curr_val < next_val)

        if is_peak or is_valley:
            final_turning.append(curr_val)
    # 补充最后一个点
    if final_turning[-1] != optimized_points[-1]:
        final_turning.append(optimized_points[-1])

    # 最终极值点序列长度校验（至少3个点才进行计数，否则无完整循环）
    if len(final_turning) < 3:
        return {}

    # ----------------------
    # 步骤5：雨流计数核心逻辑（循环识别规则）
    # ----------------------
    rainflow_results = defaultdict(int)
    # 复制输入数据，避免修改原数据（对应MATLAB的Load1=Load）
    Load1 = np.array(final_turning).copy().reshape(-1, 1)  # 转为列向量形式
    Amplitude = []  # 存储循环幅值
    Mean = []       # 存储循环均值
    while len(Load1) >= 1:
        n1 = len(Load1)
        # 若剩余数据1个或2个，无法形成循环，退出计数
        if n1 == 1 or n1 == 2:
            break
        # 遍历查找可计数的循环
        for j in range(n1 - 2):  # Python索引从0开始，对应MATLAB j=1:n1-2
            # 计算相邻两点的幅值（对应MATLAB s1、s2）
            s1 = abs(Load1[j+1] - Load1[j])
            s2 = abs(Load1[j+1] - Load1[j+2])
            # 计算均值（对应MATLAB e3）
            e3 = (Load1[j+1] + Load1[j+2]) / 2
            # 若s1 <= s2，满足计数条件
            if s1 <= s2:
                rainflow_results[s1[0]] += 1  # 循环计数
                Amplitude.append(s1[0])  # 存入幅值（取标量避免维度问题）
                Mean.append(e3[0])       # 存入均值
                # 删除Load1中第j和j+1个元素（对应MATLAB Load1(j)=[]; Load1(j)=[]）
                # Python中删除后索引会自动前移，一次删除两个元素
                Load1 = np.delete(Load1, [j], axis=0)  # 两次删除j索引（因删除第一个后j+1变为j）
                Load1 = np.delete(Load1, [j], axis=0)  # 两次删除j索引（因删除第一个后j+1变为j）
                #print(f"计数幅值: {s1[0]}, 剩余数据: {Load1.flatten().tolist()}")
                break  # 计数一次后跳出内层循环，重新开始外层循环
        else:
            # 若遍历完未找到可计数循环，退出
            break

    D1 = Load1.flatten().tolist()  # 残余数据（转为列表更易使用）
    # 转为numpy数组（可选，方便后续处理）
    Amplitude = np.array(Amplitude)
    Mean = np.array(Mean)

    # ----------------------
    # 步骤7：结果整理
    # ----------------------
    final_results = {}
    for amp, count in rainflow_results.items():
        total_count = round(count)  # 四舍五入为整数（0.5→1，1.5→2，确保次数合理）
        if total_count > 0:  # 只保留有实际循环次数的幅值
            final_results[amp] = total_count

    # 校验最终结果（无有效循环则抛错）
    if not final_results:
        raise ValueError("雨流计数未检测到有效温度循环，可能数据无明显波动")

    # 可视化各步骤结果（使用指定 figure 编号：Figure 1）
    if plot_flag:
        fig1 = plt.figure(num=1, figsize=(12, 8))
        axes = fig1.subplots(2, 2)
        ax0, ax1, ax2, ax3 = axes.flatten()

        ax0.plot(temp_data, '-o', markersize=4)
        ax0.set_title("原始温度序列")
        ax0.set_xlabel("索引")
        ax0.set_ylabel("温度(℃)")
        ax0.grid(True)

        ax1.plot(turning_points, '-o', markersize=4)
        ax1.set_title("第一次峰谷提纯")
        ax1.set_xlabel("样本序号")
        ax1.grid(True)

        ax2.plot(optimized_points, '-o', markersize=4)
        ax2.set_title("序列拼接优化")
        ax2.set_xlabel("样本序号")
        ax2.grid(True)

        ax3.plot(final_turning, '-o', markersize=4)
        ax3.set_title("第二次峰谷提纯（最终）")
        ax3.set_xlabel("样本序号")
        ax3.grid(True)

        fig1.suptitle("步骤可视化", fontsize=12)
        fig1.tight_layout(rect=[0, 0.03, 1, 0.95])  # 为 suptitle 留出空间

    # 新增：在控制台打印并可视化「幅值 -> 次数」（使用 Figure 2）
    if plot_flag:
        # 控制台输出（按幅值排序）
        print("幅值(℃) -> 循环次数:")
        for amp, cnt in sorted(final_results.items()):
            print(f"{amp} ℃ : {cnt} 次")

        # 绘制柱状图显示幅值对应次数并在柱上标注次数（Figure 2）
        amps = sorted(final_results.keys())
        counts = [final_results[a] for a in amps]

        fig2 = plt.figure(num=2, figsize=(6, 4))
        ax2 = fig2.subplots()
        x_labels = [str(a) for a in amps]
        bars = ax2.bar(x_labels, counts, color='C2')
        for rect, v in zip(bars, counts):
            ax2.text(rect.get_x() + rect.get_width() / 2, v + max(counts) * 0.02, str(v),
                     ha='center', va='bottom', fontsize=9)

        ax2.set_title("温度幅值 - 循环次数分布")
        ax2.set_xlabel("幅值 (℃)")
        ax2.set_ylabel("循环次数")
        ax2.grid(axis='y', linestyle='--', alpha=0.4)
        fig2.tight_layout()
        plt.show()

    return final_results

# ----------------------
# 关键修改：损伤度计算函数（新增使用次数倍数计算）
# ----------------------
def calculate_damage(rainflow_results, material_params=None):
    """
    损伤度计算（新增1/损伤度：预估剩余使用次数倍数）
    返回：total_damage（总损伤度）、damage_details（分段详情）、usage_multiple（使用次数倍数）
    """
    # 默认材料参数（通用金属材料）
    if material_params is None:
        material_params = {
            5.0: 100000,  # 幅值5℃：寿命10万次
            10.0: 50000,  # 幅值10℃：寿命5万次
            15.0: 20000,  # 幅值15℃：寿命2万次
            20.0: 10000,  # 幅值20℃：寿命1万次
            25.0: 5000,  # 幅值25℃：寿命5千次
            30.0: 2000,  # 幅值30℃：寿命2千次
            35.0: 1000,  # 幅值35℃：寿命1千次
            40.0: 500  # 幅值40℃：寿命5百次
        }

    total_damage = 0.0
    damage_details = []

    # 计算分段损伤与总损伤
    for amp, cycle_count in sorted(rainflow_results.items()):
        
        # 材料参数插值
        K1 = 7.61e11
        alpha = 1
        beta1 = 3.5252
        if amp == 0:
            fatigue_life = K1 * pow((alpha / (amp + 1e-10)), beta1)
            print(f"警告：amp为{amp}，alpha值为{alpha},cycle_count值为{cycle_count},fatigue_life值为{fatigue_life}")
        else:
            #fatigue_life = K1 * pow((alpha / amp), beta1)
            fatigue_life = K1*pow((alpha/amp),beta1)
        #print(f"读取数据 {amp} ℃ : {cycle_count} 次 : 疲劳寿命 {fatigue_life} 次")
        # 分段损伤计算
        single_damage = 1.0 / fatigue_life
        segment_damage = cycle_count * single_damage
        total_damage += segment_damage

        damage_details.append({
            "amplitude": round(amp, 2),
            "cycle_count": cycle_count,
            "fatigue_life": round(fatigue_life, 0),
            "single_damage": round(single_damage, 6),
            "segment_damage": round(segment_damage, 6)
        })

    total_damage = round(total_damage, 15)  # 保留15位小数，避免浮点误差

    # ----------------------
    # 新增：计算1/损伤度（使用次数倍数）
    # 物理意义：材料在当前温度循环模式下，预估还能承受的“当前损伤量”的倍数
    # ----------------------
    if total_damage == 0:
        usage_multiple = int('inf')  # 损伤度为0时，理论上可无限使用
    elif total_damage >= 1.0:
        usage_multiple = int(1.0 / total_damage)  # 已失效时，输出剩余倍数（<1）
    else:
        usage_multiple = int(1.0 / total_damage)  # 安全状态时，输出可承受倍数（>1）

    return total_damage, damage_details, usage_multiple

# 温度-时间数据解析（不变）
def parse_temperature_data(sheet):
    time_data = []
    temp_data = []

    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=2, values_only=True):
        time_val, temp_val = row
        if time_val is None or temp_val is None:
            continue

        # 时间格式处理
        try:
            if isinstance(time_val, (int, float)):
                time_data.append(float(time_val))
            else:
                time_data.append(float(time_val.toordinal()))
        except (ValueError, TypeError):
            flash(f"忽略无效时间数据: {time_val}（第{len(time_data)+2}行）")
            continue

        # 温度格式处理
        try:
            temp_data.append(float(temp_val))
        except (ValueError, TypeError):
            flash(f"忽略无效温度数据: {temp_val}（第{len(temp_data)+2}行）")
            time_data.pop()
            continue

    # 数据长度对齐与排序
    if len(time_data) != len(temp_data):
        flash("时间与温度数据长度不匹配，已自动修正")
        min_len = min(len(time_data), len(temp_data))
        time_data = time_data[:min_len]
        temp_data = temp_data[:min_len]

    sorted_indices = np.argsort(time_data)
    sorted_time = [time_data[i] for i in sorted_indices]
    sorted_temp = [temp_data[i] for i in sorted_indices]

    # 数据量校验
    if len(sorted_temp) < 3:
        raise ValueError(f"有效数据仅{len(sorted_temp)}个，无法进行雨流计数（需至少3个数据点）")

    return sorted_time, sorted_temp

def read_temperature_file(file,filename):
    """
    根据文件后缀自动选择读取方式，解析温度-时间数据
    输入：file_path（本地文件路径）
    """
    # 步骤1：获取文件后缀，判断文件类型
    print('file:',file)
    #file_name = file_path.file_name
    #file_ext = file_name.rsplit('.', 1)[1].lower()  # 提取后缀（小写）
    file_ext = filename.rsplit('.', 1)[1].lower()
    print('filename,file_ext:',filename,file_ext)

    if file_ext == 'csv':
        # 情况2：CSV文件 → 读取CSV数据，写入临时Excel，返回临时Sheet
        try:
            # 1. 用pandas读取CSV（处理编码、空行）
            # 读取文件内容并转换为字符串流
            from io import StringIO, BytesIO

            # 读取文件原始字节内容
            file_content = file.read()  # 不直接解码，先获取字节

            # 尝试多种编码格式
            encodings = ['utf-8', 'gbk', 'gb2312', 'ansi', 'latin-1']
            csv_data = None

            for encoding in encodings:
                try:
                    # 尝试用当前编码解码
                    content_str = file_content.decode(encoding)
                    csv_data = StringIO(content_str)
                    print(f"成功使用{encoding}编码解析文件")
                    break
                except UnicodeDecodeError:
                    continue

            if csv_data is None:
                raise RuntimeError("无法解析文件编码，请确认文件格式是否正确")

            # 用pandas读取CSV数据
            df = pd.read_csv(
                csv_data,
                encoding_errors='ignore',
                skip_blank_lines=True
            )
            print(f"成功读取CSV文件：{filename}，数据行数：{len(df)}")

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
        wb = openpyxl.load_workbook(file, data_only=True)
        sheet = wb.active
    else:
        print('Unknown File Type')
        sheet = []
    return sheet