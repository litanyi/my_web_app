# -*- coding: utf-8 -*-
import numpy as np
from collections import defaultdict
import csv
from flask import Flask, render_template, request, redirect, url_for, flash
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl import Workbook, load_workbook
import os
# 用于图形化文件选择框（PC本地选择）
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from openpyxl.utils.dataframe import dataframe_to_rows
from io import StringIO
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["SimHei"]  # 配置中文字体
#提纯峰谷点
def turning_points_extraction(temperature_data):
    # 转换为numpy数组（便于后续计算，兼容原列表输入）
    temp_data = np.array(temperature_data, dtype=float)
    # 初始化极值点列表（默认保留首尾点）
    turning_points = [temp_data[0]]
    m1 = len(temp_data)

    # Mark intermediate points using the MATLAB approach
    Load1 = temp_data.copy()
    Load2 = temp_data.copy()

    #remove the same value points
    # remove consecutive equal points (keep first of a run, remove subsequent equal neighbors)
    if m1 > 1:
        B = Load1.copy()
        for i in range(1, m1):
            if B[i] == B[i-1]:
                B[i] = np.nan
        B = B[~np.isnan(B)]
        Load1 = B.copy()
        Load2 = B.copy()
        m1 = len(Load1)

    # Apply peak-valley purification
    for i in range(1, m1-1):  # Adjusted for 0-based indexing
        if Load2[i-1] < Load2[i] and Load2[i] < Load2[i+1]:
            Load1[i] = np.nan
        elif Load2[i-1] > Load2[i] and Load2[i] > Load2[i+1]:
            Load1[i] = np.nan

    # Remove NaN values to keep only peaks and valleys
    Load1 = Load1[~np.isnan(Load1)]

    # Convert back to list for compatibility with rest of code
    turning_points = Load1.tolist()
        # Ensure last point is included if not already present
    if turning_points and turning_points[-1] != temp_data[-1]:
        turning_points.append(temp_data[-1])

    return turning_points

def save_to_mat(Load1,output_file): 
    try:
        mat_data = {'Load1': Load1}
        mat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file+'.mat')
        sio.savemat(mat_path, mat_data)
        print(f"Saved MATLAB .mat: {mat_path}")
    except Exception:
        txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file+'.txt')
        np.savetxt(txt_path, Load1, fmt='%.6f')
        print(f"scipy not available or save failed; saved ASCII: {txt_path}")
    return 0
# 雨流计数法
def rainflow_counting(temperature_data, plot_flag=False, csv_filename=None):
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
    save_to_mat(temperature_data,'raw_points')
    # ----------------------
    # 步骤2：第一次峰谷提纯（对应三点法步骤一）
    # 目的：移除非极值点，保留纯峰谷交替序列
    # ----------------------
    turning_points = turning_points_extraction(temperature_data)
    save_to_mat(turning_points,'turning_points')

    # ----------------------
    # 步骤3：序列拼接优化（对应MATLAB三点法步骤二）
    # 目的：从最值（绝对值最大的峰/谷）拆分拼接，确保首尾均为极值
    # ----------------------
    # 找到绝对值最大的极值点（优先用最大绝对值，而非单纯最大值，更符合MATLAB思路）
    #abs_turning = np.abs(turning_points)
    max_abs_idx = np.argmax(turning_points)  # 最大点的索引
    mi = np.min(turning_points)
    if max_abs_idx==1:
        mi=np.min(turning_points)
    else:
        mi=turning_points[max_abs_idx-1]
    # 拆分序列：从最值点拆分为前后两段，再拼接（前半段+后半段）
    B1 = turning_points[max_abs_idx:]  # 最值点到序列末尾
    B2 = turning_points[:max_abs_idx + 1]  # 序列开头到最值点（包含最值点）
    optimized_points = B1 + B2  # 新序列：从最值开始，到最值结束
    save_to_mat(optimized_points,'optimized_points')
    # ----------------------
    # 步骤4：第二次峰谷提纯（对应MATLAB三点法步骤三）
    # 目的：消除拼接处可能产生的非极值点，确保序列纯峰谷交替
    # ----------------------
    final_turning = turning_points_extraction(optimized_points)
    # 将当前的final_turning保存为 MATLAB 可读取的 .mat 文件（若无 scipy 则降级为 ASCII .txt）
    save_to_mat(final_turning,'final_turning')
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
        if n1 == 1:
            break
        if  n1 == 2 and Load1[0]==Load1[1]:
            Amplitude.append(Load1(0)-mi)  # 存入幅值（取标量避免维度问题）
            Mean.append((Load1(0)+mi)/2)       # 存入均值
            break
        # 遍历查找可计数的循环
        for j in range(n1 - 2):  # Python索引从0开始，对应MATLAB j=1:n1-2
            # 计算相邻两点的幅值（对应MATLAB s1、s2）
            s1 = abs(Load1[j+1] - Load1[j])
            s2 = abs(Load1[j+1] - Load1[j+2])
            # 计算均值（对应MATLAB e3）
            e3 = (Load1[j] + Load1[j+1]) / 2
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
        # ----------------------
    # 新增功能：生成CSV文件（幅值和均值）
    # ----------------------
    # 切换到脚本所在目录，这样生成的CSV文件会保存在脚本所在目录下
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    if csv_filename:
        try:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['幅值', '均值'])  # 写入表头
                for amp, mean in zip(Amplitude, Mean):
                    writer.writerow([round(amp, 6), round(mean, 6)])
            print(f"雨流计数结果已保存至 {csv_filename}")
        except Exception as e:
            print(f"保存CSV文件时出错: {e}")

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

        temp_data = np.array(temperature_data, dtype=float)
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
        """
        print("幅值(℃) -> 循环次数:")
        
        for amp, cnt in sorted(final_results.items()):
            print(f"{amp} ℃ : {cnt} 次")
        """

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

