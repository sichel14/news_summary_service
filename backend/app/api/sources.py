from dataclasses import asdict

from flask import Blueprint, jsonify, request, g
from sqlalchemy.exc import IntegrityError

from app.api.decorators import jwt_required
from app.models.base import db
from app.models.information_source import InformationSource
from app.services.rss_sync import sync_rss_for_source

bp_sources = Blueprint("sources", __name__)


@bp_sources.post("add_src")
@jwt_required
def add_information_source():
    """登录用户添加 RSS 信息源（需在 Header 中携带 Bearer JWT）。"""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    rss_url = (data.get("rss_url") or "").strip()
    intro = data.get("intro")
    if intro is not None:
        intro = str(intro).strip() or None

    if not name or not rss_url:
        return jsonify({"error": "name and rss_url required"}), 400

    src = InformationSource(name=name, intro=intro, rss_url=rss_url)
    db.session.add(src)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "rss_url already exists"}), 409

    return (
        jsonify(
            {
                "id": src.id,
                "name": src.name,
                "intro": src.intro,
                "rss_url": src.rss_url,
                "added_by_phone": g.jwt_phone,
            }
        ),
        201,
    )


@bp_sources.post("<int:source_id>/sync")
@jwt_required
def sync_information_source(source_id: int):
    """登录后触发指定信息源的 RSS 拉取与入库（按 aid 去重）。"""
    try:
        result = sync_rss_for_source(source_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "database conflict"}), 409

    return jsonify(asdict(result)), 200
