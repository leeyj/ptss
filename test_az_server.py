import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
URL_BASE = "http://localhost:6001"
ADMIN_USER = "admin"
ADMIN_PASS = os.getenv("PTSS_ADMIN_PASSWORD", "admin")


def run_az_test():
    session = requests.Session()

    # 1. Login
    print("Logging in...")
    login_resp = session.post(
        f"{URL_BASE}/login", data={"username": ADMIN_USER, "password": ADMIN_PASS}
    )
    if login_resp.status_code not in [200, 302]:
        print("❌ Login failed.")
        return

    # 2. Find AZ host ID
    print("Fetching host list...")
    dash_resp = session.get(f"{URL_BASE}/")
    # Simple search for host id by checking the dashboard text for 'az'
    # Normally we'd parse this, but let's try to find the host link like /connect/1
    # We can also check the DB indirectly if we had a direct API, but let's use the dashboard.

    if "az" not in dash_resp.text.lower():
        print("❌ 'az' server not found on dashboard.")
        return

    # 3. Connection Test (Internal API check if available)
    # The app uses /connect/<id> to initiate SSH.
    # Let's try to guess the ID or find it.
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(dash_resp.text, "html.parser")
    az_link = None
    for link in soup.find_all("a"):
        href = link.get("href", "")
        if "/connect/" in href and "az" in str(link.parent.parent).lower():
            az_link = href
            break

    if not az_link:
        print("❌ Could not extract connection link for 'az' server.")
        return

    host_id = az_link.split("/")[-1]
    print(f"✅ Found AZ host ID: {host_id}")

    # 4. SSH Connection & Basic Command via API
    # The app uses Socket.io for terminal, but has some Blueprint APIs
    print(f"Testing SSH connection to host {host_id}...")
    conn_resp = session.get(f"{URL_BASE}/connect/{host_id}")
    if conn_resp.status_code == 200:
        print("✅ SSH Connection Manager initialized.")
    else:
        print(f"❌ SSH Connection failed. Status: {conn_resp.status_code}")
        print(conn_resp.text[:200])
        return

    # 5. SFTP Test - List Directory
    print("Testing SFTP - Listing remote directory...")
    # Blueprint api usually at /api/sftp/list/<host_id>?path=.
    sftp_resp = session.get(f"{URL_BASE}/api/sftp/list/{host_id}?path=.")
    if sftp_resp.status_code == 200:
        files = sftp_resp.json()
        print(f"✅ SFTP List Success. Found {len(files)} items.")
    else:
        print(f"❌ SFTP List failed. Status: {sftp_resp.status_code}")
        return

    # 6. SFTP Test - Upload/Download
    print("Testing SFTP - Uploading test file...")
    test_file_content = "PTSS Test Payload"
    files = {"file": ("ptss_test.txt", test_file_content)}
    up_resp = session.post(
        f"{URL_BASE}/api/sftp/upload/{host_id}", data={"path": "."}, files=files
    )
    if up_resp.status_code == 200:
        print("✅ SFTP Upload Success.")

        # Verify and Download
        print("Testing SFTP - Downloading file back...")
        down_resp = session.get(
            f"{URL_BASE}/api/sftp/download/{host_id}?path=./ptss_test.txt"
        )
        if down_resp.status_code == 200 and down_resp.text == test_file_content:
            print("✅ SFTP Download & Data Integrity Verified.")
        else:
            print(
                f"❌ SFTP Download failed or content mismatch. Status: {down_resp.status_code}"
            )
    else:
        print(f"❌ SFTP Upload failed. Status: {up_resp.status_code}")


if __name__ == "__main__":
    run_az_test()
