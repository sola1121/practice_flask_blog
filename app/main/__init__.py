from flask import Blueprint

main = Blueprint('main', __name__)   # 第一个参数是他的名称空间名, 第二个是蓝本所在的包或模块

# 在此导入需要使用蓝本的模块, 这样就能与蓝本建立联系. 
# 因为需要使用蓝本的模块之后肯定也会导入蓝本, 为了防止循环导入, 这里将导入放在蓝本变量的后面.
from . import views, errors 
