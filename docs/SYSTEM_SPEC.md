# PTSS (Premium Terminal & SFTP System) 시스템 명세서

## 1. 개요
PTSS(Premium Terminal & SFTP System)는 웹 기반의 SSH 클라이언트 및 서버 관리 시스템입니다. 사용자는 웹 브라우저를 통해 다수의 원격 서버에 접속하고, 터미널 명령을 실행하며, SFTP를 이용해 파일을 관리할 수 있습니다.

## 2. 주요 기능

### 2.1 대시보드 및 모니터링
- **실시간 상태 모니터링**: 등록된 모든 호스트의 CPU, RAM, Disk 사용량을 실시간 차트로 시각화
- **상태 배지**: 각 호스트의 Online/Offline 상태 표시
- **호스트 관리**: 호스트 추가/삭제 (관리자 전용), 접속 버튼 제공

### 2.2 웹 터미널 (Web Terminal)
- **xterm.js 기반 터미널**: 실제 터미널과 유사한 사용자 경험 제공 (색상, 리사이징 지원)
- **스마트 리사이징**: 브라우저 창 크기 변경 시 디바운스(Debounce) 처리를 통해 불필요한 서버 부하를 방지하고, Paramiko 채널의 실제 터미널 규격(`width`, `height`)을 즉각 동기화
- **세션 유지 및 복구 (Persistence)**: 서버 측 백로그 보관(최대 2000줄)을 통해 브라우저 새로고침이나 연결 끊김 시에도 작업 내역 자동 복구
- **커스터마이징**: 환경 설정 메뉴를 통해 테마(Default, Monokai, Dracula 등), 폰트 크기 및 종류 설정 가능
- **터미널 로그 저장**: 각 탭별로 현재 세션의 모든 입출력 내역을 `.txt` 파일로 다운로드 가능
- **명령어 제한**: 일반 사용자의 `su` 명령어 사용 및 `root` 계정 접속 제한
- **세션 유지 정책**: 브라우저 종료 시 터미널 세션을 즉시 종료하거나 일정 시간 유지하는 정책 설정 가능 (`session_retention`)

### 2.3 명령어 스니펫 (Snippet)
- **스니펫 패널**: 자주 사용하는 명령어를 카테고리별로 등록하고 클릭 한 번으로 터미널에 입력/실행
- **관리 기능**: 명령어 추가/수정/삭제 및 카테고리 관리 기능 제공

### 2.4 SFTP 파일 관리
- **파일 브라우저**: 원격 서버의 파일 목록 조회 (아이콘, 크기, 수정일 표시)
- **파일 업로드/다운로드**: 드래그 앤 드롭 업로드 및 클릭 다운로드 지원
- **로그 뷰어**: `.log` 등 텍스트 파일을 브라우저에서 즉시 미리보기
- **정렬 및 이동**: 파일명/크기/날짜 정렬 및 상위/하위 디렉토리 이동

### 2.5 UI/UX 편의성
- **사이드바 토글**: `☰` 버튼을 통해 왼쪽 메뉴를 접거나 펼칠 수 있어 좁은 화면에서도 넓은 작업 공간 확보
- **반응형 디자인**: 다양한 화면 크기에 최적화된 레이아웃 및 상태 유지 기능

### 2.6 활동 히스토리 및 감사 (Audit Log)
- **역할 기반 히스토리 제어**:
    - **Admin**: 시스템 전체 사용자의 모든 활동(명령어, 파일 조작 등)을 열람하고 통계 요약 데이터를 확인 가능
    - **User**: 본인이 수행한 활동 내역만 조회 가능 (타인 및 관리자 활동 내역에 대한 접근 차단)
- **상세 내역 보존**: 실행된 명령어의 전문, 발생 시간, 대상 호스트 등의 데이터를 영구 저장하여 추후 보안 감사에 활용 가능
- **컴팩트 테이블 뷰**: 대량의 히스토리 데이터를 한 화면에서 효율적으로 확인할 수 있도록 최적화된 정보 밀도 제공

### 2.7 사용자 및 보안 관리
- **역할 기반 접근 제어 (RBAC)**:
    - **Admin**: 호스트 관리, 사용자 관리, 전역 설정 관리 권한 보유
    - **User**: 할당된 호스트 접속 및 개인 히스토리 조회 가능 (민감 설정 및 타인 정보 접근 제한)
- **암호화된 데이터 저장**: 호스트 접속 패스워드 및 개인키는 DB에 마스터 키 기반의 **AES-256 (Fernet)** 방식으로 암호화되어 저장
- **전송 계층 보안 (HTTPS)**: 공용 네트워크 배포 시 **SSL/TLS(HTTPS)** 적용을 강력히 권장하며, 이를 통해 터미널 입출력 데이터의 가로채기를 방지함
- **세션 보안**: Flask-Session 및 보안 쿠키 설정을 이용한 세션 탈취 방지 및 CSRF 보호

## 3. 기술 스택 및 주요 함수

### 3.1 기술 스택
- **Backend**: Python 3.12, Flask, Flask-SocketIO, Flask-SQLAlchemy
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript, xterm.js
- **SSH/SFTP**: Paramiko
- **Encryption**: Cryptography (Fernet), Werkzeug Security
- **Asynchronous**: Eventlet

