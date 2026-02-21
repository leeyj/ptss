import os
import json
import time
from collections import deque
from flask import request, session
from flask_socketio import emit, join_room, leave_room
from core.database import db
from core.state import (
    ssh_sessions,
    monitoring_sessions,
    active_shells,
    active_sids,
    session_backlogs,
    terminal_buffers,
    sid_to_info,
    sid_to_host,
    host_watchers,
    pending_guards,
    recording_sessions,
)
from core.i18n import _
from core.recording import compress_recording, cleanup_old_recordings
from core.monitor import connect_and_monitor, stats_monitoring_task


def register_socket_events(socketio, app):
    @socketio.on("connect")
    def handle_connect():
        print(f"Client connected: {request.sid}")

    @socketio.on("disconnect")
    def handle_disconnect_socket():
        sid = request.sid
        print(f"Client disconnected: {sid}")

        for host_id, watchers in list(host_watchers.items()):
            if sid in watchers:
                watchers.remove(sid)
                if not watchers:
                    host_watchers.pop(host_id)
                    # 만약 다른 터미널 세션이 없다면 모니터링 세션도 종료 고려 (선택 사항)
                    # if host_id in monitoring_sessions:
                    #     monitoring_sessions.pop(host_id).close()

        # 터미널 세션 연결 고리 해제 (실제 셸은 유지)
        if sid in sid_to_info:
            s_key = sid_to_info.pop(sid)
            if s_key in active_sids:
                active_sids.pop(s_key, None)
            print(f"Detached SID {sid} from session {s_key}")

    @socketio.on("join_monitoring")
    def handle_join_monitoring(data):
        host_id = data.get("host_id")
        if not host_id:
            return

        # 권한 확인
        if session.get("role") != "admin":
            emit("error", {"message": _("Unauthorized access")})
            return

        room = f"monitoring_{host_id}"
        join_room(room)

        if host_id not in host_watchers:
            host_watchers[host_id] = set()
        host_watchers[host_id].add(request.sid)

        # 연결 시도
        success, message = connect_and_monitor(host_id, app)
        if not success:
            emit("error", {"message": f"Monitoring failed: {message}"})
        else:
            emit("monitoring_started", {"host_id": host_id})

    @socketio.on("leave_monitoring")
    def handle_leave_monitoring(data):
        host_id = data.get("host_id")
        if not host_id:
            return
        room = f"monitoring_{host_id}"
        leave_room(room)
        if host_id in host_watchers:
            host_watchers[host_id].discard(request.sid)
            if not host_watchers[host_id]:
                host_watchers.pop(host_id)

    @socketio.on("terminal_connect")
    def handle_terminal_connect(data):
        user_id = session.get("user_id")
        host_id = data.get("host_id")
        tab_id = data.get("tab_id", "default")

        if not user_id or not host_id:
            emit("error", {"message": "Invalid session or host"})
            return

        session_key = (user_id, host_id, tab_id)
        active_sids[session_key] = request.sid
        sid_to_info[request.sid] = session_key

        # 세션 복구 처리
        if session_key in active_shells:
            print(f"Restoring session: {session_key}")
            # 백로그 전송
            backlog = list(session_backlogs.get(session_key, []))
            emit("terminal_output", {"data": "".join(backlog), "tab_id": tab_id})
            return

        # 신규 연결
        with app.app_context():
            from core.models import Host, Config

            host = Host.query.get(host_id)
            if not host:
                emit("error", {"message": "Host not found"})
                return

            try:
                decrypted_pw = decrypt_data(host.password) if host.password else None
                decrypted_key = (
                    decrypt_data(host.encrypted_key) if host.encrypted_key else None
                )

                ka_conf = Config.query.filter_by(key="ssh_keepalive_interval").first()
                keepalive_val = int(ka_conf.value) if ka_conf else 30

                manager = SSHManager()
                success, message = manager.connect(
                    host.hostname,
                    host.port,
                    host.username,
                    password=decrypted_pw,
                    pkey_content=decrypted_key,
                    keepalive=keepalive_val,
                )
                if not success:
                    emit("error", {"message": f"SSH Connect failed: {message}"})
                    return

                ssh_sessions[(user_id, host_id)] = manager
                shell = manager.client.invoke_shell(term="xterm", width=120, height=40)
                active_shells[session_key] = shell
                session_backlogs[session_key] = deque(maxlen=2000)

                # 세션 녹화 시작
                rec_filename = (
                    f"session_{user_id}_{host_id}_{tab_id}_{int(time.time())}.cast"
                )
                rec_path = os.path.join("recordings", rec_filename)
                os.makedirs("recordings", exist_ok=True)
                try:
                    rec_file = open(rec_path, "w", encoding="utf-8")
                    # asciinema v2 header
                    rec_file.write(
                        json.dumps(
                            {
                                "version": 2,
                                "width": 120,
                                "height": 40,
                                "timestamp": int(time.time()),
                                "title": f"Session {user_id} on Host {host_id}",
                            }
                        )
                        + "\n"
                    )
                    recording_sessions[session_key] = {
                        "file": rec_file,
                        "start_time": time.time(),
                        "path": rec_path,
                    }
                except Exception as e:
                    print(f"[REPROD] Failed to start recording: {e}")

                def shell_to_socket(s_key):
                    current_shell = active_shells.get(s_key)
                    if not current_shell:
                        return

                    try:
                        while True:
                            if current_shell.recv_ready():
                                output = current_shell.recv(1024 * 16).decode(
                                    "utf-8", "ignore"
                                )
                                if output:
                                    # 백로그 저장
                                    session_backlogs[s_key].append(output)
                                    # 녹화 파일 저장
                                    if s_key in recording_sessions:
                                        rec_info = recording_sessions[s_key]
                                        elapsed = time.time() - rec_info["start_time"]
                                        rec_info["file"].write(
                                            json.dumps([elapsed, "o", output]) + "\n"
                                        )
                                        rec_info["file"].flush()

                                    # 활성 클라이언트에게만 전송
                                    current_sid = active_sids.get(s_key)
                                    if current_sid:
                                        socketio.emit(
                                            "terminal_output",
                                            {"data": output, "tab_id": s_key[2]},
                                            room=current_sid,
                                        )
                            socketio.sleep(0.01)
                    except Exception:
                        pass
                    finally:
                        active_shells.pop(s_key, None)
                        active_sids.pop(s_key, None)
                        session_backlogs.pop(s_key, None)

                        if s_key in recording_sessions:
                            info = recording_sessions.pop(s_key)
                            info["file"].close()

                            final_path = info["path"]
                            with app.app_context():
                                from core.models import Config, History

                                compress_conf = Config.query.filter_by(
                                    key="rec_auto_compress"
                                ).first()
                                if compress_conf and compress_conf.value == "true":
                                    final_path = compress_recording(final_path)

                                u_id, h_id, t_id = s_key
                                new_hist = History(
                                    host_id=h_id,
                                    user_id=u_id,
                                    action_type="SESSION",
                                    detail=f"Terminal Session ({t_id})",
                                    extra_info=f"Recording saved: {final_path}",
                                    recording_path=final_path,
                                )
                                db.session.add(new_hist)
                                db.session.commit()

                            cleanup_old_recordings(app)

                socketio.start_background_task(shell_to_socket, session_key)
                emit(
                    "terminal_output",
                    {"data": _("Connected to host.") + "\r\n", "tab_id": tab_id},
                )

            except Exception as e:
                emit("error", {"message": f"Internal Error: {str(e)}"})

    @socketio.on("terminal_input")
    def handle_terminal_input(data):
        user_id = session.get("user_id")
        host_id = data.get("host_id")
        tab_id = data.get("tab_id", "default")
        input_data = data.get("data")

        s_key = (user_id, host_id, tab_id)
        shell = active_shells.get(s_key)
        if not shell:
            return

        # 명령어 버퍼링 (Interactive Guard 용)
        if s_key not in terminal_buffers:
            terminal_buffers[s_key] = ""

        if input_data in ("\r", "\n"):
            full_cmd = terminal_buffers[s_key].strip()
            terminal_buffers[s_key] = ""

            if full_cmd:
                # 명령어 제한 확인
                with app.app_context():
                    from core.models import User

                    user = User.query.get(user_id)
                    if user and user.restricted_commands:
                        restricted = [
                            c.strip() for c in user.restricted_commands.split(",")
                        ]
                        for r_cmd in restricted:
                            if r_cmd and r_cmd in full_cmd:
                                # Interactive Guard: 위험 명령어 탐지 시 재확인 요청
                                pending_guards[s_key] = full_cmd
                                emit(
                                    "command_guard_warning",
                                    {
                                        "command": full_cmd,
                                        "tab_id": tab_id,
                                        "message": _(
                                            "Dangerous command detected. Are you sure?"
                                        ),
                                    },
                                )
                                return

                # 위험하지 않은 명령이면 바로 실행
                shell.send(input_data)
                # 히스토리 기록 (간략화)
                with app.app_context():
                    from core.models import History
                    from core.utils import get_client_ip

                    new_hist = History(
                        user_id=user_id,
                        host_id=host_id,
                        action_type="COMMAND",
                        detail=full_cmd,
                        extra_info=f"IP: {get_client_ip(request)}",
                    )
                    db.session.add(new_hist)
                    db.session.commit()
            else:
                shell.send(input_data)
        elif input_data == "\x7f":  # Backspace
            terminal_buffers[s_key] = terminal_buffers[s_key][:-1]
            shell.send(input_data)
        else:
            terminal_buffers[s_key] += input_data
            shell.send(input_data)

    @socketio.on("command_guard_confirm")
    def handle_guard_confirm(data):
        user_id = session.get("user_id")
        host_id = data.get("host_id")
        tab_id = data.get("tab_id", "default")
        confirmed = data.get("confirmed", False)

        s_key = (user_id, host_id, tab_id)
        cmd = pending_guards.pop(s_key, None)
        shell = active_shells.get(s_key)

        if confirmed and cmd and shell:
            shell.send(
                "\r"
            )  # 이미 엔터는 눌려진 상태에서 대기 중이므로 동작 실행을 위해 엔터 전송
            with app.app_context():
                from core.models import History
                from core.utils import get_client_ip

                new_hist = History(
                    user_id=user_id,
                    host_id=host_id,
                    action_type="COMMAND_FORCED",
                    detail=f"[CONFIRMED] {cmd}",
                    extra_info=f"IP: {get_client_ip(request)}",
                )
                db.session.add(new_hist)
                db.session.commit()
        else:
            # 취소 시 버퍼 클리어 안내 등 가능
            emit(
                "terminal_output",
                {
                    "data": "\r\n" + _("Command cancelled by user.") + "\r\n",
                    "tab_id": tab_id,
                },
            )

    @socketio.on("terminal_resize")
    def handle_terminal_resize(data):
        user_id = session.get("user_id")
        host_id = data.get("host_id")
        tab_id = data.get("tab_id", "default")
        cols = data.get("cols")
        rows = data.get("rows")

        s_key = (user_id, host_id, tab_id)
        shell = active_shells.get(s_key)
        if shell:
            try:
                shell.resize_pty(width=cols, height=rows)
            except Exception:
                pass
