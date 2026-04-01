from .base import BaseModel, db


class InformationSource(BaseModel):
    """RSS 等信息源。"""

    __tablename__ = "information_sources"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    intro = db.Column(db.Text, nullable=True)
    rss_url = db.Column(db.String(512), nullable=False, unique=True)
