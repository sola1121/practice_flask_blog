from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required
from . import auth
from .forms import LoginForm
from ..models import User

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
