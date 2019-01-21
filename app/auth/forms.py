from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError

from ..models import User


class LoginForm(FlaskForm):
    email = StringField("邮箱地址", validators=(DataRequired(), Length(4, 64), Email()))
    password = PasswordField("密码", validators=(DataRequired(),))
    remember_me = BooleanField("记住我")
    submit = SubmitField("确认")


class RegistrationForm(FlaskForm):
    email = StringField("邮箱地址", validators=(DataRequired(), Length(4, 64), Email()))
    username = StringField("新建用户名", validators=(DataRequired(), 
                                                   Length(4, 64), 
                                                   Regexp(r"^[a-zA-z][a-zA-Z0-9_]*$", flags=0, message="Username must have only letters, numberes or underscores")))
    password = PasswordField("新建密码", validators=(DataRequired(),
                                                    EqualTo("password2", message="Passwords must match.")))
    password2 = PasswordField("确认密码", validators=(DataRequired(),))
    submit = SubmitField("确认创建")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Email already registered.")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already in use.")


class ChangePasswordForm(FlaskForm):
    old_pass = PasswordField("旧密码", validators=[DataRequired()])
    new_pass = PasswordField("新密码", validators=[DataRequired(), 
                                                  Length(3, 24),
                                                  EqualTo("new_pass2", message="New passwords must match.")])
    new_pass2 = PasswordField("确认新密码", validators=[DataRequired(), Length(3, 24)])
    submit = SubmitField("确认修改")


class EmailForm(FlaskForm):
    email = StringField("注册邮箱", validators=[DataRequired(), Length(4, 64), Email()])
    submit = SubmitField("确认邮箱")


class ResetPasswordForm(FlaskForm):
    new_pass = PasswordField("新密码", validators=[DataRequired(),
                                                  Length(3, 24),
                                                  EqualTo("new_pass2", message="New passwords must match.")])
    new_pass2 = PasswordField("确认新密码", validators=[DataRequired(), Length(3, 24)])
    submit = SubmitField("确认修改")


class ChangeEmailForm(FlaskForm):
    new_email = StringField("新邮箱地址", validators=[DataRequired(), Length(4, 64), Email()])
    submit = SubmitField("确认修改")
