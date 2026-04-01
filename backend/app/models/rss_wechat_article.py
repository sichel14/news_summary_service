from sqlalchemy import UniqueConstraint

from .base import BaseModel, db


class RssWechatArticle(BaseModel):
    """微信公众号 RSS 文章。"""

    __tablename__ = "rss_wechat_article"
    __table_args__ = (
        UniqueConstraint(
            "information_source_id",
            "aid",
            name="uq_rss_wechat_article_source_aid",
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=True)
    information_source_id = db.Column(
        db.Integer, db.ForeignKey("information_sources.id"), nullable=False
    )
    # 源站文章唯一标识（与 information_source_id 联合唯一）
    aid = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(512), nullable=True)