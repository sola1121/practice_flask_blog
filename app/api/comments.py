from flask import g, jsonify, request, url_for, current_app

from . import api
from .decorators import permission_required
from .. import db
from ..models import Permission, Comment, Post


@api.route("/comments/")
def get_comments():
    # 返回所有的评论
    page = request.args.get("page", 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(page, per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"], error_out=False)
    comments = pagination.items
    prev_page = None
    if pagination.has_prev:
        prev_page = url_for("api.get_comments", page=page-1)
    next_page = None
    if pagination.hax_next:
        next_page = url_for("api.get_comments", page=page+1)
    return jsonify({
        "comments": [comment.to_json() for comment in comments],
        "prev_url": prev_page, "next_url": next_page,
        "count": pagination.total,
    })


@api.route("/comments/<int:id>")
def get_comment(id):
    # 返回一篇评论
    comment = Comment.query.get_or_404(id)
    return jsonify({"comments": comment.to_json()})


@api.route("/posts/<int:id>/comments")
def get_post_comments(id):
    # 返回一篇博客文章的评论
    post = Post.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(page, per_page=current_app.config("FLASKY_COMMENTS_PER_PAGE"), error_out=False)
    comments = pagination.items
    prev_page = None
    if pagination.has_prev:
        prev_page = url_for("api.get_post_comments", id=id, page=page-1)
    next_page = None
    if pagination.hax_next:
        next_page = url_for("api.get_post_comments", id=id, page=page+1)
    return jsonify({
        "comments": [comment.to_sjon() for comment in comments],
        "prev_url": prev_page, "next_url": next_page,
        "count": pagination.total,
    })


@api.route("/posts/<int:id>/comments", methods=["POST"])
@permission_required(Permission.COMMENT)
def new_comment(id):
    # 对一篇文章进行评论
    post = Post.query.get_or_404(id)
    comment = Comment.from_json(request.json)
    comment.author = g.current_user
    comment.post = post
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_json()), 201, {'Location': url_for('api.get_comment', id=comment.id)}
