# PTSS 개발자 가이드 (Developer Guide)

이 문서는 PTSS 프로젝트에 기여하거나 로컬 개발 환경을 구축하려는 개발자를 위한 가이드입니다.

---

## 1. 환경 구축 (Environment Setup)

### 1.1 필수 요구 사항
- **Python**: 3.12 버전 이상 권장
- **OS**: Windows (개발 권장), Linux (운영 권장)
- **의존성**: `requirements.txt` 참조

### 1.2 가상 환경 설정 및 패키지 설치
```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화 (Windows)
.\venv\Scripts\activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

## 2. 데이터베이스 초기화
프로젝트 초기 실행 전 데이터베이스와 기본 테이블을 생성해야 합니다.
```bash
python tools/init_db.py
```
- 실행 후 `ptss.db` 파일이 생성되며, 최초 실행 시 '초기 설정 마법사'를 통해 관리자 계정을 생성할 수 있습니다.

## 3. 개발 서버 실행
```bash
python ptss.py
```
- 기본적으로 `http://localhost:6001`에서 서버가 구동됩니다.
- 코드 수정 시 자동 재시작이 필요한 경우 `ptss.py` 하단의 `socketio.run(app, ...)` 부분에서 `use_reloader=True` 설정을 확인하십시오. (운영 환경 배포 시에는 `False` 권장)

## 4. 프로젝트 구조

- **`core/`**: 비즈니스 로직 및 런타임 상태 관리
  - `ssh_manager.py`: 실시간 SSH/SFTP 중계 로직
  - `state.py`: 세션 백로그 및 버퍼 관리 (Persistence Layer)
  - `crypto.py`: 마스터 키 기반 암호화 유틸리티
- **`blueprints/`**: 기능 단위별 Flask 라우트 분리
- **`static/`**: CSS, JavaScript (Vanilla JS 위주)
- **`templates/`**: HTML (Jinja2 템플릿 엔진)
- **`tools/`**: DB 마이그레이션, 테스트, 배포 보조 도구

## 5. 코딩 규칙 (Coding Rules)
- **주석 및 가이드**: 모든 코드 설명과 주석은 **한국어**로 작성합니다.
- **크로스 플랫폼**: Windows 개발 및 Linux 배포 환경을 모두 고려하여 경로 처리 시 `os.path.join` 등을 적극 사용합니다.
- **보안**: 비밀번호나 개인키는 원본 그대로 DB에 저장하거나 로그에 남기지 않도록 주의하십시오.

## 6. 테스트 및 도구 활용
`/tools` 디렉토리의 스크립트들을 적극 활용하여 기능을 검증하십시오.
- `test_login.py`: 로그인 세션 검증
- `inspect_runtime.py`: 현재 메모리 상의 세션 상태 확인
- `check_design.py`: CSS 변수 및 UI 정합성 점검

## 6. 필수 유지 도구 (Essential Tools /tools)
문서화 및 유지보수를 위해 상시 유지되는 핵심 스크립트 목록입니다.

| 도구명 | 용도 | 사용 시점 |
| :--- | :--- | :--- |
| `init_db.py` | 데이터베이스 초기화 및 테이블 생성 | 최초 설치 시 |
| `migrate_v2.py` | v2 보안 스키마로의 마이그레이션 | 업그레이드 시 |
| `sync_admin.py` | 관리자 계정 권한 및 데이터 정합성 체크 | 관리자 로그인 이슈 발생 시 |
| `deploy_ptss.py` | 홈 서버(Linux) 자동 배포 및 재시작 | 코드 수정 후 배포 시 |
| `inspect_runtime.py` | 메모리 내 세션 및 공유 상태 실시간 모니터링 | 런타임 디버깅 시 |
| `check_design.py` | CSS 변수 및 UI 디자인 정합성 감사 | UI 스타일 수정 후 |
| `test_login.py` | 로그인 프로세스 및 세션 관리 자동 테스트 | 핵심 로직 수정 후 |
| `test_v2_setup.py` | 초기 설정 마법사 통합 테스트 | 설정 로직 수정 후 |

---
*새로운 아이디어나 버그 수정은 Pull Request를 통해 기여해 주시기 바랍니다.*
