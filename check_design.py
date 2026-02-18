import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

url_login = "http://localhost:6001/login"
url_dashboard = "http://localhost:6001/"
admin_password = os.getenv("PTSS_ADMIN_PASSWORD", "admin")

data = {"username": "admin", "password": admin_password}


def check_design_elements(html):
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    # 1. 폰트 로드 확인 (브라우저가 아니라서 실제 렌더링은 못보지만 CSS 링크는 확인 가능)
    fonts = soup.find_all("link", rel="stylesheet")
    if not any("fonts.googleapis.com" in f.get("href", "") for f in fonts):
        issues.append("Google Fonts link might be missing or broken.")

    # 2. 깨진 텍스트/플레이스홀더 확인
    # 'undefined', 'null', 'nan', '{{' 등이 본문에 노출되는지 확인 (템플릿 엔진 미출력 가능성)
    body_text = soup.get_text()
    if "{{" in body_text or "{%" in body_text:
        issues.append("Jinja2 template tags detected in rendered HTML.")

    # 3. 이미지 태그 오류 확인
    imgs = soup.find_all("img")
    for img in imgs:
        if not img.get("src") or img.get("src") == "":
            issues.append(f"Image tag without src found: {img}")

    # 4. 버튼/링크 텍스트 확인 (비어있는지)
    links = soup.find_all("a")
    for link in links:
        if not link.get_text(strip=True) and not link.find(
            "i"
        ):  # i는 아이콘 폰트일 수 있음
            issues.append(f"Empty link text found for: {link.get('href')}")

    return issues


print(f"--- UI/Design Element Check ---")
try:
    session = requests.Session()
    session.post(url_login, data=data, allow_redirects=True)
    response = session.get(url_dashboard)

    if response.status_code == 200:
        issues = check_design_elements(response.text)
        if not issues:
            print("✅ No major design placeholders or template errors found in HTML.")
        else:
            print("⚠️ Potential Design Issues Found:")
            for issue in issues:
                print(f"  - {issue}")

        # 특정 텍스트 매칭 확인
        if "PTSS" not in response.text:
            print("⚠️ Brand name 'PTSS' missing in home page.")

    else:
        print(f"❌ Could not access dashboard. Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
