from flask import g, jsonify, request, url_for, current_app

from . import api
from .. import db
from ..models import User, Post


@api.route("/users/<int:id>")
def get_user(id):
    # 返回一个用户
    user = User.query.get_or_404(id)
    return jsonify({"users": user.to_json()})


@api.route("/users/<int:id>/posts")
def get_user_posts(id):
    # 返回一个用户发布的所有博客文章
    user = User.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(page, per_page=current_app.config["FLASKY_POST_PER_PAGE"], error_out=False)
    posts = pagination.items
    prev_page = None
    if pagination.has_prev:
        prev_page = url_for("api.get_user_posts", id=id, page=page-1)
    next_page = None
    if pagination.has_next:
        next_page = url_for("api.get_user_posts", id=id, page=page+1)
    return jsonify({
        "posts": [post.to_json() for post in posts],
        "prev_url": prev_page, "next_url": next_page,
        "count": pagination.total,
    })


@api.route("/users/<int:id>/timeline")
def get_user_followed_posts(id):
    # 返回一个用户所关注用户发布的所有文章
    user = User.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = user.followed_posts.paginate(page, per_page=current_app.config["FLASKY_POST_PER_PAGE"], error_out=False)
    posts = pagination.items
    prev_page = None
    if pagination.has_prev:
        prev_page = url_for("api.get_user_followed_posts", id=id, page=page-1)
    if pagination.has_next:
        next_page = url_for("api.get_user_followed_posts", id=id, page=page+1)
    return jsonify({
        "posts": [post.to_json() for post in posts],
        "prev_url": prev_page, "next_url": next_page,
        "count": pagination.total,
    })
