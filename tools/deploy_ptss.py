import paramiko
import os
import sys
from pathlib import Path

# --- Configuration (User provided) ---
HOST = "192.168.0.20"
PORT = 22
USERNAME = "az001a"
PASSWORD = os.getenv(
    "PTSS_REMOTE_PASSWORD"
)  # 안전을 위해 .env 또는 환경변수에서 로드하세요.
REMOTE_PATH = "/home/az001a/Script/ptss"
LOCAL_PATH = Path("c:/Python312/ptss")  # 로컬 프로젝트 경로

# 업로드 제외 패턴
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".idea",
    ".vscode",
    "tools",
    "uploads",
    ".gemini",
}  # tools는 배포 스크립트라 굳이 올릴 필요 없음
EXCLUDE_FILES = {".DS_Store", "deploy_ptss.py", "*.pyc", "ptss.db", ".env.local"}


def create_sftp_client(host, port, username, password):
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return sftp, transport


import posixpath


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


def execute_remote_command(ssh, command):
    print(f"Executing: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
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
        sftp, transport = create_sftp_client(HOST, PORT, USERNAME, PASSWORD)
        print("Connected via SFTP.")

        # Upload Files
        print(f"Starting full upload from {LOCAL_PATH} to {REMOTE_PATH}...")

        # 전체 디렉토리 재귀 업로드 (EXCLUDE 설정에 따라 ptss.db 등은 제외됨)
        upload_directory(sftp, str(LOCAL_PATH), REMOTE_PATH)

        print("All files uploaded successfully.")

        sftp.close()
        transport.close()

    except Exception as e:
        print(f"SFTP Error: {e}")
        return

    # 2. SSH Connection for Execution
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD)
        print("Connected via SSH.")

        # Dependencies Install (Optional but recommended)
        print("Installing dependencies...")
        execute_remote_command(ssh, f"pip3 install -r {REMOTE_PATH}/requirements.txt")

        # Kill existing process
        print("Killing existing ptss process...")
        # ptss.py 프로세스 죽이기 (grep -v grep은 제외)
        kill_cmd = (
            "ps aux | grep ptss.py | grep -v grep | awk '{print $2}' | xargs -r kill -9"
        )
        execute_remote_command(ssh, kill_cmd)

        # Start new process in background
        print("Starting ptss.py in background...")
        # nohup으로 실행하고 로그를 남김.
        start_cmd = f"cd {REMOTE_PATH} && nohup python3 ptss.py > output.log 2>&1 &"
        execute_remote_command(ssh, start_cmd)

        print("Deployment and restart command sent.")
        ssh.close()

    except Exception as e:
        print(f"SSH Error: {e}")


if __name__ == "__main__":
    main()
