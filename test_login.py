import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = "http://localhost:6001/login"
admin_password = os.getenv("PTSS_ADMIN_PASSWORD", "admin")

data = {"username": "admin", "password": admin_password}

print(f"Testing login for user 'admin' with password from .env...")

try:
    # 1. Login attempt
    session = requests.Session()
    response = session.post(url, data=data, allow_redirects=False)

    print(f"Login Status Code: {response.status_code}")

    if response.status_code == 302 and response.headers.get("Location") == "/":
        print("✅ Login Success: Redirected to /")

        # 2. Access dashboard to verify session
        dash_response = session.get("http://localhost:6001/")
        print(f"Dashboard Access Status: {dash_response.status_code}")

        if dash_response.status_code == 200:
            print("✅ Dashboard Content Loaded Successfully.")
            if "로그아웃" in dash_response.text or "Logout" in dash_response.text:
                print("✅ Confirmed: Session is active (Logout button found).")

            # Simple check for hosts list
            if (
                "host-card" in dash_response.text
                or "등록된 호스트" in dash_response.text
            ):
                print("✅ Found host information on dashboard.")
        else:
            print("❌ Failed to access dashboard even after login redirect.")

    else:
        print("❌ Login Failed.")
        if response.status_code == 200:
            print(
                "Message: Login page returned instead of redirect (Invalid credentials)."
            )

except Exception as e:
    print(f"Error during test: {e}")
