import paramiko
import os
import sys

import posixpath
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# tools/pri.env 로드 시도
pri_env_path = Path(__file__).parent / "pri.env"
if pri_env_path.exists():
    load_dotenv(pri_env_path)

# --- Configuration (Environment Variables with Fallbacks) ---
HOST = os.getenv("PTSS_REMOTE_HOST")
PORT = int(os.getenv("PTSS_REMOTE_PORT", 22))
USERNAME = os.getenv("PTSS_REMOTE_USER")
REMOTE_PATH = os.getenv("PTSS_REMOTE_PATH")
PASSWORD = os.getenv("PTSS_REMOTE_PASSWORD")

if not all([HOST, USERNAME, REMOTE_PATH]):
    print(
        "Error: PTSS_REMOTE_HOST, PTSS_REMOTE_USER, or PTSS_REMOTE_PATH not set in pri.env or environment."
    )
    sys.exit(1)


if not PASSWORD:
    try:
        PASSWORD = getpass.getpass(f"Enter password for {USERNAME}@{HOST}: ")
    except Exception:
        PASSWORD = None

LOCAL_PATH = Path("c:/Python312/ptss")  # 로컬 프로젝트 경로


# 업로드 제외 패턴
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    ".venv_test",
    ".idea",
    ".vscode",
    "tools",
    "uploads",
    ".gemini",
    "node_modules",
}  # tools는 배포 스크립트라 굳이 올릴 필요 없음
EXCLUDE_FILES = {
    ".DS_Store",
    "deploy_ptss.py",
    "*.pyc",
    "ptss.db",
    ".env.local",
    "pri.env",  # 개인용 배포 키 파일 제외
}


def create_sftp_client(host, port, username, password):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec
    ssh.connect(
        host,
        port=port,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
    )
    sftp = ssh.open_sftp()
    return sftp, ssh


def upload_directory(sftp, local_dir, remote_dir):
    """
    os.walk를 사용하여 로컬 디렉토리를 순회하며 원격 서버에 업로드합니다.
    """
    local_dir = str(local_dir)
    exclude_dirs_set = set(EXCLUDE_DIRS)
    exclude_files_set = set(EXCLUDE_FILES)

    # Walk through the directory structure
    for root, dirs, files in os.walk(local_dir):
        # 1. 디렉토리 필터링 (in-place modification for os.walk)
        dirs[:] = [d for d in dirs if d not in exclude_dirs_set]

        # 2. 현재 디렉토리의 상대 경로 계산
        rel_path = os.path.relpath(root, local_dir)
        if rel_path == ".":
            current_remote_dir = remote_dir
        else:
            # 윈도우 경로 구분자(\)를 리눅스(/)로 변환
            rel_path_linux = rel_path.replace(os.sep, "/")
            current_remote_dir = posixpath.join(remote_dir, rel_path_linux)

        # 3. 원격 디렉토리 생성 (없으면)
        try:
            sftp.stat(current_remote_dir)
        except IOError:
            # print(f"[MKDIR] {current_remote_dir}")
            try:
                sftp.mkdir(current_remote_dir)
            except IOError:
                pass  # 부모가 없어서 실패할 수 있음 (순서상 부모가 먼저 만들어지므로 드문 경우)

        # 4. 파일 업로드
        for file in files:
            if file in exclude_files_set:
                continue
            if any(
                file.endswith(ext.replace("*", ""))
                for ext in exclude_files_set
                if "*" in ext
            ):
                continue

            local_file_path = os.path.join(root, file)
            remote_file_path = posixpath.join(current_remote_dir, file)

            try:
                print(f"[UPLOAD] {local_file_path} -> {remote_file_path}")
                sftp.put(local_file_path, remote_file_path)
            except Exception as e:
                print(f"[ERROR] Failed to upload {file}: {e}")


def execute_remote_command(ssh, command, wait=True):
    print(f"Executing: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)

    if not wait:
        print("[INFO] Background command started (no wait).")
        return 0

    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()

    if output:
        print(f"[OUT] {output}")
    if error:
        print(f"[ERR] {error}")

    return exit_status


def main():
    print(f"Connecting to {HOST}...")

    # 1. SFTP Connection for Upload
    try:
        sftp, ssh = create_sftp_client(HOST, PORT, USERNAME, PASSWORD)
        print("Connected via SSH/SFTP.")

        # Upload Files
        print(f"Starting initial upload from {LOCAL_PATH} to {REMOTE_PATH}...")
        upload_directory(sftp, str(LOCAL_PATH), REMOTE_PATH)
        print("Initial files uploaded.")

        # 2. Cleanup & Execution
        print("Killing existing ptss process...")
        kill_cmd = (
            "ps aux | grep ptss.py | grep -v grep | awk '{print $2}' | xargs -r kill -9"
        )
        execute_remote_command(ssh, kill_cmd)

        # [중요] 데이터 백업 (DB, .env, uploads)
        print("Backing up sensitive data (DB, .env, uploads)...")
        backup_dir = "/tmp/ptss_deploy_backup"
        execute_remote_command(ssh, f"rm -rf {backup_dir} && mkdir -p {backup_dir}")

        # 주요 파일 백업 (파일이 없을 수도 있으므로 오류 무시)
        execute_remote_command(
            ssh, f"cp {REMOTE_PATH}/ptss.db {backup_dir}/ 2>/dev/null || true"
        )
        execute_remote_command(
            ssh, f"cp {REMOTE_PATH}/.env {backup_dir}/ 2>/dev/null || true"
        )
        execute_remote_command(
            ssh, f"cp -r {REMOTE_PATH}/uploads {backup_dir}/ 2>/dev/null || true"
        )

        print("Clearing remote directory...")
        clear_cmd = f"rm -rf {REMOTE_PATH} && mkdir -p {REMOTE_PATH}"
        execute_remote_command(ssh, clear_cmd)

        # 3. Final Upload (after clearing)
        print(f"Starting full upload to fresh directory...")
        upload_directory(sftp, str(LOCAL_PATH), REMOTE_PATH)
        print("All files uploaded successfully.")

        # [중요] 데이터 복원
        print("Restoring sensitive data...")
        execute_remote_command(
            ssh, f"cp {backup_dir}/ptss.db {REMOTE_PATH}/ 2>/dev/null || true"
        )
        execute_remote_command(
            ssh, f"cp {backup_dir}/.env {REMOTE_PATH}/ 2>/dev/null || true"
        )
        execute_remote_command(
            ssh, f"cp -r {backup_dir}/uploads {REMOTE_PATH}/ 2>/dev/null || true"
        )

        # 4. Restart
        print("Installing dependencies...")
        execute_remote_command(ssh, f"pip3 install -r {REMOTE_PATH}/requirements.txt")

        print("Starting ptss.py in background...")
        start_cmd = f"cd {REMOTE_PATH} && nohup python3 ptss.py > output.log 2>&1 &"
        execute_remote_command(ssh, start_cmd, wait=False)

        print("Deployment and restart complete.")
        sftp.close()
        ssh.close()

    except Exception as e:
        print(f"Deployment Error: {e}")
        import traceback

        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
