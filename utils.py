from __future__ import annotations

from functools import wraps
from flask import abort, flash, redirect, session, url_for

from models import User


ROLE_HIERARCHY = {'Admin': 3, 'Manager': 2, 'QA': 1}


def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('login'))
            if user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
