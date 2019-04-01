from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth

from . import api
from .errors import unauthorized, forbidden
from ..models import User

auth = HTTPBasicAuth()


@auth.error_handler
def auth_error():
    return unauthorized("Invalid credentials")


@api.before_request
@auth.login_required
def before_request():
    # 用户已经注册, 但还没有完成确认的用户将会被拒
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden("Unconfirmed account") 


@auth.verify_password
def verify_password(email_or_token, password):
    # 可以依据邮件地址或是令牌来验证用户
    if email_or_token == "":
        return False
    if password == "":
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)


@api.route("/tokens/", methods=["POST"])
def get_token():
    # 检查g.token_used, 拒绝使用令牌验证身份. 防止用户绕过令牌过期机制.
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized("Invalid credentials")
    return jsonify({"token": g.current_user.generate_auth_token(expiration=3600), "expiration": 3600})
