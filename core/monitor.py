from core.models import Host, Config
from core.state import monitoring_sessions
from core.ssh_manager import SSHManager
from core.crypto import decrypt_data


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
                        except Exception:
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
