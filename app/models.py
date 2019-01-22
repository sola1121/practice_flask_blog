from flask import current_app
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from . import db, login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    defualt = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return '<Role %r>' % self.name

    def add_permissions(self, perm):
        if not self.has_permisson(perm):
            self.permissions += perm

    def remove_permissions(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm
        
    def reset_permissions(self):
        self.permissions = 0

    def has_permissions(self, perm):
        return self.permissions & perm == perm   # 使用按位与, 很巧妙的就可以检查相加中的加数

    @staticmethod
    def insert_roles():
        """在数据库中创建roles缺少的角色"""
        roles = {
            "User": (Permission.FOLLOW, Permission.COMMIT, Permission.WRITE),   # 用户
            "Moderator": (Permission.FOLLOW, Permission.COMMIT, Permission.WRITE, 
                          Permission.MODERATE),   # 协管员
            "Administrator": (Permission.FOLLOW, Permission.COMMIT, Permission.WRITE, 
                              Permission.MODERATE, Permission.ADMIN),   # 管理员
        }
        defualt_role = "User"
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                new_role = Role(name=r)
            new_role.reset_permissions()
            for perm in roles[r]:
                new_role.add_permissions(perm)
            new_role.defualt = (new_role.name == defualt_role)
            db.session.add(new_role)
        db.session.commit()


class Permission:
    FOLLOW = 1
    COMMIT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(64), unique=True, index=True)
    confirmed = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config["FLASKY_ADMIN"]:
                self.role = Role.query.filter_by(name="Administrator").first()
            if self.role is None:
                self.role = Role.query.filter_by(defualt=True).first()

    def __repr__(self):
        return '<User %r>' % self.username

    @property
    def password(self):
        """密码属性"""
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        """确认用户注册邮箱, 生成用户令牌"""
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"confirm a new user": self.id}).decode("U8")

    def confirm(self, token):
        """确认用户注册邮箱, 接收验证令牌"""
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            confirm_data = s.loads(token.encode("U8"))
        except:
            return False
        if confirm_data.get("confirm a new user") != self.id:
            return False
        self.confirmed = True
        db.session.add(self)   # 这里没有提交, 要到之后确认后才做提交.
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permissions(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser   # 重新将匿名用户指向, 这是一个flask_login.AnonymousUser的子类, 增加了权限的判断方法


@login_manager.user_loader
def load_user(user_id):
    """flask_login扩展需要从数据库中获取指定标识符对应的用户时将会调用"""
    return User.query.get(int(user_id))
