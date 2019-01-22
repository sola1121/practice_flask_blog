from flask import render_template
from . import auth


@auth.errorhandler(403)
def page_forbidden():
    return render_template("auth/403.html")
