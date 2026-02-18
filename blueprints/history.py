from flask import Blueprint, render_template, request, session  # type: ignore
from core.database import db  # type: ignore
from core.models import History, User, Host  # type: ignore
from core.decorators import login_required  # type: ignore

bp = Blueprint("history", __name__)


@bp.route("/history")
@login_required
def view_history():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    current_user_id = session.get("user_id")
    current_role = session.get("role")

    # 필터 파라미터
    user_id = request.args.get("user_id", type=int)
    host_id = request.args.get("host_id", type=int)
    action_type = request.args.get("action_type")
    search_query = request.args.get("q")

    query = History.query

    # 권한 체크: 일반 사용자는 본인 데이터만, 관리자는 전체 데이터 조회 가능
    if current_role != "admin":
        query = query.filter(History.user_id == current_user_id)
        user_id = current_user_id  # 필터 값 고정
    elif user_id:
        query = query.filter(History.user_id == user_id)

    if host_id:
        query = query.filter(History.host_id == host_id)
    if action_type:
        query = query.filter(History.action_type == action_type)
    if search_query:
        query = query.filter(History.detail.ilike(f"%{search_query}%"))

    pagination = query.order_by(History.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    histories = pagination.items

    # 필터용 데이터 (관리자는 전체 목록, 유저는 본인만)
    if current_role == "admin":
        all_users = User.query.all()
    else:
        all_users = User.query.filter_by(id=current_user_id).all()

    all_hosts = Host.query.all()
    # 고유한 활동 유형 목록 추출
    action_types = db.session.query(History.action_type).distinct().all()
    action_types = [at[0] for at in action_types]

    return render_template(
        "history.html",
        histories=histories,
        pagination=pagination,
        per_page=per_page,
        all_users=all_users,
        all_hosts=all_hosts,
        action_types=action_types,
        filters={
            "user_id": user_id,
            "host_id": host_id,
            "action_type": action_type,
            "q": search_query,
        },
        stats_summary={
            "most_active_user": db.session.query(User.username)
            .join(History)
            .group_by(User.username)
            .order_by(db.func.count(History.id).desc())
            .first()[0]
            if db.session.query(User.username).join(History).first()
            else "N/A",
            "most_used_host": db.session.query(Host.name)
            .join(History)
            .group_by(Host.name)
            .order_by(db.func.count(History.id).desc())
            .first()[0]
            if db.session.query(Host.name).join(History).first()
            else "N/A",
            "top_action": db.session.query(History.action_type)
            .group_by(History.action_type)
            .order_by(db.func.count(History.id).desc())
            .first()[0]
            if db.session.query(History.action_type).first()
            else "N/A",
        },
    )
