import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import eventlet  # type: ignore

eventlet.monkey_patch()  # type: ignore

import os

# import sys
# import functools
# from datetime import datetime
from collections import deque

from flask import (  # type: ignore
    Flask,
    request,
    redirect,
    url_for,
    session,
)
from flask_socketio import SocketIO, emit  # type: ignore

# from flask_socketio import disconnect
# from werkzeug.security import generate_password_hash, check_password_hash
# from cryptography.fernet import Fernet  # type: ignore
from dotenv import load_dotenv  # type: ignore

from core.database import db  # type: ignore
from core.models import Host, History, Config, User  # type: ignore
from core.state import (  # type: ignore
    ssh_sessions,
    monitoring_sessions,
    active_shells,
    active_sids,
    session_backlogs,
    terminal_buffers,
    sid_to_info,
    sid_to_host,
    host_watchers,
)
from core.ssh_manager import SSHManager  # type: ignore
from core.crypto import decrypt_data  # type: ignore

# Blueprints
from blueprints.api import bp as api_bp  # type: ignore
from blueprints.auth import bp as auth_bp  # type: ignore
from blueprints.main import bp as main_bp  # type: ignore
from blueprints.admin import bp as admin_bp  # type: ignore
from blueprints.history import bp as history_bp  # type: ignore
from blueprints.terminal import bp as terminal_bp  # type: ignore
from blueprints.scripts import bp as scripts_bp  # type: ignore

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()
db_url = os.getenv("DATABASE_URL")

if not db_url:
    # .env가 없거나 값이 비어있을 경우 기본값 사용
    db_url = "sqlite:///" + os.path.join(basedir, "ptss.db")
elif db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
    # sqlite:/// (슬래시 3개)로 시작하면서 절대경로(/)가 아닌 경우 basedir 결합
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


@app.before_request
def check_setup():
    if (
        request.path.startswith("/static")
        or request.path == "/setup"
        or request.path.startswith("/api/health")
    ):
        return

    # 사용자가 하나도 없으면 /setup으로 리디렉션
    if not User.query.first():
        return redirect(url_for("auth.setup"))


@app.context_processor
def inject_hosts():
    return {"all_hosts": Host.query.all()}


monitoring_failures = {}


def connect_and_monitor(host_id):
    """Helper to connect for monitoring if not already connected."""
    if host_id in monitoring_sessions:
        return True, "Already connected"

    with app.app_context():
        host = Host.query.get(host_id)
        if not host:
            return False, "Host not found"

        try:
            decrypted_pw = decrypt_data(host.password) if host.password else None
            decrypted_key = (
                decrypt_data(host.encrypted_key) if host.encrypted_key else None
            )
            pkey_content = decrypted_key

            ka_conf = Config.query.filter_by(key="ssh_keepalive_interval").first()
            keepalive_val = int(ka_conf.value) if ka_conf else 0

            manager = SSHManager()
            success, message = manager.connect(
                host.hostname,
                host.port,
                host.username,
                password=decrypted_pw,
                pkey_content=pkey_content,
                keepalive=keepalive_val,
            )
            if success:
                monitoring_sessions[host.id] = manager
                return True, "Connected"
            else:
                return False, message
        except Exception as e:
            return False, str(e)


def stats_monitoring_task():
    """모니터링 세션이 활성화된 호스트만 상태 수집"""
    print("Dashboard Monitoring Task Active.")
    while True:
        with app.app_context():
            # 활성 모니터링 세션만 순회 (keys를 리스트로 복사하여 순회 중 변경 오류 방지)
            active_ids = list(monitoring_sessions.keys())
            for host_id in active_ids:
                manager = monitoring_sessions.get(host_id)
                if not manager:
                    continue

                try:
                    stats = manager.get_system_stats()
                    if stats:
                        socketio.emit(
                            "server_stats",
                            {"host_id": host_id, "stats": stats},
                            room=f"monitoring_{host_id}",
                        )
                    else:
                        # 통신 실패 시 세션 정리
                        print(f"[Monitoring] Stats fail for {host_id}. Closing.")
                        try:
                            manager.close()
                        except:
                            pass
                        monitoring_sessions.pop(host_id, None)

                        socketio.emit(
                            "host_status_change",
                            {"host_id": host_id, "status": "offline"},
                            room=f"monitoring_{host_id}",
                        )
                except Exception as e:
                    print(f"[Monitoring Task Error] {host_id}: {str(e)}")

        socketio.sleep(5)


