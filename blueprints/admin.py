from flask import (  # type: ignore
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from werkzeug.security import generate_password_hash  # type: ignore
from core.database import db  # type: ignore
from core.models import User, Host, Config  # type: ignore
from core.decorators import admin_required  # type: ignore
from core.ssh_manager import SSHManager  # type: ignore
from core.crypto import encrypt_data, decrypt_data  # type: ignore

bp = Blueprint("admin", __name__)


@bp.route("/admin/users", methods=["GET", "POST"])
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
        return redirect(url_for("admin.manage_users"))

    users = User.query.all()
    return render_template("users.html", users=users)


@bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("자기 자신은 삭제할 수 없습니다.")
        return redirect(url_for("admin.manage_users"))

    user = User.query.get(user_id)
    if user:
        if user.username == "admin":
            flash("기본 관리자 계정은 삭제할 수 없습니다.")
        else:
            db.session.delete(user)
            db.session.commit()
            flash("사용자가 삭제되었습니다.")
    return redirect(url_for("admin.manage_users"))


@bp.route("/admin/users/update_restrictions/<int:user_id>", methods=["POST"])
@admin_required
def update_user_restrictions(user_id):
    user = User.query.get_or_404(user_id)
    restricted = request.form.get("restricted_commands", "")
    user.restricted_commands = restricted
    db.session.commit()
    flash(f"'{user.username}' 사용자의 명령어 제한이 업데이트되었습니다.")
    return redirect(url_for("admin.manage_users"))


@bp.route("/host/add", methods=["POST"])
@admin_required
def add_host():
    name = request.form["name"]
    hostname = request.form["hostname"]
    port = int(request.form["port"])
    username = request.form["username"]
    auth_type = request.form["auth_type"]
    password = request.form.get("password")
    key_content = request.form.get("key_content")
    key_file = request.files.get("key_file")

    if key_file and key_file.filename != "":
        key_content = key_file.read().decode("utf-8")

    # 1. 테스트 연결 수행
    ka_conf = Config.query.filter_by(key="ssh_keepalive_interval").first()
    keepalive_val = int(ka_conf.value) if ka_conf else 0

    manager = SSHManager()
    success, message = manager.connect(
        hostname,
        port,
        username,
        password=password,
        pkey_content=key_content,
        keepalive=keepalive_val,
    )
    manager.close()

    if not success:
        return jsonify({"success": False, "error": f"연결 테스트 실패: {message}"}), 400

    # 2. 성공 시 암호화하여 저장
    new_host = Host(
        name=name,
        hostname=hostname,
        port=port,
        username=username,
        auth_type=auth_type,
        password=encrypt_data(password) if password else None,
        encrypted_key=encrypt_data(key_content) if key_content else None,
    )
    db.session.add(new_host)
    db.session.commit()

    return jsonify({"success": True, "message": f"호스트 {name}이(가) 추가되었습니다."})


@bp.route("/host/delete/<int:host_id>", methods=["POST"])
@admin_required
def delete_host(host_id):
    host = Host.query.get_or_404(host_id)
    db.session.delete(host)
    db.session.commit()
    flash(f"호스트 {host.name}이(가) 삭제되었습니다.")
    return redirect(url_for("main.index"))
