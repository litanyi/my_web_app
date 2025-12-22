# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, session
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
import os
import numpy as np
from collections import defaultdict
from tool import *

# Flask应用初始化（不变）
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'csv', 'txt'}
app.config['SECRET_KEY'] = 'temp_rainflow_damage_key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制文件大小16MB
app.config['SECRET_KEY'] = 'temp_rainflow_damage_key'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 添加测试函数
def test_function():
    print("This is a test function.")   
    return "Test function executed."

# 文件类型校验
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ----------------------
# 关键修改：首页路由（传递使用次数倍数到前端）
# ----------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    result_data = {
        "step": 1,  # 新增：1=上传文件步骤，2=选择数据步骤
        "has_result": False,
        "time_range": None,
        "temp_range": None,
        "rainflow": None,
        "total_damage": None,
        "damage_details": None,
        "usage_multiple": None,  # 新增：使用次数倍数
        "show_preview": False,  # 新增预览标记
        "preview_data": None,   # 前5行数据
        "columns": None,        # 列名
        "file_path": None       # 临时文件路径
    }

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('错误：请求中未包含文件数据')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('错误：未选择任何文件')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash(f'错误：不支持该文件类型！仅允许上传 .txt / .xlsx / .csv 格式的Excel文件')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            #print(f"file:{file},file.filename:{file.filename}")
            try:
                # 保存文件到临时目录
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                print(f"temp_path:{temp_path}")
                file.save(temp_path)
                # 读取文件前5行和列名
                sheet = read_temperature_file_PC(temp_path)
                columns = [cell.value for cell in sheet[1]]  # 假设第一行为表头
                preview_data = []
                for row in sheet.iter_rows(min_row=2, max_row=6, values_only=True):  # 前5行数据
                    preview_data.append(row)
                
                # 更新结果数据
                result_data["show_preview"] = True
                result_data["preview_data"] = preview_data
                result_data["columns"] = columns
                result_data["file_path"] = temp_path

                # 存储到会话中用于传递到列选择路由函数select_columns
                session['result_data'] = result_data 
            except InvalidFileException:
                flash('错误：无效的Excel文件（可能是文件损坏或版本不兼容）')
            except ValueError as ve:
                flash(f'数据处理错误：{str(ve)}')
            except Exception as e:
                flash(f'系统错误：{str(e)}（请检查文件格式是否正确）')
            finally:
                flash(f'上传文件成功！')
                # 更新步骤为2
                result_data["step"] = 2

    return render_template('index.html', title='温度循环雨流计数与损伤度计算', result=result_data)

@app.route('/select_columns', methods=['POST'])
def select_columns():
    # 从会话获取result_data
    result_data = session.get('result_data', {
        "has_result": False,
        "time_range": None,
        "temp_range": None,
        "rainflow": None,
        "total_damage": None,
        "damage_details": None,
        "usage_multiple": None,
        "show_preview": False,
        "preview_data": None,
        "columns": None,
        "file_path": None
    })
    file_path = request.form['file_path']
    time_col = request.form['time_col']
    temp_col = request.form['temp_col']
    
    # 读取选定列数据
    sheet = read_temperature_file_PC(file_path)
    columns = [cell.value for cell in sheet[1]]
    time_idx = columns.index(time_col)
    temp_idx = columns.index(temp_col)
    
    # 解析选定列的数据
    time_data = []
    temp_data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[time_idx]:
            # 转换为浮点数并添加到列表，修复txt文件读取的bug
            time_data.append(float(row[time_idx]))
        if row[temp_idx]:
            temp_data.append(float(row[temp_idx]))
    
    # 直接使用解析后的time_data和temp_data进行后续处理
    try:
        # 数据范围
        time_min = round(min(time_data), 2)
        time_max = round(max(time_data), 2)
        temp_min = round(min(temp_data), 2)
        temp_max = round(max(temp_data), 2)
        result_data["time_range"] = f"{time_min} ~ {time_max}"
        result_data["temp_range"] = f"{temp_min} ~ {temp_max}"

        # 雨流计数
        rainflow_results = rainflow_counting(temp_data,plot_flag=True)
        sorted_rainflow = sorted(rainflow_results.items(), key=lambda x: x[0])
        result_data["rainflow"] = sorted_rainflow
        flash(f'雨流计数完成：检测到 {len(sorted_rainflow)} 种温度循环幅值')

        # 损伤度计算
        total_damage, damage_details, usage_multiple = calculate_damage(rainflow_results)
        result_data["total_damage"] = total_damage
        result_data["damage_details"] = damage_details
        result_data["usage_multiple"] = usage_multiple
        result_data["has_result"] = True

        # 损伤状态提示
        if total_damage >= 1.0:
            flash(f'⚠️  总损伤度 {total_damage}（≥1.0）：材料已达到疲劳失效阈值！')
            flash(f'   剩余使用倍数（1/损伤度）：{usage_multiple}（表示仅能承受当前损伤量的{usage_multiple}倍，已失效）')
        else:
            flash(f'✅  总损伤度 {total_damage}（<1.0）：材料当前处于安全状态')
            flash(f'   剩余使用倍数（1/损伤度）：{usage_multiple}（表示还能承受当前温度循环模式的{usage_multiple}倍）')

    except Exception as e:
        flash(f'数据处理错误：{str(e)}')
    
    # 处理完成后更新会话
    session['result_data'] = result_data
    flash(f'寿命计算任务完成，欢迎再次使用本系统！')
    return render_template('index.html', title='温度循环雨流计数与损伤度计算', result=result_data)

# 关于页面（不变）
@app.route('/about')
def about():
    return render_template('about.html', title='关于本系统')

# 关于页面（不变）
@app.route('/predict_temperature')
def predict_temperature():
    #加载外部链接
    return redirect('http://localhost/custom/testEV3ph-2-level-DC-AC-inverter.html')

if __name__ == '__main__':
    app.config['DEBUG'] = True
    app.run(host='127.0.0.1', port=5001)