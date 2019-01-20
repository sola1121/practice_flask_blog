from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from . import db, login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(64), unique=True, index=True)
    confirmed = db.Column(db.Boolean, default=False)

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


@login_manager.user_loader
def load_user(user_id):
    """flask_login扩展需要从数据库中获取指定标识符对应的用户时将会调用"""
    return User.query.get(int(user_id))
