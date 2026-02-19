# ⚡ PTSS: Premium Terminal & SFTP System

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Personal--Free-green.svg)](LICENSE)

**PTSS**는 웹 브라우저 하나로 여러 서버를 동시에 관리할 수 있는 가볍고 강력한 **웹 기반 SSH 클라이언트 & SFTP 매니저**입니다. 복잡한 설치 없이 실시간 터미널 제어와 파일 관리를 프리미엄 UI 환경에서 경험하세요.

---

## ✨ 주요 특징 (Key Features)

### 🖥️ 고성능 웹 터미널
*   **xterm.js 기반**: 실제 로컬 터미널과 동일한 수준의 색상 표현과 반응 속도.
*   **멀티 탭 지원**: 여러 서버 세션을 탭 형태로 동시에 전환하며 작업 가능.
*   **세션 유지(Persistence)**: 브라우저를 닫거나 새로고침해도 작업 내용이 서버에 보관되어 즉시 복구.
*   **테마 커스터마이징**: Monokai, Dracula 등 유명 테마와 폰트 크기/종류 자유 조절.

### 📁 통합 SFTP 파일 매니저
*   **GUI 기반 관리**: 드래그 앤 드롭 업로드, 클릭 한 번으로 다운로드.
*   **실시간 로그 뷰어**: 서버 내 로그 파일을 브라우저에서 즉시 미리보기.
*   **권한 및 소유자 확인**: 파일별 상세 속성 확인 및 리눅스 친화적 인터페이스.

### 🚀 생산성 도구
*   **명령어 스니펫(Snippet)**: 자주 쓰는 복잡한 명령어를 저장해두고 클릭 한 번으로 실행.
*   **자동화 스크립트**: 반복되는 일련의 작업을 스크립트로 관리 및 즉시 배포.
*   **대시보드 모니터링**: 등록된 서버들의 CPU, RAM, 디스크 상태를 실시간 차트로 확인.

---

## 🛠️ 설치 및 실행 (Setup & Run)

### 2. 초기 설정 (Setup)
애플리케이션 실행 전, 루트 디렉토리에 `.env` 파일을 생성하고 필수 보안 키를 설정해야 합니다.

```env
# .env 파일 예시
PTSS_SECRET_KEY=your_unique_session_key  # 세션 유지용 (필수)
DATABASE_URL=sqlite:///ptss.db           # DB 경로 (선택)
```

이후 애플리케이션을 실행하면 `/setup` 페이지로 자동 리디렉션되어 다음 설정을 진행합니다:
*   **관리자 계정**: 시스템 로그인을 위한 ID/PW 생성.
*   **마스터 키**: SSH 접속 정보 암호화용 키 설정 (DB에 저장됨).

### 3. 시작하기(테스트)
```bash
python ptss.py
```
접속 주소: `http://localhost:6001`

---


### 4. 시작하기(실 사용)
```bash
python ptss.py
```
*   ptss.py의 debug=True 를 False로 변경 후 실행
*   상황에 따라 포트를 변경해야 할 수 있음
---

### 5. 초기화
---
*   ptss.db 삭제 후 서비스 재시작
---




## 📜 라이선스 및 기업 후원 (License & Sponsorship)

본 프로젝트는 **개인 및 비영리 사용자에게는 무료**로 공개되나, **사업적/영리적 목적으로 사용 시에는 후원 또는 유료 라이선스**가 권장됩니다.

*   **개인/비영리**: 자유로운 사용 가능 (무상)
*   **기업/영리 목적**: 지속적인 개발을 위해 [GitHub Sponsors](https://github.com/sponsors)를 통한 후원을 요청드립니다. 기업 후원 시 기술 지원 및 로고 노출 등 등급별 혜택을 제공합니다.
*   **상세 수익화 계획**: [PTSS 수익화 전략 및 라이선스 가이드](docs/PLAN_MONETIZATION.md)

상세 내용은 [LICENSE](LICENSE) 파일을 참조해 주세요.

---

## 🤝 기여하기 (Contributing)
이슈 제보나 기능 제안은 언제나 환영합니다! Pull Request를 보내주시면 검토 후 반영하겠습니다.

---
*Created by PTSS Developer. Premium management for your servers.*
