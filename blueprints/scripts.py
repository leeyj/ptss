from flask import Blueprint, render_template  # type: ignore
from core.models import Host, Script  # type: ignore
from core.decorators import login_required  # type: ignore

bp = Blueprint("scripts", __name__)


@bp.route("/scripts")
@login_required
def view_scripts():
    scripts = Script.query.all()
    hosts = Host.query.all()
    return render_template("scripts.html", scripts=scripts, hosts=hosts)
