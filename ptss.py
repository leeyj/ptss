import eventlet

eventlet.monkey_patch()  # 필수: 웹소켓과 다른 라이브러리 간의 비동기 호환성 확보

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    send_file,
    session,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import io
from ssh_manager import SSHManager
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# .env 로드 및 마스터 키 설정
load_dotenv()
MASTER_KEY = os.getenv("PTSS_MASTER_KEY")
if not MASTER_KEY:
    # 키가 없을 경우 임시 생성 (운영 환경에서는 반드시 .env에 고정 보관 필요)
    MASTER_KEY = Fernet.generate_key().decode()
cipher_suite = Fernet(MASTER_KEY.encode())


def encrypt_data(data: str) -> str:
    if not data:
        return None
    return cipher_suite.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    if not encrypted_data:
        return None
    return cipher_suite.decrypt(encrypted_data.encode()).decode()


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "ptss.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.urandom(24)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


from database import db

db.init_app(app)

from models import Host, History, Config, User, Script
from blueprints.api import bp as api_bp
from state import (
    ssh_sessions,
    monitoring_sessions,
    active_shells,
    active_sids,
    session_backlogs,
    sid_to_info,
    sid_to_host,
)
from collections import deque

app.register_blueprint(api_bp)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=True,
    engineio_logger=True,
)

# Global SSH Manager & Session tracking (Moved to state.py)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = User.query.get(session["user_id"])
        if not user or user.role != "admin":
            flash("관리자 권한이 필요합니다.")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
@login_required
def index():
    hosts = Host.query.all()
    # 활성화된 호스트 ID 목록 전달 (프론트엔드 모니터링용)
    active_hosts = list(ssh_sessions.keys())
    return render_template("index.html", hosts=hosts, active_hosts=active_hosts)


def stats_monitoring_task():
    """DB의 모든 호스트를 순회하며 실시간 상태 수집 (모니터링 전용 세션 사용)"""
    print("Dashboard Monitoring Task Active.")
    while True:
        socketio.sleep(5)  # 5초 주기
        with app.app_context():
            try:
                hosts = Host.query.all()
                for host in hosts:
                    manager = monitoring_sessions.get(host.id)

                    # 1. 세션이 없으면 자동 접속 시도
                    if not manager:
                        print(f"Auto-connecting to {host.name} for monitoring...")
                        manager = SSHManager()

                        # 암호화된 키가 있다면 복호화하여 전달
                        pkey_content = decrypt_data(host.encrypted_key)

                        success, _ = manager.connect(
                            host.hostname,
                            host.port,
                            host.username,
                            host.password,
                            pkey_content=pkey_content,
                        )
                        if success:
                            monitoring_sessions[host.id] = manager
                            socketio.emit(
                                "server_stats", {"host_id": host.id, "stats": "online"}
                            )
                        else:
                            continue

                    # 2. 상태 수집 및 전송
                    stats = manager.get_system_stats()
                    if stats:
                        socketio.emit(
                            "server_stats", {"host_id": host.id, "stats": stats}
                        )
            except Exception as e:
                print(f"Monitoring Loop Error: {e}")


monitoring_started = False


@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("index"))
        flash("로그인 정보가 올바르지 않습니다.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/history")
