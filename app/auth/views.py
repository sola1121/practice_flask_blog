from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from .. import db
from . import auth
from .forms import LoginForm, RegistrationForm
from ..models import User
from ..email import send_email

@auth.route("/login", methods=["GET", "POST"])
def login():
    """用户登录"""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            jump_to = request.args.get("next")
            if jump_to is None or not jump_to.startwith("/"):
                jump_to = url_for("main.index")
            return redirect(jump_to)
        flash("Invalid username or password.")
    return render_template("auth/login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("main.index"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    """用户注册"""
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(email=form.email.data, username=form.username.data, password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        token = new_user.generate_confirmation_token()
        send_email(new_user.email, "账户邮箱确认", "auth/email/confirm_new_user", new_user=new_user, token=token)
        flash("A confirmation email has been sent to you by email.")
        return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@auth.route("/confirm/<token>", endpoint="confirm")
@login_required
def confirm_account(token):
    """用户账户确认"""
    if current_user.confirmed:
        return redirect(url_for("main.index"))
    if current_user.confirm(token):
        db.session.commit()
        flash("You have confirmed your account.")
    else:
        flash("The confirmation link is invalid or has expired.")
    return redirect(url_for("main.index"))


@auth.before_app_request
def before_request():
    """在发起请求前检查
    用户已登录, 用户未确认邮箱, 请求的URL不在身份蓝本中, 不是对静态文件的请求.
    """
    if current_user.is_authenticated and not current_user.confirmed and \
        request.blueprint != "auth" and request.endpoint != "static":
        return redirect(url_for("auth.unconfirmed"))


@auth.route("/unconfirmed")
def unconfirmed():
    """用户没有通过请求检查将会跳转的页面"""
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for("main.index"))
    return render_template("auth/unconfirmed.html")


@auth.route("/confirm")
@login_required
def resend_confirmation():
    """重新在向用户邮箱中发送验证"""
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, "账户邮箱确认", "auth/email/confirm_new_user", new_user=current_user, token=token)
    flash("A new confirmation email has been sent to you by email.")
    return redirect(url_for("main.index"))
