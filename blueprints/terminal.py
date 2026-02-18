from flask import Blueprint, render_template, request, session  # type: ignore
from core.models import Host, Config  # type: ignore
from core.decorators import login_required  # type: ignore
from core.state import ssh_sessions  # type: ignore
from core.ssh_manager import SSHManager  # type: ignore
from core.crypto import decrypt_data  # type: ignore

bp = Blueprint("terminal", __name__)


@bp.route("/connect/<int:host_id>")
@login_required
def connect(host_id):
    host = Host.query.get_or_404(host_id)
    user_id = session.get("user_id")
    user_role = session.get("role")

    # 일반 사용자의 root 계정 접속 제한
    if user_role != "admin" and host.username == "root":
        return "일반 사용자는 root 계정으로 접속할 수 없습니다. (관리자 권한 필요)", 403

    # 이미 세션이 있는지 확인
    manager = ssh_sessions.get((user_id, host_id))
    if (
        manager
        and manager.client
        and manager.client.get_transport()
        and manager.client.get_transport().is_active()
    ):
        log_mode = Config.query.filter_by(key="log_view_mode").first()
        mode_val = log_mode.value if log_mode else "preview"
        sftp_sort = Config.query.filter_by(key="sftp_sort_by").first()
        sort_val = sftp_sort.value if sftp_sort else "name"
        retention = Config.query.filter_by(key="session_retention").first()
        ret_val = retention.value if retention else "maintain"

        return render_template(
            "console.html",
            host=host,
            log_view_mode=mode_val,
            sftp_sort_by=sort_val,
            session_retention=ret_val,
        )

    # 신규 연결
    decrypted_pw = decrypt_data(host.password) if host.password else None
    decrypted_key = decrypt_data(host.encrypted_key) if host.encrypted_key else None

    # Keepalive 설정 로드
    ka_conf = Config.query.filter_by(key="ssh_keepalive_interval").first()
    keepalive_val = int(ka_conf.value) if ka_conf else 0

    manager = SSHManager()
    success, message = manager.connect(
        host.hostname,
        host.port,
        host.username,
        password=decrypted_pw,
        pkey_content=decrypted_key,
        keepalive=keepalive_val,
    )

    if success:
        ssh_sessions[(user_id, host_id)] = manager
        log_mode = Config.query.filter_by(key="log_view_mode").first()
        mode_val = log_mode.value if log_mode else "preview"
        sftp_sort = Config.query.filter_by(key="sftp_sort_by").first()
        sort_val = sftp_sort.value if sftp_sort else "name"
        retention = Config.query.filter_by(key="session_retention").first()
        ret_val = retention.value if retention else "maintain"

        return render_template(
            "console.html",
            host=host,
            log_view_mode=mode_val,
            sftp_sort_by=sort_val,
            session_retention=ret_val,
        )
    else:
        return render_template(
            "error.html",
            title="연결 실패",
            message=f"서버 접속에 실패했습니다: {message}",
            back_url="/",
        )


@bp.route("/log_view/<int:host_id>")
@login_required
def log_view_standalone(host_id):
    host = Host.query.get_or_404(host_id)
    path = request.args.get("path")
    log_mode = Config.query.filter_by(key="log_view_mode").first()
    mode_val = log_mode.value if log_mode else "preview"
    return render_template(
        "log_view.html", host=host, path=path, log_view_mode=mode_val
    )