### 3.2 주요 모듈 및 함수
- **`core/` (핵심 패키지)**:
    - **`SSHManager` (`core/ssh_manager.py`)**: SSH 접속 수립 및 인증 처리, 셸 채널 생성 담당
    - **`core/models.py`**: 데이터베이스 스키마 정의 (User, Host, History, Config 등)
    - **`core/database.py`**: SQLAlchemy 인스턴스 (`db`) 관리
    - **`core/crypto.py`**: AES-256 데이터 암호화/복호화 유틸리티
    - **`core/state.py`**: SSH 세션, 백로그, 버퍼 등 전역 런타임 상태 관리
- **`ptss.py`**: 메인 애플리케이션 초기화, 블루프린트 등록, Socket.IO 이벤트 핸들링
- **`blueprints/`**: 기능별 라우트 분리 (Auth, Admin, Terminal, API, History, Scripts)

## 4. 데이터베이스 스키마 (SQLite)

### 4.1 `Config` 테이블 (시스템 설정)
| 필드명 | 타입 | 설명 |
|---|---|---|
| `key` | String(50) | 설정 키 (예: log_view_mode, sftp_sort_by) |
| `value` | String(100) | 설정 값 |

### 4.2 `Snippet` 테이블 (명령어 스니펫)
| 필드명 | 타입 | 설명 |
|---|---|---|
| `id` | Integer (PK) | 스니펫 ID |
| `category` | String(50) | 명령어 카테고리 |
| `name` | String(100) | 스니펫 명 |
| `command` | Text | 명령어 본문 |

## 5. 데이터베이스 스키마 (SQLite)

### 5.1 `User` 테이블 (사용자 정보)
| 필드명 | 타입 | 설명 |
|---|---|---|
| `username` | String | 로그인 ID |
| `password_hash` | String | 해시화된 비밀번호 |
| `role` | String | 사용자 권한 (`admin`, `user`) |

### 5.2 `Host` 테이블 (서버 정보)
| 필드명 | 타입 | 설명 |
|---|---|---|
| `hostname` | String | 접속 주소 (IP/Domain) |
| `username` | String | SSH 접속 계명 |
| `password` | String | **암호화된** 접속 비밀번호 |
| `encrypted_key` | Text | **암호화된** SSH 개인키 |

### 5.3 `History` 테이블 (활동 로그)
| 필드명 | 타입 | 설명 |
|---|---|---|
| `user_id` | Integer | 활동 수행 사용자 ID |
| `action_type` | String | 활동 유형 (SSH, SFTP, LOGIN 등) |
| `detail` | Text | 실행 명령어 등 상세 내역 |
| `timestamp` | DateTime | 발생 시간 |

## 6. 라이선스 및 수익화 모델
### 6.1 배포 모델 (Dual-Path)
PTSS는 오픈소스 가치와 상용 수준의 보안 기능을 동시에 충족하기 위해 두 가지 배포 경로를 제공합니다.
- **Community Edition (Open Source)**: 개인 및 비영리를 위한 전체 기능 공개 버전.
- **Enterprise Edition (Binary)**: 기업용 고도화 기능(세션 녹화, 명령어 방화벽 등)이 포함된 난독화/컴파일 버전.

### 6.2 수익화 및 후원
- 기업적 상업적 목적 사용 시 **GitHub Sponsors**를 통한 후원 및 라이선스 발급이 권장됩니다.
- 상세 계획은 [PTSS 수익화 전략](PLAN_MONETIZATION.md) 문서를 참조하십시오.

### 6.2 면책 조항
- 본 소프트웨어 사용으로 인해 발생하는 데이터 손실, 접속 장애 등의 결과에 대해 개발자는 어떠한 보상 책임도 지지 않습니다.

## 7. 배포 및 유지보수 도구

### 7.1 유지보수 및 테스트 도구 (`/tools` 디렉토리)
프로젝트 관리 및 테스트를 위한 보조 스크립트들은 `/tools` 디렉토리에 집중 관리됩니다.

- **데이터베이스 관련**:
    - `init_db.py`: 데이터베이스 초기화 및 테이블 생성
    - `migrate_db.py`, `migrate_v2.py`: 스키마 변경 시 마이그레이션 수행
    - `sync_admin.py`: 관리자 계정 상태 동기화 및 점검
- **검증 및 디버깅**:
    - `check_users.py`, `debug_users.py`: DB 사용자 목록 및 권한 확인
    - `debug_host_auth.py`: 호스트 접속 및 인증 과정 디버깅
    - `check_design.py`: UI 디자인 요소 및 CSS 변수 정합성 검사
- **테스트 스크립트**:
    - `test_login.py`: 로그인 기능 및 세션 처리 테스트 
    - `test_manual_ssh.py`: 수동 SSH 접속 기능 단위 테스트
    - `test_v2_setup.py`: 초기 설정(Setup) 프로세스 통합 테스트

### 7.2 배포 자동화 (`tools/deploy_ptss.py`)
- **목적**: 로컬 개발 환경(Windows)에서 홈 서버(Linux)로 프로젝트 최신 코드를 배포하고 서비스를 재시작함.
- **기능**: SFTP 파일 동기화, 의존성 설치, 기존 프로세스 종료/재시작 자동화.
