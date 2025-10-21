# -*- coding: utf-8 -*-
# app.py
from flask import Flask, render_template
from flask_ngrok import run_with_ngrok

app = Flask(__name__)
run_with_ngrok(app)

# 首页路由
@app.route('/')
def index():
    # 可以传递数据到模板
    data = {
        'title': 'My Flask Website',
        'message': 'Flask'
    }
    return render_template('index.html', **data)

# 在app.py中添加
@app.route('/about')
def about():
    return render_template('about.html', title='About Us')

if __name__ == '__main__':
    # 去掉debug参数，或者通过app.config设置
    app.config['DEBUG'] = False  # 这样设置调试模式
    app.run()  # 这里不要加debug=True
    #app.run(debug=True)