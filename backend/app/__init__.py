from flask import Flask
from .config.config import config_env
from .models.base import db
from .models.user import User
from .models.information_source import InformationSource  # noqa: F401
from .models.rss_wechat_article import RssWechatArticle  # noqa: F401
from .api.auth import bp_auth
from .api.sources import bp_sources
from .db_migrate import migrate_sqlite
from .services.seed_default_sources import ensure_default_sources
import os

def create_app():
    app = Flask(__name__)

    env = os.getenv("RUN_ENV", "development")
    app.config.from_object(config_env[env])

    db.init_app(app)
    with app.app_context():
        db.create_all()
        migrate_sqlite(db.engine)
        ensure_default_sources()
    
    app.register_blueprint(bp_auth, url_prefix="/api/auth")
    app.register_blueprint(bp_sources, url_prefix="/api/sources")

    @app.route('/')
    def index():
        return 'Index Page'

    @app.route('/hello')
    def hello():
        return 'Hello, World'
    
    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app