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

if not all([HOST, USERNAME]):
    import sys

    print("Error: Remote configuration not complete in pri.env")
    sys.exit(1)


def check_specs():
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec
    try:
        ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD)

        # Execute commands and print raw output
        print("Connecting to:", HOST)

        stdin, stdout, stderr = ssh.exec_command("lscpu | grep 'Model name'")
        print("\n[CPU]")
        print(stdout.read().decode().strip())

        stdin, stdout, stderr = ssh.exec_command("free -h")
        print("\n[Memory]")
        print(stdout.read().decode().strip())

        stdin, stdout, stderr = ssh.exec_command("df -h /")
        print("\n[Disk]")
        print(stdout.read().decode().strip())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_specs()
