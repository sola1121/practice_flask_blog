from flask import render_template, request, make_response, session, redirect, url_for, current_app, flash, abort
from flask_login import login_required, current_user

from .. import db
from ..models import User, Role, Permission, Post, Comment
from ..email import send_email
from ..decorators import admin_required, permission_required
from . import main
from .forms import NameForm, EditProfileForm, EditProfileAdminForm, PostForm, CommentForm


@main.route("/", methods=["GET", "POST"])
def index():
    """首页显示"""
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        new_post = Post(body=form.body.data, author=current_user._get_current_object())
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for(".index"))
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get("show_followed", ""))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    # 使用分页
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_POST_PER_PAGE"], error_out=False
    )
    posts = pagination.items
    return render_template("index.html", form=form, posts=posts, pagination=pagination, show_followed=show_followed)


@main.route("/all")
@login_required
def show_all():
    """记住用户的选项, 重定向到index"""
    resp = make_response(redirect(url_for(".index")))
    resp.set_cookie("show_followed", "", max_age=3600*24*30)   # 30天
    return resp


@main.route("/followed")
@login_required
def show_followed():
    """记住用户的选项, 重定向到index"""
    resp = make_response(redirect(url_for(".index")))
    resp.set_cookie("show_followed", "1", max_age=3600*24*30)   # 30天
    return resp


@main.route("/user/<username>")
def user(username):
    """用户资料页"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template("user.html", user=user, posts=posts)


@main.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    """用于对应用户的用户资料编辑"""
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.location.data
        db.session.add(current_user)   # current_user._get_current_object()
        db.session.commit()
        flash("Your profile has been update.")
        return redirect(url_for(".user", username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", form=form)


@main.route('/edit-profile/<int:id>', endpoint="edit_profile_admin", methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    """用于管理员的用户资料编辑"""
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    """在单独的页面显示文章"""
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                         post=post,
                         author=current_user._get_current_object()
        )
        db.session.add(comment)
        db.session.commit()
        flash("Your comment has been published")
        return redirect(url_for(".post", id=post.id, page=-1))   # -1显示最后一页, 提交成功后将会自动定位到最后一页评论
    page = request.args.get("page", 1, type=int)
    if page == -1:   # 设定特定页数-1的处理方式
        page = (post.comments.count()-1) // current_app.config["FLASKY_COMMENTS_PER_PAGE"] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(page, 
                                                                          per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"],
                                                                          error_out=False
                                                                )
    comments = pagination.items
    return render_template("post.html", posts=[post], form=form, comments=comments, pagination=pagination)


@main.route("/editpost/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    """在对文章进行编辑"""
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash("The post has been updated.")
        return redirect(url_for(".post", id=post.id))
    form.body.data = post.body
    return render_template("edit_post.html", form=form)


@main.route("/follow/<username>")
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    """关注用户"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user.")
        return redirect(url_for(".index"))
    if current_user.is_following(user):
        flash("You are already following this user.")
        return redirect(url_for(".user", username=username))
    current_user.follow(user)
    db.session.commit()
    flash("You are now following %s." % username)
    return redirect(url_for(".user", username=username))


@main.route("/unfollow/<username>")
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    """不关注用户"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user.")
        return redirect(url_for(".index"))
    if not current_user.is_following(user):
        flash("You are not following this user.")
        return redirect(url_for(".user", username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash("You are now not following %s" % username)
    return redirect(url_for(".user", username=username))


@main.route("/followers/<username>")
def followers(username):
    """关注指定用户的"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user.")
        return redirect(url_for(".index"))
    # 当前用户关注的
    page = request.args.get("page", 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config["FLASKY_FOLLOWERS_PER_PAGE"], error_out=False
    )
    follows = [{"user": item.follower, "timestamp": item.timestamp} for item in pagination.items]
    return render_template("followers.html", user=user, title="Followers of", endpoint=".followers",
                            pagination=pagination, follows=follows)


@main.route("/followed_by/<username>")
def followed_by(username):
    """指定用户关注的"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user.")
        return redirect(url_for(".index"))
    # 关注当前用户的
    page = request.args.get("page", 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config["FLASKY_FOLLOWERS_PER_PAGE"], error_out=False
    )
    follows = [{"user": item.followed, "timestamp": item.timestamp} for item in pagination.items]
    return render_template("followers.html", user=user, title="Followed by", endpoint=".followed_by",
                            pagination=pagination, follows=follows)


@main.route("/moderate")
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get("page", 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(page,
                                                                           per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"],
                                                                           error_out=False
                                                                  )
    comments = pagination.items
    return render_template("moderate.html", comments=comments, pagination=pagination, page=page)


@main.route("/moderate/enable/<int:id>")
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for(".moderate", page=request.args.get("page", 1, type=int)))

@main.route("/moderate/disable/<int:id>")
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for(".moderate", page=request.args.get("page", 1, type=int)))
