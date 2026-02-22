import paramiko
import os
from pathlib import Path
from dotenv import load_dotenv


def migrate_remote():
    # Load credentials
    pri_env_path = Path(__file__).parent / "pri.env"
    if pri_env_path.exists():
        load_dotenv(pri_env_path)

    HOST = os.getenv("PTSS_REMOTE_HOST")
    PORT = int(os.getenv("PTSS_REMOTE_PORT", "22"))
    USERNAME = os.getenv("PTSS_REMOTE_USER")
    PASSWORD = os.getenv("PTSS_REMOTE_PASSWORD")
    REMOTE_PATH = os.getenv("PTSS_REMOTE_PATH")

    if not all([HOST, USERNAME, PASSWORD, REMOTE_PATH]):
        print("Error: Remote configuration missing in pri.env")
        return

    print(f"Connecting to remote server {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec

    try:
        ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD)
        print("Connected.")

        # Upload migrate_db.py
        sftp = ssh.open_sftp()
        local_script = Path(__file__).parent / "migrate_db.py"
        remote_script = f"{REMOTE_PATH}/migrate_db.py"
        print(f"Uploading migration script {local_script} to {remote_script}...")
        sftp.put(str(local_script), remote_script)
        sftp.close()

        # Run the script
        run_cmd = f"cd {REMOTE_PATH} && python3 migrate_db.py"
        print(f"Executing: {run_cmd}")
        stdin, stdout, stderr = ssh.exec_command(run_cmd)

        print("Output:", stdout.read().decode().strip())
        print("Error:", stderr.read().decode().strip())

        # Restart server
        print("Restarting PTSS server...")
        kill_cmd = (
            "ps aux | grep ptss.py | grep -v grep | awk '{print $2}' | xargs -r kill -9"
        )
        ssh.exec_command(kill_cmd, get_pty=True)

        start_cmd = f"cd {REMOTE_PATH} && nohup python3 ptss.py > output.log 2>&1 &"
        ssh.exec_command(start_cmd)
        print("Server restarted.")

    except Exception as e:
        print(f"Remote migration failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    migrate_remote()