@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect_socket():
    sid = request.sid
    print(f"Client disconnected: {sid}")

    # 1. Monitoring Watchers Cleanup
    for host_id, watchers in list(host_watchers.items()):
        if sid in watchers:
            watchers.discard(sid)
            # socketio.leave_room(f"monitoring_{host_id}", sid) # disconnect 시에는 자동 해제됨

            if not watchers and host_id in monitoring_sessions:
                print(f"[Auto-Stop] No watchers for {host_id}. Disconnecting.")
                manager = monitoring_sessions.pop(host_id, None)
                if manager:
                    try:
                        manager.close()
                    except:
                        pass
                socketio.emit(
                    "host_status_change",
                    {"host_id": host_id, "status": "offline"},
                    room=f"monitoring_{host_id}",
                )
            if not watchers:
                del host_watchers[host_id]

    # 2. Terminal Session Cleanup
    s_info = sid_to_info.pop(sid, None)
    if s_info:
        user_id, host_id, tab_id = s_info
        session_key = (user_id, host_id, tab_id)
        active_sids.pop(session_key, None)
        active_shells.pop(session_key, None)

        with app.app_context():
            retention = Config.query.filter_by(key="session_retention").first()
            if retention and retention.value == "terminate":
                # 현재 사용자의 해당 호스트에 대해 다른 활성 탭이 있는지 확인
                still_has_tabs = any(
                    k[0] == user_id and k[1] == host_id for k in active_sids.keys()
                )

                if not still_has_tabs:
                    manager = ssh_sessions.pop((user_id, host_id), None)
                    if manager:
                        print(
                            f"[Policy] Closing SSH session for user {user_id}, host {host_id} (No more tabs)"
                        )
                        try:
                            manager.close()
                        except Exception as e:
                            print(f"[Policy Error] Manager close fail: {e}")
                else:
                    print(f"[Policy] SSH session maintained (Remaining tabs exist)")


@socketio.on("start_monitoring")
def handle_start_monitoring(data):
    host_id = data.get("host_id")
    sid = request.sid
    if not host_id:
        return

    print(f"Start monitoring request for {host_id} from {sid}")

    # 구독자 추가 및 룸 접속
    if host_id not in host_watchers:
        host_watchers[host_id] = set()
    host_watchers[host_id].add(sid)

    from flask_socketio import join_room  # type: ignore

    join_room(f"monitoring_{host_id}")

    # 이미 연결되어 있다면 성공 응답
    if host_id in monitoring_sessions:
        emit("monitoring_started", {"host_id": host_id, "status": "active"})
        socketio.emit(
            "host_status_change",
            {"host_id": host_id, "status": "online"},
            room=f"monitoring_{host_id}",
        )
        return

    # 연결 시도
    success, msg = connect_and_monitor(host_id)
    if success:
        emit("monitoring_started", {"host_id": host_id, "status": "active"})
        socketio.emit(
            "host_status_change",
            {"host_id": host_id, "status": "online"},
            room=f"monitoring_{host_id}",
        )
    else:
        emit("monitoring_error", {"host_id": host_id, "message": msg})


@socketio.on("stop_monitoring")
def handle_stop_monitoring(data):
    host_id = data.get("host_id")
    sid = request.sid
    if not host_id:
        return

    print(f"Stop monitoring request for {host_id} from {sid}")

    if host_id in host_watchers:
        host_watchers[host_id].discard(sid)

        from flask_socketio import leave_room  # type: ignore

        leave_room(f"monitoring_{host_id}")

        if not host_watchers[host_id]:
            # 구독자가 없으면 연결 해제
            print(f"No watchers for {host_id}. Closing connection.")
            manager = monitoring_sessions.pop(host_id, None)
            if manager:
                try:
                    manager.close()
                except:
                    pass
            socketio.emit(
                "host_status_change",
                {"host_id": host_id, "status": "offline"},
                room=f"monitoring_{host_id}",
            )


