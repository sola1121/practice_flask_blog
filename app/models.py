from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach

from . import db, login_manager
from .app.exceptions import ValidationError

import datetime
import hashlib


### 用户相关数据库 ###

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    defualt = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')   # 关联User

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return '<Role %r>' % self.name

    def add_permissions(self, perm):
        if not self.has_permissions(perm):
            self.permissions += perm

    def remove_permissions(self, perm):
        if self.has_permissions(perm):
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
    """用户权限值"""
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)   # 关注者的id
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)   # 被关注者的id
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))   # 关联Role中的主键
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(64), unique=True, index=True)
    confirmed = db.Column(db.Boolean, default=False)
    # 用户的一些额外的信息
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    # 头像hash缓存
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship("Post", backref="author", lazy="dynamic")   # 关联Post
    # 关注者, 都是只涉及User表, 属于自引用关系
    followed = db.relationship("Follow",    # 被当前账号关注的
                                foreign_keys=[Follow.follower_id],   # 指明对应Follow中的主键, 是关注者
                                backref=db.backref("follower", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")
    followers = db.relationship("Follow",    # 当前账号关注的
                                foreign_keys=[Follow.followed_id],   # 指明对应Follow中的主键, 是被关注者
                                backref=db.backref("followed", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")
    # 关联评论, 一对多
    comments = db.relationship("Comment", backref="author", lazy="dynamic")

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # 初始化角色
        if self.role is None:
            if self.email == current_app.config["FLASKY_ADMIN"]:
                self.role = Role.query.filter_by(name="Administrator").first()
            if self.role is None:
                self.role = Role.query.filter_by(defualt=True).first()
        # 初始化头像hash
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
        # 将自己设为自己的关注者
        self.follow(self)

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
    
    def ping(self):
        """每次登录更新时间, 将会注册到before_request钩子中, 使用current_user来进行检查"""
        self.last_seen = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode("U8")).hexdigest()

    def gravatar(self, size=100, default="identicon", rating="g"):
        """使用gravatar.com提供的服务, 以便在模板中直接使用生成img链接
        s图像尺寸 
        r图像级别 
        d尚未注册的用户使用的默认图像生成方式
        fd强制使用默认头像"""
        url = "https://secure.gravatar.com/avatar"
        md5_str = self.gravatar_hash()
        return "{url}/{md5_str}?s={size}&d={default}&r={rating}".format(
                url=url, md5_str=md5_str, size=size, default=default, rating=rating)

    # 用户关注相关
    def follow(self, user):
        """关注某个用户"""
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)  # 自己设为关注者, 指定用户设为被关注者
            db.session.add(f)
    
    def unfollow(self, user):
        """取消关注某个用户"""
        f = self.followed.filter_by(followed_id=user.id).first()   # 当前用户关注的用户中查找指定用户
        if f:
            db.session.delete(f)
    
    def is_following(self, user):
        """当前用户是否在关注某个用户"""
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None
    
    def is_followed_by(self, user):
        """当前用户是否被某个用户关注"""
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id).first() is not None

    @property
    def followed_posts(self):
        # select * from Post 
        # join Follow on Follow.followed_id=Post.author_id 
        # join User on User.id = Follow.follower_id
        # where User.id = ;
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)
    
    @staticmethod
    def add_self_follows():
        """更新还未关注自己的用户"""
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()
    
    def generate_auth_token(self, expiration):
        """生成用于API的令牌, 使用用户的id"""
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"user's id token": self.id}).decode("U8")

    @staticmethod
    def verify_auth_token(token):
        """用于API的令牌验证, 通过解码的id获取到用户对象"""
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data["user's id token"])

    def to_json(self):
        json_user = {
            "url": url_for("api.get_user", id=self.id),
            "username": self.username,
            "member_since": self.member_since,
            "last_seen": self.last_seen,
            "posts_url": url_for("api.get_user_posts", id=self.id),
            "followd_posts_url": url_for("api.get_user_followed_posts", id=self.id),
            "post_count": self.posts.count()
        }
        return json_user


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


### 博客文章相关数据库 ###

class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))   # 关联User中的主键
    # 关联评论, 一对多
    comments = db.relationship("Comment", backref="post", lazy="dynamic")
    
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ["a", "abbr", "acronym", "b", "blockquote", "code", "em", "i", "li",
                        "ol", "pre", "strong", "ul", "h1", "h2", "h3", "p"]
        target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format="html"), tags=allowed_tags, strip=True))
    
    def to_json(self):
        json_post = {
            "url": url_for("api.get_post", id=self.id),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author_url": url_for("api.get_user", id=self.author_id),
            "comments_url": url_for("api.get_post_comments", id=self.id),
            "comment_count": self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get("body")
        if body is None or body =="":
            raise ValidationError("post does not have a body")   # 无body内容抛出自定义的一个错误, 这个错误在蓝本errorhandler中注册了, 会自动捕获
        return Post(body=body)


db.event.listen(Post.body, "set", Post.on_changed_body)   # 监听发生在Post.body上的set事件, 并使用指定的函数再处理


### 评论相关数据库 ###

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))   # User表中id的外键
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))   # Post表中id的外键

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ["a", "abbr", "acronym", "b", "code", "em", "i"]
        target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format="html"), 
                                                       tags=allowed_tags, 
                                                       strip=True)
                                                       )
    
    def to_josn(self):
        json_comment = {
            "url": url_for("api.get_comment", id=self.id),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author_url": url_for("api.get_user", id=self.author_id),
            "post_url": url_for("api.get_post", id=self.post_id)
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get("body")
        if body is None or body == "":
            raise ValidationError("comment does not have a body")   # 无body内容抛出自定义的一个错误, 这个错误在蓝本errorhandler中注册了, 会自动捕获
        return Comment(body=body)


db.event.listen(Comment.body, "set", Comment.on_changed_body)
