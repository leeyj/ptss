import sys
import unittest
import urllib.request
import urllib.parse
import http.cookiejar


class BasicSystemTest(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:6001"
    LOGIN_URL = f"{BASE_URL}/auth/login"
    DASHBOARD_URL = f"{BASE_URL}/"

    def setUp(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj)
        )

    def test_01_connectivity(self):
        """Check if the server is reachable based on status root."""
        try:
            with urllib.request.urlopen(self.BASE_URL) as response:
                print(f"Connectivity check: {response.status}")
                # It might redirect to login, which is fine (302 found)
                # But urlopen follows redirects by default usually?
                self.assertIn(response.status, [200, 302])
        except urllib.error.HTTPError as e:
            # specifically for 401/403 which might be expected if auth required
            print(f"Connectivity check failed with HTTP Error: {e.code}")
            # If redirected to login (found=302), urllib might follow and return 200 from login page
            self.fail(f"HTTP Error: {e.code}")
        except urllib.error.URLError as e:
            print(f"Connectivity check failed: {e.reason}")
            self.fail(f"URL Error: {e.reason}")

    def test_02_login(self):
        """Attempt to login with default admin credentials."""
        import os

        # 하드코딩된 비밀번호 대신 환경 변수를 사용하도록 수정
        test_password = os.getenv("TEST_ADMIN_PASSWORD", "your_test_password")
        data = urllib.parse.urlencode(
            {"username": "admin", "password": test_password}
        ).encode()

        req = urllib.request.Request(self.LOGIN_URL, data=data, method="POST")
        try:
            with self.opener.open(req) as response:
                # Check for successful login indicator, e.g., redirect to dashboard or cookie set
                # Flask login usually redirects to 'next' or index upon success
                print(f"Login response code: {response.status}")
                self.assertEqual(response.status, 200)
                content = response.read().decode("utf-8")

                # Simple check for dashboard content
                if "Dashboard" in content or "Logout" in content:
                    print("Login successful: Dashboard found.")
                else:
                    print("Login might have failed or dashboard content not found.")
                    # print(content[:500]) # print start of content for debug
        except urllib.error.HTTPError as e:
            print(f"Login failed with HTTP Error: {e.code}")
            self.fail(f"Login HTTP Error: {e.code}")


if __name__ == "__main__":
    unittest.main()
