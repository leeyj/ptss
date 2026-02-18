from flask import Blueprint, request, jsonify, session, send_file  # type: ignore
from core.database import db  # type: ignore
from core.models import History, Host, Script, User, Snippet  # type: ignore
from core.state import ssh_sessions, sid_to_host, shell_threads, input_buffers  # type: ignore
import os
import io

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/sftp/list/<int:host_id>", methods=["GET"])
def sftp_list(host_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session.get("user_id")
    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        return jsonify({"error": "Not connected"}), 400

    path = request.args.get("path", ".")
    files, message = manager.list_dir(path)
    if files is not None:
        return jsonify({"files": files})
    return jsonify({"error": message}), 400


@bp.route("/sftp/upload/<int:host_id>", methods=["POST"])
def sftp_upload(host_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session.get("user_id")
    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        return jsonify({"error": "Not connected"}), 400

    file = request.files.get("file")
    remote_path = request.form.get("path", ".")
    full_path = f"{remote_path}/{file.filename}"

    success, message = manager.upload_file(file.stream, full_path)
    if success:
        file.stream.seek(0, 2)
        size = file.stream.tell()
        new_hist = History(
            host_id=host_id,
            user_id=user_id,
            action_type="UPLOAD",
            detail=file.filename,
            extra_info=f"Size: {size}, Path: {full_path}",
        )
        db.session.add(new_hist)
        db.session.commit()
        return jsonify({"message": "Success"})
    return jsonify({"error": message}), 400


@bp.route("/sftp/download/<int:host_id>", methods=["GET"])
def sftp_download(host_id):
    if "user_id" not in session:
        return "Unauthorized", 401

    user_id = session.get("user_id")
    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        return "Not connected", 400

    remote_path = request.args.get("path")
    filename = os.path.basename(remote_path)
    file_obj, message = manager.download_file(remote_path)

    if file_obj:
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)
        new_hist = History(
            host_id=host_id,
            user_id=user_id,
            action_type="DOWNLOAD",
            detail=filename,
            extra_info=f"Size: {size}, Remote: {remote_path}",
        )
        db.session.add(new_hist)
        db.session.commit()
        return send_file(file_obj, as_attachment=True, download_name=filename)
    return f"Error: {message}", 400


@bp.route("/sftp/view_log/<int:host_id>", methods=["GET"])
def sftp_view_log(host_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session.get("user_id")
    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        return jsonify({"error": "Not connected"}), 400
    content, message = manager.read_log(request.args.get("path"))
    if content is not None:
        return jsonify({"content": content})
    return jsonify({"error": message}), 400


@bp.route("/sftp/read_text/<int:host_id>", methods=["GET"])
def sftp_read_text(host_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session.get("user_id")
    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        return jsonify({"error": "Not connected"}), 400

    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Path required"}), 400

    content, message = manager.read_file_content(path)
    if content is not None:
        return jsonify({"content": content, "path": path})
    return jsonify({"error": message}), 400


@bp.route("/sftp/write_text/<int:host_id>", methods=["POST"])
def sftp_write_text(host_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session.get("user_id")
    manager = ssh_sessions.get((user_id, host_id))
    if not manager:
        return jsonify({"error": "Not connected"}), 400

    data = request.json
    path = data.get("path")
    content = data.get("content")

    if not path or content is None:
        return jsonify({"error": "Path and content required"}), 400

    success, message = manager.write_file_content(path, content)

    if success:
        # 히스토리 기록
        new_hist = History(
            host_id=host_id,
            user_id=user_id,
            action_type="EDIT",
            detail=os.path.basename(path),
            extra_info=f"Remote Edit: {path}",
        )
        db.session.add(new_hist)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": message}), 500


@bp.route("/scripts", methods=["GET"])
def list_scripts():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    scripts = Script.query.all()
    return jsonify(
        [{"id": s.id, "name": s.name, "content": s.content} for s in scripts]
    )


@bp.route("/scripts/save", methods=["POST"])
def save_script():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(session["user_id"])
    if not user or user.role != "admin":
        return jsonify({"error": "Admin required"}), 403

    data = request.json
    script_id = data.get("id")
    name = data.get("name")
    content = data.get("content")

    if script_id:
        script = Script.query.get(script_id)
        if script:
            script.name = name
            script.content = content
    else:
        script = Script(name=name, content=content)
        db.session.add(script)

    db.session.commit()
    return jsonify({"success": True, "id": script.id})


@bp.route("/scripts/upload", methods=["POST"])
def upload_script():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith(".sh"):
        content = file.read().decode("utf-8")
        script = Script(name=file.filename, content=content)
        db.session.add(script)
        db.session.commit()
        return jsonify({"success": True, "id": script.id})
    return jsonify({"error": "Only .sh files are allowed"}), 400


@bp.route("/scripts/execute", methods=["POST"])
def execute_script_remote():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    script_id = data.get("script_id")
    host_id = data.get("host_id")

    script = Script.query.get(script_id)
    host = Host.query.get(host_id)
    user_id = session.get("user_id")
    manager = ssh_sessions.get((user_id, host_id))

    if not script or not host or not manager:
        return jsonify({"error": "Invalid script, host, or not connected"}), 400

    # 원격 서버로 스크립트 전송 및 실행
    # 1. 임시 파일로 원격 전송
    remote_path = f"/tmp/ptss_script_{script.id}.sh"
    success, msg = manager.upload_file(
        io.BytesIO(script.content.encode("utf-8")), remote_path
    )

    if not success:
        return jsonify({"error": f"Upload failed: {msg}"}), 500

    # 2. 실행 권한 부여 및 실행
    exec_cmd = f"chmod +x {remote_path} && {remote_path} && rm {remote_path}"
    stdin, stdout, stderr = manager.client.exec_command(exec_cmd)

    output = stdout.read().decode("utf-8", errors="ignore")
    error = stderr.read().decode("utf-8", errors="ignore")

    # 히스토리에 기록
    new_hist = History(
        host_id=host_id,
        user_id=user_id,
        action_type="SCRIPT",
        detail=f"Executed script: {script.name}",
    )
    db.session.add(new_hist)
    db.session.commit()

    return jsonify({"output": output, "error": error})


@bp.route("/scripts/delete/<int:script_id>", methods=["DELETE"])
def delete_script(script_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(session["user_id"])
    if not user or user.role != "admin":
        return jsonify({"error": "Admin required"}), 403

    script = Script.query.get(script_id)
    if script:
        db.session.delete(script)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Script not found"}), 404


@bp.route("/disconnect/<int:host_id>", methods=["POST"])
def disconnect_host(host_id):
    manager = ssh_sessions.pop(host_id, None)
    if manager:
        manager.close()

    to_remove = []
    for sid, m_id in sid_to_host.items():
        if m_id == host_id:
            to_remove.append(sid)

    for sid in to_remove:
        sid_to_host.pop(sid, None)
        shell_threads.pop(sid, None)
        input_buffers.pop(sid, None)  # 버퍼 정리

    return jsonify({"status": "disconnected"})


@bp.route("/snippets", methods=["GET"])
def list_snippets():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    snippets = Snippet.query.order_by(Snippet.category, Snippet.name).all()
    return jsonify(
        [
            {
                "id": s.id,
                "category": s.category,
                "name": s.name,
                "command": s.command,
            }
            for s in snippets
        ]
    )


@bp.route("/snippets/save", methods=["POST"])
def save_snippet():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    snippet_id = data.get("id")
    category = data.get("category", "일반")
    name = data.get("name")
    command = data.get("command")

    if not name or not command:
        return jsonify({"error": "Name and command required"}), 400

    if snippet_id:
        snippet = Snippet.query.get(snippet_id)
        if snippet:
            snippet.category = category
            snippet.name = name
            snippet.command = command
    else:
        snippet = Snippet(category=category, name=name, command=command)
        db.session.add(snippet)

    db.session.commit()
    return jsonify({"success": True, "id": snippet.id})


@bp.route("/snippets/delete/<int:snippet_id>", methods=["DELETE"])
def delete_snippet(snippet_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    snippet = Snippet.query.get(snippet_id)
    if snippet:
        db.session.delete(snippet)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Snippet not found"}), 404
