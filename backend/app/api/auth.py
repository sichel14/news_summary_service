from flask import Blueprint, request, jsonify, current_app
import jwt
from datetime import datetime, timezone, timedelta
from app.models.base import db
from app.models.user import User

bp_auth = Blueprint("auth", __name__)

def _make_token(phone_number: str, scopes: list or None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        seconds=current_app.config["JWT_EXPIRATION"]
    )
    payload = {
        "sub": str(phone_number),
        "exp": exp,
    }
    if scopes:
        payload["scopes"] = scopes  # 以后做 endpoint-level 用
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm="HS256",
    )


@bp_auth.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    phone_number = (data.get("phone_number") or "").strip()
    password = data.get("password") or ""

    if not phone_number or not password:
        return jsonify({"error": "phone_number and password required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password too short"}), 400

    if User.query.filter_by(phone_number=phone_number).first():
        return jsonify({"error": "phone_number taken"}), 409

    user = User(phone_number=phone_number)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({"phone_number": user.phone_number}), 200

@bp_auth.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    phone_number = (data.get("phone_number") or "").strip()
    password = data.get("password") or ""

    if not phone_number or not password:
        return jsonify({"error": "phone_number and password required"}), 400

    user = User.query.filter_by(phone_number=phone_number).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid phone_number or password"}), 401

    token = _make_token(user.phone_number)

    return jsonify({
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": current_app.config["JWT_EXPIRATION"],
    }), 200

    # return jsonify({"phone_number": user.phone_number}), 200