@login_required
def view_history():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)  # 20/30/50 선택 가능

    pagination = History.query.order_by(History.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    histories = pagination.items
    return render_template(
        "history.html", histories=histories, pagination=pagination, per_page=per_page
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        new_password = request.form.get("password")
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("비밀번호가 성공적으로 변경되었습니다.")
            return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def manage_users():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role", "user")

        if User.query.filter_by(username=username).first():
            flash("이미 존재하는 사용자 이름입니다.")
        else:
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role,
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"사용자 {username}이(가) 등록되었습니다.")
        return redirect(url_for("manage_users"))

    users = User.query.all()
    return render_template("users.html", users=users)


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("자기 자신은 삭제할 수 없습니다.")
        return redirect(url_for("manage_users"))

    user = User.query.get(user_id)
    if user:
        if user.username == "admin":
            flash("기본 관리자 계정은 삭제할 수 없습니다.")
        else:
            db.session.delete(user)
            db.session.commit()
            flash("사용자가 삭제되었습니다.")
    return redirect(url_for("manage_users"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def view_settings():
    if request.method == "POST":
        log_mode = request.form.get("log_view_mode")
        sftp_sort = request.form.get("sftp_sort_by")

        # Log view mode update
        conf_log = Config.query.filter_by(key="log_view_mode").first()
        if not conf_log:
            conf_log = Config(key="log_view_mode", value=log_mode)
            db.session.add(conf_log)
        else:
            conf_log.value = log_mode

        # SFTP sort update
        conf_sort = Config.query.filter_by(key="sftp_sort_by").first()
        if not conf_sort:
            conf_sort = Config(key="sftp_sort_by", value=sftp_sort)
            db.session.add(conf_sort)
        else:
            conf_sort.value = sftp_sort

        db.session.commit()
        return redirect(url_for("view_settings"))

    log_mode = Config.query.filter_by(key="log_view_mode").first()
    mode_val = log_mode.value if log_mode else "preview"

    sftp_sort = Config.query.filter_by(key="sftp_sort_by").first()
    sort_val = sftp_sort.value if sftp_sort else "name"

    return render_template(
        "settings.html", log_view_mode=mode_val, sftp_sort_by=sort_val
    )


@app.route("/log_view/<int:host_id>")
@login_required
def log_view_standalone(host_id):
    host = Host.query.get_or_404(host_id)
    path = request.args.get("path")
    log_mode = Config.query.filter_by(key="log_view_mode").first()
    mode_val = log_mode.value if log_mode else "preview"
    return render_template(
        "log_view.html", host=host, path=path, log_view_mode=mode_val
    )


@app.route("/host/add", methods=["POST"])
@admin_required
def add_host():
    # 개인키 파일 또는 직접 입력 처리
    key_content = request.form.get("key_content")
    key_file = request.files.get("key_file")

    if key_file and key_file.filename != "":
        key_content = key_file.read().decode("utf-8")

    new_host = Host(
        name=request.form["name"],
        hostname=request.form["hostname"],
        port=int(request.form["port"]),
        username=request.form["username"],
        auth_type=request.form["auth_type"],
        password=request.form.get("password"),
        encrypted_key=encrypt_data(key_content) if key_content else None,
    )
    db.session.add(new_host)
    db.session.commit()
    flash(
        f"호스트 {new_host.name}이(가) 추가되었습니다. (보안 정책에 따라 개인키는 암호화 저장되었습니다.)"
    )
    return redirect(url_for("index"))


@app.route("/host/delete/<int:host_id>", methods=["POST"])
@admin_required
def delete_host(host_id):
    host = Host.query.get_or_404(host_id)
    db.session.delete(host)
    db.session.commit()
    flash(f"호스트 {host.name}이(가) 삭제되었습니다.")
    return redirect(url_for("index"))


@app.route("/connect/<int:host_id>")
@login_required
def connect(host_id):
    host = Host.query.get_or_404(host_id)
    user_role = session.get("role")

    # 일반 사용자의 root 계정 접속 제한
    if user_role != "admin" and host.username == "root":
        return "일반 사용자는 root 계정으로 접속할 수 없습니다. (관리자 권한 필요)", 403

    manager = SSHManager()

    # 암호화된 키 복호화
    pkey_content = decrypt_data(host.encrypted_key)

    success, message = manager.connect(
        host.hostname,
        host.port,
        host.username,
        password=host.password,
        pkey_content=pkey_content,
    )

    if success:
        user_id = session["user_id"]
        ssh_sessions[(user_id, host_id)] = manager
        log_mode = Config.query.filter_by(key="log_view_mode").first()
        mode_val = log_mode.value if log_mode else "preview"

        sftp_sort = Config.query.filter_by(key="sftp_sort_by").first()
        sort_val = sftp_sort.value if sftp_sort else "name"

        return render_template(
            "console.html", host=host, log_view_mode=mode_val, sftp_sort_by=sort_val
        )
    else:
        return f"Connection Failed: {message}", 400


@app.context_processor
def inject_hosts():
    return {"all_hosts": Host.query.all()}


@socketio.on("terminal_connect")
def handle_terminal_connect(data):
    host_id = int(data.get("host_id"))
    tab_id = data.get("tab_id", "default")
    sid = request.sid
    user_id = session.get("user_id")

    # 세션 식별키
    session_key = (user_id, host_id, tab_id)
    sid_to_info[sid] = session_key
    sid_to_host[sid] = host_id
    active_sids[session_key] = sid

    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        emit(
            "terminal_output",
            {"data": "\r\n[PTSS] SSH 매니저를 찾을 수 없습니다.\r\n", "tab_id": tab_id},
        )
        return

    # 이미 존재하는 셸 세션이 있는지 확인 (퍼시스턴스)
    shell = active_shells.get(session_key)

    if shell:
        # 1. 기존 백로그 전송 (복구)
        backlog = session_backlogs.get(session_key, [])
        if backlog:
            emit("terminal_output", {"data": "".join(list(backlog)), "tab_id": tab_id})
        emit(
            "terminal_output",
            {"data": "\r\n[PTSS] 기존 세션 복구됨...\r\n", "tab_id": tab_id},
        )
    else:
        # 2. 신규 셸 생성
        shell = manager.get_shell()
        if not shell:
            emit(
                "terminal_output",
                {
                    "data": "\r\n[PTSS] 셸 세션을 시작할 수 없습니다.\r\n",
                    "tab_id": tab_id,
                },
            )
            return

        active_shells[session_key] = shell
        session_backlogs[session_key] = deque(maxlen=2000)  # 약 2000라인 가량 보관

        def shell_to_socket(s_key):
            """백그라운드에서 셸 출력을 읽어 소켓으로 브로드캐스팅 및 백로그 저장"""
            while True:
                target_shell = active_shells.get(s_key)
                if not target_shell:
                    break
                try:
                    if target_shell.recv_ready():
                        output = target_shell.recv(4096).decode(
                            "utf-8", errors="ignore"
                        )
                        # 백로그에 추가
                        if s_key in session_backlogs:
                            session_backlogs[s_key].append(output)

                        # 현재 활성화된 SID가 있으면 출력 전송
                        current_sid = active_sids.get(s_key)
                        if current_sid:
                            socketio.emit(
                                "terminal_output",
                                {"data": output, "tab_id": s_key[2]},
                                room=current_sid,
                            )
                    socketio.sleep(0.01)
                except Exception:
                    # 세션 종료 시 정리
                    active_shells.pop(s_key, None)
                    active_sids.pop(s_key, None)
                    session_backlogs.pop(s_key, None)
                    break

        socketio.start_background_task(shell_to_socket, session_key)
        emit(
            "terminal_output",
            {"data": "\r\n[PTSS] 실시간 서버 연결 성공...\r\n", "tab_id": tab_id},
        )


@socketio.on("terminal_input")
def handle_terminal_input(data):
    sid = request.sid
    tab_id = data.get("tab_id", "default")
    user_id = session.get("user_id")
    host_id = sid_to_host.get(sid)

    if not host_id:
        return

    session_key = (user_id, host_id, tab_id)
    shell = active_shells.get(session_key)

    if not shell:
        return

    input_data = data.get("data")

    # 셸에 즉시 전송
    # 3. 일반 사용자의 su 명령어 사용 제한
    user_role = session.get("role")
    if user_role != "admin" and (
        input_data.strip().startswith("su ") or input_data.strip() == "su"
    ):
        socketio.emit(
            "terminal_output",
            {
                "data": "\r\n[PTSS] 일반 사용자는 su 명령어를 사용할 수 없습니다. (관리자 권한 필요)\r\n",
                "tab_id": tab_id,
            },
            room=sid,
        )
        return

    shell.send(input_data)


@socketio.on("terminal_command")
def handle_terminal_command(data):
    sid = request.sid
    cmd = data.get("command", "").strip()
    host_id = sid_to_host.get(sid)

    if host_id and cmd:
        with app.app_context():
            new_hist = History(host_id=host_id, action_type="COMMAND", detail=cmd)
            db.session.add(new_hist)
            db.session.commit()
            print(f"[History] Saved: {cmd} (Host: {host_id})")


@socketio.on("terminal_resize")
def handle_terminal_resize(data):
    sid = request.sid
    tab_id = data.get("tab_id", "default")
    user_id = session.get("user_id")
    host_id = sid_to_host.get(sid)

    if host_id:
        session_key = (user_id, host_id, tab_id)
        shell = active_shells.get(session_key)
        if shell:
            try:
                shell.resize_pty(
                    width=int(data.get("cols", 80)), height=int(data.get("rows", 24))
                )
            except:
                pass


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    # SID 매핑 정보 제거 (셸은 유지됨)
    session_key = sid_to_info.pop(sid, None)
    if session_key:
        # 현재 활성 SID가 내 것이라면 제거
        if active_sids.get(session_key) == sid:
            active_sids.pop(session_key, None)
    sid_to_host.pop(sid, None)
    print(f"Client disconnected and SID mapping cleared: {sid}")


# Automation Script Tool Routes
@app.route("/scripts")
@login_required
def view_scripts():
    scripts = Script.query.all()
    hosts = Host.query.all()
    return render_template("scripts.html", scripts=scripts, hosts=hosts)


with app.app_context():
    db.create_all()
    # 초기 설정값 보장
    if not Config.query.filter_by(key="log_view_mode").first():
        db.session.add(Config(key="log_view_mode", value="preview"))
    if not Config.query.filter_by(key="sftp_sort_by").first():
        db.session.add(Config(key="sftp_sort_by", value="name"))

    # 기본 관리자 계정 생성
    if not User.query.filter_by(username="admin").first():
        admin_user = User(
            username="admin", password_hash=generate_password_hash("[REDACTED]")
        )
        db.session.add(admin_user)

    db.session.commit()


if __name__ == "__main__":
    # 서버 기동 시 모니터링 태스크 강제 시작
    socketio.start_background_task(stats_monitoring_task)
    socketio.run(app, debug=False, host="0.0.0.0", port=6001)