@socketio.on("terminal_connect")
def handle_terminal_connect(data):
    host_id = int(data.get("host_id"))
    tab_id = data.get("tab_id", "default")
    sid = request.sid
    user_id = session.get("user_id")

    if not user_id:
        emit(
            "terminal_output",
            {"data": "\r\n[ERROR] Unauthorized\r\n", "tab_id": tab_id},
        )
        return

    sid_to_host[sid] = host_id
    session_key = (user_id, host_id, tab_id)
    active_sids[session_key] = sid
    sid_to_info[sid] = (user_id, host_id, tab_id)  # 튜플 보관

    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        emit(
            "terminal_output",
            {
                "data": "\r\n[ERROR] SSH Session lost. Please reconnect.\r\n",
                "tab_id": tab_id,
            },
        )
        return

    shell = active_shells.get(session_key)
    if shell:
        backlog = session_backlogs.get(session_key, [])
        if backlog:
            emit("terminal_output", {"data": "".join(list(backlog)), "tab_id": tab_id})
        emit(
            "terminal_output",
            {"data": "\r\n[PTSS] 기존 세션 복구됨...\r\n", "tab_id": tab_id},
        )
    else:
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
        session_backlogs[session_key] = deque(maxlen=2000)

        def shell_to_socket(s_key):
            while True:
                target_shell = active_shells.get(s_key)
                if not target_shell:
                    break
                try:
                    if target_shell.recv_ready():
                        output = target_shell.recv(4096).decode(
                            "utf-8", errors="ignore"
                        )
                        if s_key in session_backlogs:
                            session_backlogs[s_key].append(output)
                        current_sid = active_sids.get(s_key)
                        if current_sid:
                            socketio.emit(
                                "terminal_output",
                                {"data": output, "tab_id": s_key[2]},
                                room=current_sid,
                            )
                    socketio.sleep(0.01)
                except Exception:
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

    # sid_to_info에서 우선적으로 정보를 가져옴
    s_info = sid_to_info.get(sid)
    if s_info:
        user_id, host_id, _ = s_info
    else:
        user_id = session.get("user_id")
        host_id = sid_to_host.get(sid)

    if not user_id or not host_id:
        return

    session_key = (user_id, host_id, tab_id)
    shell = active_shells.get(session_key)
    input_data = data.get("data")
    user_role = session.get("role")

    if user_role != "admin":
        if session_key not in terminal_buffers:
            terminal_buffers[session_key] = ""

        for char in input_data:
            if char in ["\r", "\n"]:
                full_cmd = terminal_buffers[session_key].strip()
                if full_cmd:
                    user = User.query.get(user_id)
                    if user and user.restricted_commands:
                        blacklist = [
                            k.strip()
                            for k in user.restricted_commands.split(",")
                            if k.strip()
                        ]
                        for keyword in blacklist:
                            if keyword and keyword in full_cmd:
                                if shell:
                                    shell.send("\x15")
                                terminal_buffers[session_key] = ""
                                socketio.emit(
                                    "terminal_output",
                                    {
                                        "data": f"\r\n\x1b[31m[PTSS] 금지된 명령어가 포함되어 있습니다: '{keyword}'\x1b[0m\r\n",
                                        "tab_id": tab_id,
                                    },
                                    room=sid,
                                )
                                new_hist = History(
                                    host_id=host_id,
                                    user_id=user_id,
                                    action_type="BLOCKED",
                                    detail=full_cmd,
                                )
                                db.session.add(new_hist)
                                db.session.commit()
                                return
                terminal_buffers[session_key] = ""
            elif char in ["\x7f", "\x08"]:
                if len(terminal_buffers[session_key]) > 0:
                    terminal_buffers[session_key] = terminal_buffers[session_key][:-1]
            elif isinstance(char, str) and ord(char) >= 32:
                terminal_buffers[session_key] += char

    if shell:
        shell.send(input_data)


@socketio.on("terminal_command")
def handle_terminal_command(data):
    sid = request.sid
    cmd = data.get("command", "").strip()
    host_id = sid_to_host.get(sid)
    s_info = sid_to_info.get(sid)
    user_id = s_info[0] if s_info else session.get("user_id")

    if host_id and cmd:
        with app.app_context():
            new_hist = History(
                host_id=host_id, user_id=user_id, action_type="COMMAND", detail=cmd
            )
            db.session.add(new_hist)
            db.session.commit()


@socketio.on("terminal_resize")
def handle_terminal_resize(data):
    sid = request.sid
    tab_id = data.get("tab_id", "default")

    s_info = sid_to_info.get(sid)
    if s_info:
        user_id, host_id, _ = s_info
    else:
        user_id = session.get("user_id")
        host_id = sid_to_host.get(sid)

    if host_id and user_id:
        session_key = (user_id, host_id, tab_id)
        shell = active_shells.get(session_key)
        if shell:
            try:
                # Paramiko의 resize_pty는 width, height 인자를 사용함
                shell.resize_pty(
                    width=int(data.get("cols", 80)), height=int(data.get("rows", 24))
                )
            except Exception as e:
                print(f"PTY Resize Error: {e}")


with app.app_context():
    db.create_all()
    if not Config.query.filter_by(key="log_view_mode").first():
        db.session.add(Config(key="log_view_mode", value="preview"))
    if not Config.query.filter_by(key="sftp_sort_by").first():
        db.session.add(Config(key="sftp_sort_by", value="name"))
    if not Config.query.filter_by(key="session_retention").first():
        db.session.add(Config(key="session_retention", value="maintain"))
    db.session.commit()

if __name__ == "__main__":
    socketio.start_background_task(stats_monitoring_task)
    socketio.run(app, debug=True, use_reloader=False, host="0.0.0.0", port=6001)