# 温度-时间数据解析（选择列）
def parse_selected_columns(sheet, time_idx, temp_idx):
    """解析用户选择的时间列和温度列"""
    time_data = []
    temp_data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):  # 从第二行开始读取数据
        try:
            time_val = float(row[time_idx]) if row[time_idx] is not None else None
            temp_val = float(row[temp_idx]) if row[temp_idx] is not None else None
            if time_val:
                time_data.append(time_val)
            if temp_val:
                temp_data.append(temp_val)
        except (ValueError, TypeError):
            continue  # 跳过无效数据
    
    # 按时间排序
    combined = sorted(zip(time_data, temp_data), key=lambda x: x[0])
    return [x[0] for x in combined], [x[1] for x in combined]

# 温度-时间数据解析（固定列）
def parse_temperature_data(sheet):
    time_data = []
    temp_data = []

    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=2, values_only=True):
        time_val, temp_val = row
        # 时间格式处理
        try:
            if isinstance(time_val, (int, float)):
                time_data.append(float(time_val))
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

    sorted_time = time_data
    sorted_temp = temp_data

    # 数据量校验
    if len(sorted_temp) < 3:
        raise ValueError(f"有效数据仅{len(sorted_temp)}个，无法进行雨流计数（需至少3个数据点）")

    return sorted_time, sorted_temp

#读本地文件
def read_temperature_file_PC(file_path):
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
    # -------------------------- TXT处理分支 --------------------------
    elif file_ext == 'txt':
        try:
            # 读取TXT：自动识别分隔符（空格/制表符/逗号），兼容多编码
            # 核心修正：移除errors参数，改用open()处理编码错误
            # 先通过open()读取文件（处理编码错误），再传给pd.read_csv
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 读取所有行并过滤空行（替代skip_blank_lines）
                lines = [line.strip() for line in f if line.strip()]
            
            # 用StringIO模拟文件对象，传给pd.read_csv解析
            from io import StringIO
            df = pd.read_csv(
                StringIO('\n'.join(lines)),  # 将过滤后的行转为内存文件
                sep=r'\s+|,|;',             # 分隔符：空格/制表符/逗号/分号
                engine='python',            # 启用python引擎支持正则分隔符
                header=None,                # TXT默认无表头
                dtype=str,
                on_bad_lines='skip'         # 跳过解析失败的行
            )
            # 可选：如果TXT有固定表头，可手动设置列名
            # df.columns = ['时间', '温度', '备注']  # 根据实际场景调整
            print(f"成功读取TXT文件：{os.path.basename(file_path)}，数据行数：{len(df)}，列数：{len(df.columns)}")
            # 创建内存临时Excel工作簿
            wb_temp = Workbook()
            sheet_temp = wb_temp.active
            sheet_temp.title = "TXT_Data"

            # 将DataFrame写入临时Sheet（无表头则index=False, header=False）
            header_mode = False if df.columns.tolist() == [0,1,2,...][:len(df.columns)] else True
            for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=header_mode), 1):
                for c_idx, value in enumerate(row, 1):
                    sheet_temp.cell(row=r_idx, column=c_idx, value=value)
            sheet = sheet_temp

        except Exception as e:
            raise RuntimeError(f"TXT文件处理失败：{str(e)}")
    else:
        print('Unknown File Type')
        sheet = []
    return sheet

#读网页文件
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