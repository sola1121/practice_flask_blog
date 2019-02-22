from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_pagedown import PageDown

from config import CONFIG

# 创建插件对象
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
pagedown = PageDown()


def create_app(config_name):
    # 生成应用
    app = Flask(__name__)
    # 配置应用
    app.config.from_object(CONFIG[config_name])
    CONFIG[config_name].init_app(app)

    # 向应用中初始化插件
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    # 向应用中注册蓝本
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix="/auth")   # 所有该蓝本下的路由将会加上auth的前缀

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix="/api/ver1")

    return app
