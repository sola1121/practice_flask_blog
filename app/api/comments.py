from flask import g, jsonify

from . import api
from ..models import Permisssion, Comment

@api.route("/comments/")
def get_comments():
    comments = Comment.query.all()
    return jsonify({"comments": [comment.to_json() for comment in comments]})
