import os

base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Config:
    DEBUG = False
    SECRET_KEY = "sichel14"
    JWT_EXPIRATION = 7 * 24 * 60 * 60 # 7 days
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(base_path, "database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    pass

# 映射环境
config_env = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}
