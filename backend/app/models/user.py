from .base import BaseModel, db

class User(BaseModel):
    __tablename__ = "users"
    phone_number = db.Column(db.String(11), nullable=False, unique=True, primary_key=True)
    username = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(100), nullable=False)

    def set_password(self, raw: str):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(raw)

    def check_password(self, raw: str):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, raw)