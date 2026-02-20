# Nginx 리버스 프록시 구축 가이드 (서브 디렉토리 방식)

이 문서는 우분투 홈 서버에서 여러 개의 분산된 서비스 포트를 하나의 도메인(`az001a.iptime.org`)의 서브 디렉토리(예: `/ptss`, `/nas`)로 매핑하여 보안과 관리 편의성을 극대화하는 Nginx 리버스 프록시 설정 가이드입니다.

---

## 1. 사전 준비 (방화벽 재정립)
가장 먼저 여러 개로 열려있던 포트들을 모두 닫고, Nginx 전용 외부 접속 포트(80, 443)만 개방합니다.

```bash
# SSH 접속은 끊기면 안 되므로 필수 허용
sudo ufw allow ssh

# Nginx 웹 서버용 포트 열기
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 기존에 수동으로 열어두었던 개별 서비스 포트 닫기 (아래는 예시입니다)
# sudo ufw delete allow 6001/tcp
# sudo ufw delete allow 5000/tcp

# 변경된 ufw 설정 리로드 및 확인
sudo ufw reload
sudo ufw status
```

---

## 2. Nginx 설치 및 기본 설정
Nginx 패키지를 설치하고, 기존의 기본 설정 파일을 백업한 뒤 새로운 규칙을 만듭니다.

```bash
# Nginx 설치
sudo apt update
sudo apt install nginx -y

# 기존 설정 파일 백업
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# 새로운 설정 파일 열기
sudo nano /etc/nginx/sites-available/default
```

---

## 3. Nginx 라우팅 맵 작성
열린 nano 에디터의 내용을 모두 지우고, 아래의 예시를 참고하여 본인의 실제 서비스 포트들로 매핑되도록 코드를 작성합니다.

```nginx
server {
    # 80번 포트 수신 대기
    listen 80;
    
    # 본인의 아이피타임 도메인 입력
    server_name az001a.iptime.org;

    # ==========================================================
    # 1. 서브 디렉토리: PTSS 앱 (/ptss 연결)
    # ==========================================================
    location /ptss/ {
        # 뒤에 반드시 슬래시(/)를 붙여야 내부 경로가 올바르게 전달됩니다
        proxy_pass http://127.0.0.1:6001/;
        
        # 내부 Python(Flask) 앱에 외부 접속 정보를 온전히 전달하기 위한 필수 헤더
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /ptss;

        # WebSocket 및 리소스 로딩 지원
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # ==========================================================
    # 2. 서브 디렉토리: 또 다른 서비스 예시 (/nas 연결)
    # ==========================================================
    location /nas/ {
        proxy_pass http://127.0.0.1:5000/;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /nas;
    }
    
    # ----------------------------------------------------------
    # (필요한 나머지 5개 서비스도 위와 동일한 복붙 패턴으로 포트만 변경하여 추가)
    # ----------------------------------------------------------

    # ==========================================================
    # 루트 접속 시 띄울 메인 페이지 (옵션, 404 차단 등)
    # ==========================================================
    location / {
        # 루트에 연결할 메인 서비스가 있다면 해당 127.0.0.1 포트를 적어줍니다.
        # 없다면 오류(403 등)을 반환하게 설정하여 해커 스캔을 막을 수도 있습니다.
        # return 403; 
        try_files $uri $uri/ =404;
    }
}
```
**`작성 완료 후 저장(Ctrl+O, Enter) -> 빠져나오기(Ctrl+X)`**

---

## 4. Nginx 재시작 및 문법 검사
설정한 파일의 오타나 문법적 오류가 없는지 테스트한 후 서버를 재시작합니다.

```bash
# Nginx 문법 오류 검사 (Syntax OK 가 떠야 합니다)
sudo nginx -t

# Nginx 서비스 재시작하여 적용
sudo systemctl restart nginx
```
> **여기까지 완료하셨다면 HTTP 연결이 성공적으로 라우팅됩니다! (`http://az001a.iptime.org/ptss`)**

---

## 5. SSL 자물쇠(HTTPS) 무료 발급 및 자동화
보다 강력한 보안과 구글 로그인 연동 등의 규격(HTTPS)을 맞추기 위해 Let's Encrypt 무료 인증서를 적용합니다.

