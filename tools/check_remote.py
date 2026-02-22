import paramiko
import os
from pathlib import Path
from dotenv import load_dotenv

pri_env_path = Path(__file__).parent / "pri.env"
load_dotenv(pri_env_path)

HOST = os.getenv("PTSS_REMOTE_HOST")
PORT = int(os.getenv("PTSS_REMOTE_PORT", 22))
USERNAME = os.getenv("PTSS_REMOTE_USER")
PASSWORD = os.getenv("PTSS_REMOTE_PASSWORD")
REMOTE_PATH = os.getenv("PTSS_REMOTE_PATH")

if not all([HOST, USERNAME, REMOTE_PATH]):
    import sys

    print("Error: Remote configuration not complete in pri.env")
    sys.exit(1)


def check():
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD)

    stdin, stdout, stderr = ssh.exec_command("ps aux | grep ptss.py | grep -v grep")
    print("--- Processes ---")
    print(stdout.read().decode())

    stdin, stdout, stderr = ssh.exec_command(f"tail -n 20 {REMOTE_PATH}/output.log")
    print("--- Log Error/Output ---")
    print(stdout.read().decode())

    ssh.close()


if __name__ == "__main__":
    check()
