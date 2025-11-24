import sys
path = '/home/litanyi/test'  # 替换为你的项目路径
if path not in sys.path:
    sys.path.append(path)
 
from app import app as application