```bash
# Certbot 패키지 및 Nginx 플러그인 설치
sudo apt install certbot python3-certbot-nginx -y

# 인증서 발급 신청 (이메일 및 동의, 도메인 입력 필요)
# Nginx 설정 파일에 알아서 HTTPS(443) 코드를 주입해줍니다.
sudo certbot --nginx -d az001a.iptime.org
```

인증서 발급 절차가 모두 완료되면, Certbot이 이전 단계(3단계)에서 만든 Nginx 파일에 알아서 `listen 443 ssl...` 등 암호화 구문들을 추가(수정)해 줍니다. 

> **완료되었습니다! 이제 `https://az001a.iptime.org/ptss` 로 접속해보세요!**

---

## 6. (주의점) 앱 내부 리디렉트 문제 해결
구글 소셜 로그인 파이썬(Flask/FastAPI 등) 앱은 자신이 `/ptss` 라는 경로로 묶여 있고 앞단에 Nginx 프록시가 있다는 사실을 모를 수 있습니다.

**만약 로그인이나, 앱 내의 이미지/CSS 로딩 또는 화면 전환 시 계속 로컬호스트 주소나 루트(`/`) 서버 주소로 잘못 이동(Redirect)한다면 앱 소스 코드를 다음과 같이 한 줄 수정해야 합니다.**

### 🔧 [Python Flask - ptss.py 앱의 경우]
코드 앞 부분(app 초기화 직후)에 프록시 미들웨어 보정 코드를 추가합니다.

```python
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask

app = Flask(__name__)

# Nginx 뒤에 있다는 것을 Flask 내부 라우터에게 명시 /ptss URL 인지
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
```

### 🔧 [구글 클라우드 콘솔 Oauth 세팅]
리다이렉션 승인 주소를 새 HTTPS 기반의 묶음 경로로 꼭 수정해주세요.
* **기존:** `http://...:6001/auth/google/callback`
* **변경:** `https://az001a.iptime.org/ptss/auth/google/callback`

---

## FAQ: `bind() to 0.0.0.0:80 failed` 에러가 뜰 때 (Apache 충돌)

서버에 기존에 설치된 **Apache(아파치)** 웹 서버 등 다른 프로그램이 80번 포트를 점유하고 있다면, Nginx를 시작할 때 충돌이 발생합니다.

### 해결책 1: Nginx 포트 변경 (비권장)
가장 간단히 에러를 없애려면 Nginx의 수신 포트를 수정하면 됩니다.
1. `sudo nano /etc/nginx/sites-available/default` 를 엽니다.
2. `listen 80;` 을 `listen 8080;` (또는 81 등 사용하지 않는 포트)로 변경합니다.
3. `sudo systemctl restart nginx`
* **단점:** 접속할 때 `http://az001a.iptime.org:8080/ptss` 처럼 항상 뒤에 포트를 붙여야 하며, Certbot(무료 HTTPS) 자동 적용이 매우 까다로워집니다.

### 해결책 2: 아파치를 다른 포트로 밀어내고 Nginx가 80번 차지 (추천)
Nginx를 정문(프록시)으로 쓰려면 Nginx가 80과 443번을 가져야 합니다.
1. 아파치 설정 파일 열기: `sudo nano /etc/apache2/ports.conf`
2. `Listen 80` 을 `Listen 8080` 으로 변경 후 저장.
3. 아파치 기본 호스트 설정 열기: `sudo nano /etc/apache2/sites-enabled/000-default.conf`
4. 맨 윗줄 `<VirtualHost *:80>` 을 `<VirtualHost *:8080>` 으로 변경 후 저장.
5. `sudo systemctl restart apache2` -> `sudo systemctl restart nginx`
* **장점:** 아파치는 웹 전용(8080)으로 계속 동작하고, Nginx는 문지기가 되어 HTTPS까지 완벽하게 처리해 줍니다. 아파치 서비스도 앞서 배운 프록시 설정에 `location /apache/ { proxy_pass http://127.0.0.1:8080/; }` 처럼 등록해서 함께 쓸 수 있습니다!
