import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import eventlet  # type: ignore

eventlet.monkey_patch()  # type: ignore

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, redirect, url_for
from flask_socketio import SocketIO
from dotenv import load_dotenv

from core.database import db
from core.models import Host, Config, User
from core.sockets import register_socket_events
from core.monitor import stats_monitoring_task
from core.i18n import I18nManager, _

# Blueprints
from blueprints.api import bp as api_bp
from blueprints.auth import bp as auth_bp
from blueprints.main import bp as main_bp
from blueprints.admin import bp as admin_bp
from blueprints.history import bp as history_bp
from blueprints.terminal import bp as terminal_bp
from blueprints.scripts import bp as scripts_bp

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# 환경 변수 기반 프록시 설정 (Cloudflare/Nginx 등)
load_dotenv()
USE_PROXY = os.getenv("PTSS_USE_PROXY", "false").lower() == "true"
if USE_PROXY:
    x_for = int(os.getenv("PTSS_PROXY_FIX_X_FOR", "1"))
    x_proto = int(os.getenv("PTSS_PROXY_FIX_X_PROTO", "1"))
    x_host = int(os.getenv("PTSS_PROXY_FIX_X_HOST", "1"))
    x_prefix = int(os.getenv("PTSS_PROXY_FIX_X_PREFIX", "1"))
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=x_for, x_proto=x_proto, x_host=x_host, x_prefix=x_prefix
    )
    logging.info(f"ProxyFix enabled: x_for={x_for}, x_prefix={x_prefix}")
else:
    logging.info("Running in Native Mode (ProxyFix disabled)")

# 로깅 설정 (ptss.log 작성)
basedir = os.path.abspath(os.path.dirname(__file__))
log_file = os.path.join(basedir, "ptss.log")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("PTSS")
logger.info("PTSS Server starting up...")

load_dotenv()
db_url = os.getenv("DATABASE_URL")

if not db_url:
    db_url = "sqlite:///" + os.path.join(basedir, "ptss.db")
elif db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
    db_path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_url = "sqlite:///" + os.path.join(basedir, db_path)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("PTSS_SECRET_KEY", os.urandom(24))
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

# Register Blueprints
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(history_bp)
app.register_blueprint(terminal_bp)
app.register_blueprint(scripts_bp)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=True,
    engineio_logger=True,
)

# Register SocketIO Handlers
register_socket_events(socketio, app)

# Initialize I18n
with app.app_context():
    I18nManager.load_translations()


@app.context_processor
def inject_i18n():
    return dict(_=_, get_lang=I18nManager.get_lang)


@app.before_request
def check_setup():
    if (
        request.path.startswith("/static")
        or request.path == "/setup"
        or request.path.startswith("/api/health")
    ):
        return
    if not User.query.first():
        return redirect(url_for("auth.setup"))


@app.context_processor
def inject_hosts():
    return {"all_hosts": Host.query.all()}


with app.app_context():
    db.create_all()
    # 기본 설정값 초기화
    default_configs = {
        "log_view_mode": "preview",
        "sftp_sort_by": "name",
        "session_retention": "maintain",
        "ssh_keepalive_interval": "30",
        "rec_auto_compress": "true",
        "rec_retention_days": "30",
    }
    for key, value in default_configs.items():
        if not Config.query.filter_by(key=key).first():
            db.session.add(Config(key=key, value=value))
    db.session.commit()

    DEBUG_MODE = os.getenv("PTSS_DEBUG", "false").lower() == "true"
    socketio.start_background_task(stats_monitoring_task, socketio, app)
    socketio.run(app, debug=DEBUG_MODE, use_reloader=False, host="0.0.0.0", port=6001)
