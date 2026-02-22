import paramiko
import os
import time
from dotenv import load_dotenv

from pathlib import Path

load_dotenv(Path(__file__).parent / "pri.env")
HOST = os.getenv("PTSS_REMOTE_HOST")
USERNAME = os.getenv("PTSS_REMOTE_USER")
PASSWORD = os.getenv("PTSS_REMOTE_PASSWORD")
REMOTE_PATH = os.getenv("PTSS_REMOTE_PATH")

if not all([HOST, USERNAME, REMOTE_PATH]):
    import sys

    print("Error: Remote configuration not complete in pri.env")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.load_system_host_keys()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec
ssh.connect(HOST, username=USERNAME, password=PASSWORD)

sftp = ssh.open_sftp()

print("Uploading specific patch files...")
try:
    sftp.put("templates/layout.html", f"{REMOTE_PATH}/templates/layout.html")
    sftp.put(
        "static/js/console_sftp.js",
        f"{REMOTE_PATH}/static/js/console_sftp.js",
    )
    sftp.put(
        "static/js/console_main.js",
        f"{REMOTE_PATH}/static/js/console_main.js",
    )
except Exception as e:
    print("Upload error:", e)

print("Restarting PTSS server on remote...")
cmd = "ps aux | grep ptss.py | grep -v grep | awk '{print $2}' | xargs -r kill -9"
ssh.exec_command(cmd)
time.sleep(2)
start_cmd = f"cd {REMOTE_PATH} && nohup python3 ptss.py > output.log 2>&1 < /dev/null &"
ssh.exec_command(start_cmd)
time.sleep(2)

print("Checking log...")
stdin, stdout, stderr = ssh.exec_command(f"tail -n 10 {REMOTE_PATH}/output.log")
print(stdout.read().decode())


print("Patch applied successfully.")
sftp.close()
ssh.close()
