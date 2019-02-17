from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, ValidationError
from flask_pagedown.fields import PageDownField

from ..models import Role, User


### 用户相关表单 ###

class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    name = StringField("真实姓名", validators=[Length(0, 64)])
    location = StringField("居住地", validators=[Length(0, 64)])
    about_me = TextAreaField("个人简介")
    submit = SubmitField("修改保存")


class EditProfileAdminForm(FlaskForm):
    # 账户信息
    email = StringField("邮箱", validators=[DataRequired(), Length(4, 64), Email()])
    username = StringField("用户名", validators=[DataRequired(), 
                            Length(4, 64),
                            Regexp(r"^[A-Za-z0-9][A-Za-z0-9_]*$", flags=0, message="Username must have only letters, numbers or underscores.")])
    confirmed = BooleanField("是否验证")
    role = SelectField("用户角色", coerce=int)   # label=None, validators=None, coerce=text_type, choices=None, **kwargs
    # 使用者信息
    name = StringField("真实姓名", validators=[Length(0, 64)])
    location = StringField("居住地", validators=[Length(0, 64)])
    about_me = TextAreaField("个人简介")
    submit = SubmitField("修改保存")

    def __init__(self, user, *args, **kwargs):
        """为SelectField提供选项, 保存原始的user在表单对象中"""
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError("Email already registered.")

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already in use.")


### 博客相关表单 ###

class PostForm(FlaskForm):
    body = PageDownField("现在的想法", validators=[DataRequired()])
    submit = SubmitField("确认发布")


### 评论相关表单 ###

class CommentForm(FlaskForm):
    body = StringField("", validators=[DataRequired()])
    submit = SubmitField("发表评论")
