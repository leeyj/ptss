# ☁️ 홈 서버 도메인 & Cloudflare 마이그레이션 통합 가이드

이 문서는 홈 서버의 외부 접속 환경을 아이파이타임 주소(`iptime.org`)에서 정식 도메인(`carls-dev.org`)으로 이전하고, Cloudflare를 통한 HTTPS 보안 및 서브도메인 관리를 설정하는 모든 과정을 담고 있습니다.

---

## 🎫 0. 도메인 구매 및 관리 정보

마치 내 집 주소를 정하는 것과 같은 기본 정보입니다. 1년 뒤 갱신을 잊지 마세요!

*   **구입처:** [Spaceship.com](https://www.spaceship.com)
*   **구매한 도메인:** `carls-dev.org`
*   **구입/갱신일:** 매년 **2월 21일** (차기 갱신일: **2027-02-21**)
*   **예상 비용:** 약 $9.00 ~ $11.00 (환율에 따라 약 1.3~1.5만 원 수준)
*   **갱신 팁:** 만료 1개월 전에 Spaceship에서 알림 메일이 오면 결제 정보를 업데이트하여 자동 갱신되도록 설정하는 것이 안전합니다.

---

## 🚀 1. Cloudflare (DNS/보안/인증서) 설정

전 세계에서 우리 집으로 들어오는 트래픽을 필터링하고 보안 자물쇠(HTTPS)를 채워주는 관제탑입니다.

*   **관리 주소:** [dash.cloudflare.com](https://dash.cloudflare.com)
*   **네임서버(Nameservers) 설정 (Spaceship 관리 페이지 입력용):**
    1.  `maisie.ns.cloudflare.com`
    2.  `rustam.ns.cloudflare.com`

### 🛠️ DNS 레코드 (Records) 설정 핵심
도메인 활성화 후 **[DNS] -> [Records]** 에서 아래 딱 2줄이면 모든 서브도메인이 해결됩니다.

| Type  | Name (이름) | Target/IPv4 (대상) | Proxy status (구름) | 설명 |
|-------|-------------|--------------------|----------------------------|------|
| **A** | `carls-dev.org` (혹은 `@`) | **우리 집 외부 IP** | 🟠 **Proxied** | 메인 도메인을 집 IP로 연결 |
| **CNAME** | `*` (별표 단일 기호) | `carls-dev.org` | 🟠 **Proxied** | `ptss`, `komga` 등 모든 서브도메인 자동 연결 |
| **A** | `air` (에어코믹스 전용) | **우리 집 외부 IP** | ⚪️ **DNS Only** | 구형 앱(HTTP 전용)을 위한 직통 차선 |

---

## 🛡️ 2. HTTPS 보안 설정 (Zero-Config)

홈 서버 내부에 인증서를 깔 필요 없이 Cloudflare 메뉴 클릭 한 번으로 끝냅니다.

1.  **[SSL/TLS] -> [Overview]:** `Flexible` (가변) 모드 선택
2.  **[SSL/TLS] -> [Edge Certificates]:** `Always Use HTTPS` 스위치 **ON** (자동 자물쇠 강제)

---

## 🛠️ 3. Nginx 설정 파일 (`/etc/nginx/sites-available/default`)

홈 서버(Ubuntu)에서 각각의 서브도메인을 내부 포트로 연결해 주는 최종 지도입니다.

```nginx
# ==========================================================
# 0. 보안: 알 수 없는 접근 차단
# ==========================================================
server {
    listen 80 default_server;
    server_name _;
    return 444; 
}

# ==========================================================
# 1. PTSS (터미널/SFTP)
# ==========================================================
server {
    listen 80;
    server_name ptss.carls-dev.org;
    location / {
        proxy_pass http://127.0.0.1:6001; 
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# ==========================================================
# 2. Komga (만화 뷰어 - CDN 캐싱 혜택)
# ==========================================================
server {
    listen 80;
    server_name komga.carls-dev.org;
    client_max_body_size 0;
    location / {
        proxy_pass http://127.0.0.1:5200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# ==========================================================
# 3. Aegis (홈 컨트롤 / 구글 인증)
# ==========================================================
server {
    listen 80;
    server_name aegis.carls-dev.org;
    location / {
        proxy_pass http://127.0.0.1:5700;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# ==========================================================
# 4. Plex (동영상 스트리밍 - 버퍼링 최적화)
# ==========================================================
server {
    listen 80;
    server_name plex.carls-dev.org;
    send_timeout 100m;
    client_max_body_size 0;
    location / {
        proxy_pass http://127.0.0.1:32400; 
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off; # 스트리밍 성능 향상
    }
}
```

---

## 🏃 4. 서버 적용 및 관리

설정 변경 후 반드시 아래 명령어로 Nginx를 새로고침 하세요.

```bash
sudo nginx -t           # 문법 체크
sudo systemctl reload nginx  # 설정 반영
```

> **마무리 팁:** 이제 공유기에는 **80번 포트**와 에어코믹스 전용 **31257 포트** 두 개만 열어두면 됩니다. 22번 SSH 포트는 PTSS가 있으니 안전하게 닫으셔도 좋습니다! 🛡️
