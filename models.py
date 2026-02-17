from database import db
from datetime import datetime


class Host(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(100), nullable=False)
    auth_type = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(100))
    encrypted_key = db.Column(db.Text)  # 실제 키 콘텐츠를 암호화하여 저장
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    histories = db.relationship(
        "History", backref="host", lazy=True, cascade="all, delete-orphan"
    )


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey("host.id"), nullable=False)
    action_type = db.Column(db.String(20), nullable=False)  # COMMAND, UPLOAD, DOWNLOAD
    detail = db.Column(db.Text, nullable=False)  # 명렁어나 파일명
    extra_info = db.Column(db.Text)  # 크기, 경로 등
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(100), nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")  # 'admin' or 'user'


class Script(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Snippet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), default="일반")
    name = db.Column(db.String(100), nullable=False)
    command = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
