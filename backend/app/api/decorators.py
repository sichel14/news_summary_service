from functools import wraps

import jwt
from flask import current_app, g, jsonify, request


def jwt_required(f):
    """要求请求头携带 ``Authorization: Bearer <access_token>``，校验通过后可在视图内使用 ``g.jwt_phone``（即登录时的手机号）。"""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "authorization required"}), 401
        token = auth[7:].strip()
        if not token:
            return jsonify({"error": "authorization required"}), 401
        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401
        g.jwt_phone = payload.get("sub")
        return f(*args, **kwargs)

    return decorated
