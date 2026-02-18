from flask import Blueprint, render_template, request, redirect, url_for, session, flash  # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash  # type: ignore
from core.database import db  # type: ignore
from core.models import User, Config, History  # type: ignore
from core.decorators import login_required  # type: ignore

bp = Blueprint("auth", __name__)


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    if User.query.first():
        flash("이미 초기 설정이 완료되었습니다.")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        master_key = request.form.get("master_key")

        # 관리자 생성
        new_admin = User(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin",
            restricted_commands=None,
        )
        db.session.add(new_admin)

        # 마스터 키 업데이트 (DB 설정값에 저장)
        conf_key = Config.query.filter_by(key="PTSS_MASTER_KEY").first()
        if not conf_key:
            conf_key = Config(key="PTSS_MASTER_KEY", value=master_key)
            db.session.add(conf_key)
        else:
            conf_key.value = master_key

        db.session.commit()
        flash("초기 설정이 완료되었습니다. 로그인을 진행해주세요.")
        return redirect(url_for("auth.login"))

    # 기본 생성된 키 제공 (UI에서 편집 가능하게)
    from cryptography.fernet import Fernet  # type: ignore

    temp_key = Fernet.generate_key().decode()
    return render_template("setup.html", default_key=temp_key)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role

            # 감사 로그: 로그인 기록
            new_hist = History(
                user_id=user.id,
                action_type="LOGIN",
                detail=f"User {user.username} logged in",
                extra_info=f"IP: {request.remote_addr}",
            )
            db.session.add(new_hist)
            db.session.commit()

            return redirect(url_for("main.index"))

        # 감사 로그: 로그인 실패 기록
        new_hist = History(
            action_type="AUTH_FAIL",
            detail=f"Failed login attempt for username: {username}",
            extra_info=f"IP: {request.remote_addr}",
        )
        db.session.add(new_hist)
        db.session.commit()

        flash("로그인 정보가 올바르지 않습니다.")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    u_id = session.get("user_id")
    if u_id:
        # 감사 로그: 로그아웃 기록
        new_hist = History(
            user_id=u_id,
            action_type="LOGOUT",
            detail=f"User {session.get('username')} logged out",
        )
        db.session.add(new_hist)
        db.session.commit()

    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("role", None)
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        new_password = request.form.get("password")
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("비밀번호가 성공적으로 변경되었습니다.")
            return redirect(url_for("auth.profile"))
    return render_template("profile.html", user=user)
