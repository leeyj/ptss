import os
import logging
from collections import deque
from flask import request, session, current_app
from flask_socketio import emit, join_room, leave_room
from core.database import db
from core.models import Host, History, Config, User
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
)
from core.ssh_manager import SSHManager
from core.crypto import decrypt_data
from core.utils import get_client_ip
from core.i18n import _


def connect_and_monitor(host_id, app):
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


def stats_monitoring_task(socketio, app):
    """모니터링 세션이 활성화된 호스트만 상태 수집"""
    print("Dashboard Monitoring Task Active.")
    while True:
        with app.app_context():
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
                watchers.discard(sid)
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

        infos = sid_to_info.pop(sid, [])
        if infos:
            for info in infos:
                user_id, host_id, tab_id = info
                session_key = (user_id, host_id, tab_id)
                active_sids.pop(session_key, None)
                active_shells.pop(session_key, None)

                with app.app_context():
                    retention = Config.query.filter_by(key="session_retention").first()
                    if retention and retention.value == "terminate":
                        still_has_tabs = any(
                            k[0] == user_id and k[1] == host_id
                            for k in active_sids.keys()
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
                            print(
                                "[Policy] SSH session maintained (Remaining tabs exist)"
                            )

    @socketio.on("start_monitoring")
    def handle_start_monitoring(data):
        host_id = data.get("host_id")
        sid = request.sid
        if not host_id:
            return

        if host_id not in host_watchers:
            host_watchers[host_id] = set()
        host_watchers[host_id].add(sid)
        join_room(f"monitoring_{host_id}")

        if host_id in monitoring_sessions:
            emit("monitoring_started", {"host_id": host_id, "status": "active"})
            socketio.emit(
                "host_status_change",
                {"host_id": host_id, "status": "online"},
                room=f"monitoring_{host_id}",
            )
            return

        success, msg = connect_and_monitor(host_id, app)
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

        if host_id in host_watchers:
            host_watchers[host_id].discard(sid)
            leave_room(f"monitoring_{host_id}")
            if not host_watchers[host_id]:
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

        if sid not in sid_to_info:
            sid_to_info[sid] = []
        if (user_id, host_id, tab_id) not in sid_to_info[sid]:
            sid_to_info[sid].append((user_id, host_id, tab_id))

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
                emit(
                    "terminal_output",
                    {"data": "".join(list(backlog)), "tab_id": tab_id},
                )
            emit(
                "terminal_output",
                {"data": f"\r\n{_('terminal_restore_msg')}\r\n", "tab_id": tab_id},
            )
        else:
            shell = manager.get_shell()
            if not shell:
                emit(
                    "terminal_output",
                    {
                        "data": f"\r\n{_('terminal_start_fail_msg')}\r\n",
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
                {
                    "data": f"\r\n{_('terminal_connect_success_msg')}\r\n",
                    "tab_id": tab_id,
                },
            )

    @socketio.on("terminal_input")
    def handle_terminal_input(data):
        sid = request.sid
        tab_id = data.get("tab_id", "default")
        infos = sid_to_info.get(sid, [])
        if infos:
            user_id, host_id, _ = infos[0]
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
                                            "data": f"\r\n\x1b[31m{_('terminal_restricted_msg').format(keyword=keyword)}\x1b[0m\r\n",
                                            "tab_id": tab_id,
                                        },
                                        room=sid,
                                    )
                                    new_hist = History(
                                        host_id=host_id,
                                        user_id=user_id,
                                        action_type="BLOCKED",
                                        detail=full_cmd,
                                        extra_info=f"IP: {get_client_ip()}",
                                    )
                                    db.session.add(new_hist)
                                    db.session.commit()
                                    return
                    terminal_buffers[session_key] = ""
                elif char in ["\x7f", "\x08"]:
                    if len(terminal_buffers[session_key]) > 0:
                        terminal_buffers[session_key] = terminal_buffers[session_key][
                            :-1
                        ]
                elif isinstance(char, str) and ord(char) >= 32:
                    terminal_buffers[session_key] += char

        if shell:
            shell.send(input_data)

    @socketio.on("terminal_command")
    def handle_terminal_command(data):
        sid = request.sid
        cmd = data.get("command", "").strip()
        host_id = sid_to_host.get(sid)
        infos = sid_to_info.get(sid, [])
        user_id = infos[0][0] if infos else session.get("user_id")

        if host_id and cmd:
            with app.app_context():
                new_hist = History(
                    host_id=host_id,
                    user_id=user_id,
                    action_type="COMMAND",
                    detail=cmd,
                    extra_info=f"IP: {get_client_ip()}",
                )
                db.session.add(new_hist)
                db.session.commit()

    @socketio.on("terminal_resize")
    def handle_terminal_resize(data):
        sid = request.sid
        tab_id = data.get("tab_id", "default")
        infos = sid_to_info.get(sid, [])
        if infos:
            user_id, host_id, _ = infos[0]
        else:
            user_id = session.get("user_id")
            host_id = sid_to_host.get(sid)

        if host_id and user_id:
            session_key = (user_id, host_id, tab_id)
            shell = active_shells.get(session_key)
            if shell:
                try:
                    shell.resize_pty(
                        width=int(data.get("cols", 80)),
                        height=int(data.get("rows", 24)),
                    )
                except Exception as e:
                    print(f"PTY Resize Error: {e}")
