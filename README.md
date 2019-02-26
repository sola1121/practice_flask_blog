# practice_flask_blog

## 多文件目录组织结构

    |-practice_flask_blog  
        |-app/  
            |-templates/  
            |-static/  
            |-main/  
                |-__init__.py  
                |-errors.py  
                |-forms.py  
                |-views.py  
            |-__init__.py  
            |-email.py  
            |-models.py  
        |-migrations/  
        |-tests/  
            |-__init__.py  
            |-test*.py  
        |-venv/  
        |-requirements.txt  
        |-config.py  
        |-practice_flask_blog.py  

app, migrations, tests, venv都是次级目录, app实现主要的功能, MVC设计的所有的东西都在里面; migrations是使用flask-migrate生成的迁移文件目录; tests测试单元; venv是虚拟环境. 同级的文件还有config.py和practice_flask_blog.py, 这一个是配置, 一个是启动的接口.

模板, 静态文件都保存在app中, 为app/templates, app/static

在app/main中保存的主Controler, 包含主视图views, 表单forms, 自定错误errors. 如果有别的应用, 也可以在这儿添加.

在app中包含模板Models, email插件的外加功能也在app目录中.

**目的**

+ 在单个文件中, 应用在全局作用域中创建, 无法动态的修改配置. 这一点对单元测试尤其重要, 因为有时为了提高测试覆盖度, 必须在不同的配置下运行应用.

+ 所以, 这里应该考虑延迟创建应用实例, 把创建过程移动到可显式调用的工厂函数中. 这种方法不仅可以给脚本留出配置应用的时间, 还能够创建多个应用实例, 为测试提供便利.

## 运行流程

通过practice_flask_blog进入运行

    # practice_flask_blog.py
    import os
    from flask_migrate import Migrate   # 用于迁移
    from app import create_app, db   # 导入创建应用, app/__init__.py中
    from app.models import User, Role   # 导入数据库

    app = create_app(os.getenv('FLASK_CONFIG') or 'default')   # 生成app用以运行
    migrate = Migrate(app, db)   # 注册迁移适用的应用和数据库对象

    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db, User=User, Role=Role)

主要的运行还是在create_app函数中, 该函数在app/\_\_init__.py文件中, 其导入了所有的要使用到的插件, 生成,配置app并将插件用于了初始化app, 在这之后的将会注册到应用中的子应用所使用的插件对象都可以在此导入, 最后将事先写好的蓝本注册到app中, 返回app, 此时的app就是已经完成了所有功能的app了. 蓝本是在app/main/\_\_init__.py中定义的, 使用蓝本定义了Controler的所有功能, 即视图应该做什么.  
`app.register_blueprint`的*url_prefix*参数, 可以指定该蓝本下的所有附属视图路由的前面都多一个链接前缀

    # app/__init__.py, 即导入app包就可以导入
    from flask import Flask
    from flask_bootstrap import Bootstrap
    from flask_mail import Mail
    from flask_moment import Moment
    from flask_sqlalchemy import SQLAlchemy
    from config import config

    # 事先实例化的插件们
    bootstrap = Bootstrap()
    mail = Mail()
    moment = Moment()
    db = SQLAlchemy()

    # 工厂函数
    def create_app(config_name:"应用使用的配置名"):
        # 生成app
        app = Flask(__name__)
        # 导入配置, 并作为app设置
        app.config.from_object(config[config_name])
        config[config_name].init_app(app)

        # 使用插件进行初始化app
        bootstrap.init_app(app)
        mail.init_app(app)
        moment.init_app(app)
        db.init_app(app)

        # 注册蓝本
        from .main import main as main_blueprint
        app.register_blueprint(main_blueprint)

        return app

在app/main/\_\_init__.py中使用的蓝本

    # app/main/__init__.py, 即main包
    from flask import Blueprint

    main = Blueprint('main', __name__)   # main蓝本对象, 主要将会在views和errors中当成app使用, 提前注册功能

    from . import views, errors   # 防止重复导入, 放在后面. 导入这两个模块, 才能在这对应的模块使用蓝本.

#### 运行流程

1. practice_flask_blog.py应用实例  
2. app/包(\_\_init__.py), create_app函数, 会生成完整的app应用  
    2.1 会去调用蓝本, 蓝本是在app/main/包(\_\_init__.py)中创建

> practice_flask_blog.py --> app/\_\_init__.py --> app/main/\_\_init__.py

#### 使用蓝本

+ 使用工厂函数的操作让定义路由变复杂了. 在单脚本应用中, 应用实例存在于全局作用域中 路由可以直接使用app.route装饰器定义. 此时应用在运行时创建, 只有调用create_app之后才能使用app.route装饰器, 这时定义路由就太晚了.
+ 自定义的错误处理程序页面临同样的问题, 因为错误页面处理程序使用app.errorhandler装饰器定义.
+ 蓝本和应用类似, 也可以定义路由和错误处理程序. 不同的是在蓝本中定义的路由和错误处理程序处于休眠状态, 直到蓝本注册到应用上之后, 他们才真正成为应用的一部分. 使用位于全局作用域中的蓝本时, 定义路由和错误处理程序的方法几乎与单脚本应用一样.

## 详细笔记

### 开发阶段

[用户身份验证](./01用户身份验证.md)

[用户角色](./02用户角色.md)

[用户资料](./03用户资料.md)

[博客文章](./04博客文章.md)

[关注者](./05关注者.md)

[用户评论](./06用户评论.md)

[应用编程接口](./07应用编程接口.md)

### 测试阶段

[测试](./08测试.md)
