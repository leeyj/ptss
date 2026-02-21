# PTSS 기여 가이드라인 (Contributing Guide)

PTSS(Premium Terminal & SFTP System) 프로젝트에 관심을 가져주셔서 감사합니다! 여러분의 기여가 이 프로젝트를 더욱 훌륭하게 만듭니다.

## 🤝 기여 방법

### 1. 버그 리포트 및 기능 제안
- 프로젝트의 [GitHub Issues](https://github.com/leeyj/ptss/issues) 탭을 통해 버그를 신고하거나 새로운 기능을 제안할 수 있습니다.
- 버그 신고 시 **재현 단계, 기대 결과, 실제 결과**를 명확히 작성해 주세요.

### 2. 코드 기여 (Pull Request)
1. 이 저장소를 포크(Fork)합니다.
2. 새로운 기능이나 수정을 위한 브랜치를 생성합니다 (`feature/amazing-feature` 또는 `fix/bug-name`).
3. 변경 사항을 커밋합니다. (커밋 메시지는 가급적 명확하게 작성해 주세요.)
4. 생성한 브랜치를 원격 저장소에 푸시합니다.
5. `main` 브랜치를 대상으로 Pull Request를 생성합니다.

## 🛠️ 개발 환경 설정
- **기본 스택**: Python 3.8+, Flask, Flask-SocketIO
- **설치**: `pip install -r requirements.txt`
- **실행**: `python ptss.py` (최초 실행 시 Setup Wizard가 실행됩니다.)

## 📏 코딩 규칙 (Coding Rules)
- 모든 코드 설명, 가이드, 주석은 반드시 **한국어**로 작성합니다.
- 변수 및 함수 명명은 직관적인 영어 이름을 사용합니다.
- 새로운 기능을 추가할 때는 `docs/` 내 관련 문서를 함께 업데이트해 주세요.
- 보안에 민감한 정보(IP, 비밀번호 등)가 코드에 포함되지 않도록 주의해 주세요. (커밋 전 `tools/security_scan.py` 실행 권장)

## ⚖️ 라이선스
기여하신 모든 코드는 프로젝트의 [MIT License](LICENSE)에 따라 공개되는 것에 동의하는 것으로 간주됩니다.

---
여러분의 소중한 참여를 기다립니다!
