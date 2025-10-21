# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
import os
import numpy as np
from collections import defaultdict
from tool import *

# Flask应用初始化（不变）
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'csv'}
app.config['SECRET_KEY'] = 'temp_rainflow_damage_key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制文件大小16MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
        "has_result": False,
        "time_range": None,
        "temp_range": None,
        "rainflow": None,
        "total_damage": None,
        "damage_details": None,
        "usage_multiple": None  # 新增：使用次数倍数
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
            flash(f'错误：不支持该文件类型！仅允许上传 .xlsx 或 .csv 格式的Excel文件')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            try:
                #wb = openpyxl.load_workbook(file, data_only=True)
                #sheet = wb.active

                sheet = read_temperature_file(file,file.filename)

                flash(f'成功读取文件：{file.filename}（工作表：{sheet.title}）')

                # 解析数据
                sorted_time, sorted_temp = parse_temperature_data(sheet)
                flash(f'成功解析 {len(sorted_temp)} 个有效温度-时间数据点')

                # 数据范围
                time_min = round(min(sorted_time), 2)
                time_max = round(max(sorted_time), 2)
                temp_min = round(min(sorted_temp), 2)
                temp_max = round(max(sorted_temp), 2)
                result_data["time_range"] = f"{time_min} ~ {time_max}"
                result_data["temp_range"] = f"{temp_min} ~ {temp_max} ℃"

                # 雨流计数
                rainflow_results = rainflow_counting(sorted_temp)
                sorted_rainflow = sorted(rainflow_results.items(), key=lambda x: x[0])
                result_data["rainflow"] = sorted_rainflow
                flash(f'雨流计数完成：检测到 {len(sorted_rainflow)} 种温度循环幅值')

                # 损伤度计算（新增接收usage_multiple）
                total_damage, damage_details, usage_multiple = calculate_damage(rainflow_results)
                usage_multiple = int(usage_multiple)  # 使用次数变量值取整数
                result_data["total_damage"] = total_damage
                result_data["damage_details"] = damage_details
                result_data["usage_multiple"] = usage_multiple  # 传递到前端
                result_data["has_result"] = True

                # 损伤状态提示（新增使用次数倍数说明）
                if total_damage >= 1.0:
                    flash(f'⚠️  总损伤度 {total_damage}（≥1.0）：材料已达到疲劳失效阈值！')
                    flash(f'   1/损伤度（剩余使用倍数）：{usage_multiple}（表示仅能承受当前损伤量的{usage_multiple}倍，已失效）')
                else:
                    flash(f'✅  总损伤度 {total_damage}（<1.0）：材料当前处于安全状态')
                    flash(f'   1/损伤度（预估使用倍数）：{usage_multiple}（表示还能承受当前温度循环模式的{usage_multiple}倍）')

            except InvalidFileException:
                flash('错误：无效的Excel文件（可能是文件损坏或版本不兼容）')
            except ValueError as ve:
                flash(f'数据处理错误：{str(ve)}')
            except Exception as e:
                flash(f'系统错误：{str(e)}（请检查文件格式是否正确）')
            finally:
                flash(f'寿命计算任务完成，欢迎再次使用本系统！')

    return render_template('index.html', title='温度循环雨流计数与损伤度计算', result=result_data)


# 关于页面（不变）
@app.route('/about')
def about():
    return render_template('about.html', title='关于本系统')


if __name__ == '__main__':
    app.config['DEBUG'] = True
    app.run(host='127.0.0.1', port=5000)