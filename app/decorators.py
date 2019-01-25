from flask import abort
from flask_login import current_user

from .models import Permission

import functools

def permission_required(permission):
    """用于检查用户权限的自定义装饰器, 使用curren_user判断"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)
