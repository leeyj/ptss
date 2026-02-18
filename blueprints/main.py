from flask import Blueprint, render_template, request, redirect, url_for  # type: ignore
from core.database import db  # type: ignore
from core.models import Host, Config  # type: ignore
from core.decorators import login_required  # type: ignore
from core.state import ssh_sessions  # type: ignore

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def index():
    hosts = Host.query.all()
    # 활성화된 호스트 ID 목록 전달 (프론트엔드 모니터링용)
    active_hosts = [h_id for (u_id, h_id) in ssh_sessions.keys()]
    return render_template("index.html", hosts=hosts, active_hosts=active_hosts)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def view_settings():
    if request.method == "POST":
        log_mode = request.form.get("log_view_mode")
        sftp_sort = request.form.get("sftp_sort_by")
        keepalive = request.form.get("ssh_keepalive_interval", "0")
        retention = request.form.get("session_retention", "maintain")

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

        # SSH Keepalive update
        conf_ka = Config.query.filter_by(key="ssh_keepalive_interval").first()
        if not conf_ka:
            conf_ka = Config(key="ssh_keepalive_interval", value=keepalive)
            db.session.add(conf_ka)
        else:
            conf_ka.value = keepalive

        # Session Retention update
        conf_ret = Config.query.filter_by(key="session_retention").first()
        if not conf_ret:
            conf_ret = Config(key="session_retention", value=retention)
            db.session.add(conf_ret)
        else:
            conf_ret.value = retention

        db.session.commit()
        return redirect(url_for("main.view_settings"))

    log_mode = Config.query.filter_by(key="log_view_mode").first()
    mode_val = log_mode.value if log_mode else "preview"

    sftp_sort = Config.query.filter_by(key="sftp_sort_by").first()
    sort_val = sftp_sort.value if sftp_sort else "name"

    keepalive = Config.query.filter_by(key="ssh_keepalive_interval").first()
    ka_val = keepalive.value if keepalive else "0"

    return render_template(
        "settings.html",
        log_view_mode=mode_val,
        sftp_sort_by=sort_val,
        ssh_keepalive_interval=ka_val,
    )
