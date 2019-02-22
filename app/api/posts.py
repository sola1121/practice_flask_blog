from flask import g, jsonify, request, url_for, current_app

from . import api
from .errors import forbidden
from .decorators import permission_required
from .. import db
from ..models import Permission, Post


@api.route("/posts/", methods=["GET"])
def get_posts():
    # 使用GET获取所有的post
    page = request.args.get("page", 1, type=int)
    pagination = Post.query.paginate(page, per_page=current_app.config["FLASKY_POSTS_PER_PAGE"], error_out=False)
    posts = pagination.items
    prev_page = None
    if pagination.has_prev:
        prev_page = url_for("api.get_posts", page=page-1)
    next_page = None
    if pagination.has_next:
        next_page = url_for("api.get_posts", page=page+1)
    return jsonify({
        "posts": [post.to_json() for post in posts],
        "prev_url": prev_page, "next_url": next_page,
        "count": pagination.total,
    })


@api.route("/posts/<int:id>", methods=["GET"])
def get_post(id):
    # 使用GET获取指定id的post
    post = Post.query.get_or_404(id)
    return jsonify({"posts": post.to_json()})


@api.route("/posts/", methods=["POST"])
@permission_required(Permission.WRITE)
def new_post():
    # 使用POST新建post
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    ad.session.commit()
    return jsonify(post.to_json(), 201, {"Location": url_for("api.get_post", id=post.id)})


@api.route("/posts/<int:id>", methods=["PUT"])
@permission_required(Permission.WRITE)
def edit_post(id):
    # 使用PUT更改post
    post = Post.query.get_or_404(id)
    if g.current_user != post.author and not g.current_user.can(Permission.ADMIN):
        return forbidden("Insuficient permissions")
    post.body = request.json.get("body", post.body)   # 让原post的body如果有新的提交变为新的, 否则还是原来的.
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())
