from flask import current_app, render_template, redirect, abort, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.contrib.cache import SimpleCache
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from .. import db
from . import auth
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, EmailForm, ResetPasswordForm, ChangeEmailForm
from ..models import User
from ..email import send_email

CACHE = SimpleCache()

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
    """对用户的每次请求都进行提前的检查
    用户已登录, 将更新登录时间), 执行之后检查
    用户未确认邮箱, 并且请求的URL不在auth蓝本中, 也不是对静态文件的请求, 将会重定向到要求确认邮箱的界面
    """
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed and \
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


@auth.route("/change_pass", endpoint="change_pass", methods=["GET", "POST"])
@login_required
def change_pass():
    """更改密码"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.verify_password(form.old_pass.data):
            flash("Password is not match the old one.")
            return redirect("auth.change_pass")
        current_user.password = form.new_pass.data
        db.session.add(current_user)
        db.session.commit()
        logout_user()
        flash("Password changed, login again.")
        return redirect(url_for("auth.login"))
    return render_template("auth/password_change.html", form=form)


def generate_reset_token(confirm_data, expiration=1800):
    """重置, 生成用户令牌"""
    if confirm_data is None:
        raise AttributeError("don't have token data, a data needed. generate_reset_token(self, confirm_data, expiration=1800)")
    if not isinstance(confirm_data, dict):
        raise TypeError("token data must be a dict object.")
    s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
    return s.dumps(confirm_data).decode("U8")


def confirm_reset_token(token, key):
    """重置, 解析用户令牌"""
    s = Serializer(current_app.config["SECRET_KEY"])
    try:
        confirm_data = s.loads(token.encode("U8"))
    except:
        return False
    return confirm_data.get(key, False)


@auth.route("/reset_pass_mail", endpoint="reset_pass_01", methods=["GET", "POST"])
def reset_pass01():
    """重设密码, 第一步, 确认邮箱, 并发送邮件"""
    form = EmailForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash("Don't have this user account.")
            return redirect(url_for("auth.reset_pass_01"))
        if not user.confirmed:
            flash("Account didn't confirmed. Please confirm your account first.")
            return redirect(url_for("auth.confirm"))
        token = generate_reset_token({"reset_pass": user.id})
        send_email(user.email, "重置密码", "auth/email/password_reset", user=user, token=token)
        return render_template("auth/prompt.html", prompt_title="Email", prompt_info="Email sended.")
    return render_template("auth/password_reset_01.html", form=form)


@auth.route("/reset_pass_confirm/<token>", endpoint="reset_pass_02", methods=["GET", "POST"])
def reset_pass02(token):
    """重设密码, 第二步, 接受重设请求, 通过验证, 更改密码, 成功后跳转"""
    form = ResetPasswordForm()
    if form.validate_on_submit():
        reset_user_id = confirm_reset_token(token, "reset_pass")
        if not reset_user_id:
            return render_template("auth/prompt.html", prompt_title="Fail", prompt_info="Wrong URL.")
        try:
            user = User.query.filter_by(id=int(reset_user_id)).first()
            if user is None:
                raise TypeError("None Type Error")
        except:
            return render_template("auth/prompt.html", prompt_title="Fail", prompt_info="Wrong URL.")
        user.password = form.new_pass.data
        db.session.add(user)
        db.session.commit()
        flash("Password reset success.")
        return redirect("auth.login")
    return render_template("auth/password_reset_02.html", form=form)


@auth.route("/reset_email", endpoint="change_email_01", methods=["GET", "POST"])
@login_required
def change_email01():
    """改变邮箱, 获取新邮箱, 发送确认邮件"""
    # if not current_user.confirmed:
    #     flash("Account didn't confirmed. Please confirm your account first.")
    #     return redirect(url_for("auth.confirm"))
    form = EmailForm()
    if form.validate_on_submit():
        CACHE.set(key="new_email_" + current_user.id, value=form.new_email.data, timeout=3600)
        token = generate_reset_token({"user_id": current_user.id}, expiration=3600)
        send_email(current_user.email, "重置密码", "auth/email/email_change", token=token)
    return render_template("auth/email_change.html", form=form)


@auth.route("/reset_email/<token>", endpoint="change_email_02")
def change_email02(token):
    """改变邮箱, 获取邮件中的token, 从缓存中获取新邮箱, 改变现在邮箱"""
    user_id = confirm_reset_token(token, "user_id")
    if not user_id:
        flash("Change email address failed.")
        logout_user()
        return redirect(url_for("main.index"))
    new_email = CACHE.get("new_email_" + user_id)
    if not new_email:
        flash("Change email address expired.")
        logout_user()
        return redirect(url_for("main_index"))
    try:
        user = User.query.filter_by(id=int(user_id)).first()
        if user is None:
            raise TypeError("None Type Error")
    except:
        abort(404)
    user.email = new_email
    user.avatar_hash = user.gravatar_hash()   # 更新头像hash缓存
    db.session.add(user)
    db.session.commit()
    flash("Email change success.")
    return redirect(url_for("auth.login"))
