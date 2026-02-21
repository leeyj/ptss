# ⚡ PTSS: Premium Terminal & SFTP System

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Personal--Free-green.svg)](LICENSE)

[**한국어 설명 (Korean)**](#-ptss-premium-terminal--sftp-system-ko) | [**English Description**](#-ptss-premium-terminal--sftp-system-en)

---

<a name="-ptss-premium-terminal--sftp-system-ko"></a>
## ⚡ PTSS: Premium Terminal & SFTP System (KO)

**PTSS**는 웹 브라우저 하나로 여러 서버를 동시에 관리할 수 있는 가볍고 강력한 **웹 기반 SSH 클라이언트 & SFTP 매니저**입니다. 복잡한 설치 없이 실시간 터미널 제어와 파일 관리를 프리미엄 UI 환경에서 경험하세요.

### ✨ 주요 특징 (Key Features)

#### 🖥️ 고성능 웹 터미널
*   **xterm.js 기반**: 실제 로컬 터미널과 동일한 수준의 색상 표현과 반응 속도.
*   **멀티 탭 지원**: 여러 서버 세션을 탭 형태로 동시에 전환하며 작업 가능.
*   **세션 유지(Persistence)**: 브라우저를 닫거나 새로고침해도 작업 내용이 서버에 보관되어 즉시 복구.
*   **테마 커스터마이징**: Monokai, Dracula 등 유명 테마와 폰트 크기/종류 자유 조절.

#### 📁 통합 SFTP 파일 매니저
*   **GUI 기반 관리**: 드래그 앤 드롭 업로드, 클릭 한 번으로 다운로드.
*   **실시간 로그 뷰어**: 서버 내 로그 파일을 브라우저에서 즉시 미리보기.
*   **권한 및 소유자 확인**: 파일별 상세 속성 확인 및 리눅스 친화적 인터페이스.

#### 🚀 생산성 도구
*   **명령어 스니펫(Snippet)**: 자주 쓰는 복잡한 명령어를 저장해두고 클릭 한 번으로 실행.
*   **자동화 스크립트**: 반복되는 일련의 작업을 스크립트로 관리 및 즉시 배포.
*   **대시보드 모니터링**: 등록된 서버들의 CPU, RAM, 디스크 상태를 실시간 차트로 확인.

### 🛠️ 설치 및 실행 (Setup & Run)

#### 1. 초기 설정 (Setup)
애플리케이션 실행 전, 루트 디렉토리에 `.env` 파일을 생성하고 필수 보안 키를 설정해야 합니다.

```env
# .env 파일 예시
PTSS_SECRET_KEY=your_unique_session_key  # 세션 유지용 (필수)
DATABASE_URL=sqlite:///ptss.db           # DB 경로 (선택)
```

#### 2. 시작하기
```bash
python ptss.py
```
접속 주소: `http://localhost:6001`

---

<a name="-ptss-premium-terminal--sftp-system-en"></a>
## ⚡ PTSS: Premium Terminal & SFTP System (EN)

**PTSS** is a lightweight yet powerful **web-based SSH client & SFTP manager** that allows you to manage multiple servers simultaneously through a single web browser. Experience real-time terminal control and file management in a premium UI environment without complex installations.

### ✨ Key Features

#### 🖥️ High-Performance Web Terminal
*   **Powered by xterm.js**: Offers color expression and response speed identical to a local terminal.
*   **Multi-Tab Support**: Work on multiple server sessions simultaneously using a tabbed interface.
*   **Session Persistence**: Your work is saved on the server, allowing instant recovery even if the browser is closed or refreshed.
*   **Theme Customization**: Freely adjust themes (Monokai, Dracula, etc.), font sizes, and types.

#### 📁 Integrated SFTP File Manager
*   **GUI-Based Management**: Drag-and-drop uploads and one-click downloads.
*   **Real-time Log Viewer**: Preview server log files directly in the browser.
*   **Permissions & Ownership**: Detailed file attribute checks with a Linux-friendly interface.

#### 🚀 Productivity Tools
*   **Command Snippets**: Save frequently used complex commands and execute them with a single click.
*   **Automation Scripts**: Manage and deploy repetitive tasks using scripts.
*   **Dashboard Monitoring**: Check CPU, RAM, and disk status of registered servers with real-time charts.

### 🛠️ Setup & Run

#### 1. Requirements
Ensure you have Python 3.12+ installed. Install dependencies using:
```bash
pip install -r requirements.txt
```

#### 2. Configuration
Before running the application, create a `.env` file in the root directory and set the essential security keys.

```env
# Example .env file
PTSS_SECRET_KEY=your_unique_session_key  # Required for session handling
DATABASE_URL=sqlite:///ptss.db           # DB path (Optional)
```

#### 3. Quick Start 
```bash
python ptss.py
```
Access URL: `http://localhost:6001`

---

## 📜 License & Sponsorship

본 프로젝트는 **개인 및 비영리 사용자에게는 무료**로 공개되나, **사업적/영리적 목적으로 사용 시에는 후원 또는 유료 라이선스**가 권장됩니다.
This project is **free for personal and non-profit users**. For **commercial or for-profit use, sponsorship or a paid license** is encouraged.

*   **Personal/Non-Profit**: 자유로운 사용 가능 (무상) / Free to use.
*   **Corporate/Commercial**: 지속적인 개발을 위해 [GitHub Sponsors](https://github.com/sponsors)를 통한 후원을 요청드립니다. / Please consider sponsoring via [GitHub Sponsors](https://github.com/sponsors) to support ongoing development.
*   **Monetization Plan**: [PTSS Monetization Strategy & License Guide](docs/PLAN_MONETIZATION.md)

---

## 🤝 기여하기 (Contributing)
이슈 제보나 기능 제안은 언제나 환영합니다! / Bug reports and feature suggestions are always welcome!

---
*Created by PTSS Developer. Premium management for your servers.*
