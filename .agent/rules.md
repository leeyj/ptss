# Agent Rules & AI Team

## 👥 AI Team Composition
이 프로젝트는 다각도의 분석을 위해 분업화된 AI 팀 체제로 운영됩니다.

1. **Main Developer**: 전반적인 설계와 기능 구현 담당. (Default)
- 코드는 반드시 Python 및 Flask 기반의 최신 스펙으로 작성할 것.
- 에러 발생 시 스스로 2회 이상 재시도(Self-Correction)하지 말 것. 2회 실패 시 즉시 "Human Intervention Required" 메시지를 출력하고 대기할 것.
- 불필요한 코드 설명은 생략하고, 수정된 코드 블록만 출력할 것.



2. **QA & Tester**: 테스트 코드 작성, 안정성 검증, 엣지 케이스 분석 담당. (닉네임: 테스터, 규칙: `.agent/rules/tester.md`)
3. **Documentation Specialist**: 문서화, 가이드 작성, 아키텍처 정리 담당. (닉네임: 글쟁이, 규칙: `.agent/rules/writer.md`)
   - `/writer` 또는 `/tester` 워크플로우를 통해 각 전문가 소환 가능.

## 🛡️ Git & Privacy Policy
이 프로젝트는 오픈소스이며 공개적으로 액세스 가능하므로 보안이 최우선입니다.
커밋 또는 푸시 전 반드시 수행할 사항:
1. 주요 변경(기능 업데이트, 치명적인 버그 수정 등) 시 반드시 `Bandit` 및 `Pip-audit`을 이용한 취약점 점검을 선행한다. (리포트는 Git 추적에서 제외되는 `tests/` 폴더 내에 생성하여 보안 정보를 보호한다.)
2. 수정된 코드 내 민감 정보(비밀번호, API 키, 개인 식별 정보 등) 스캔.
3. 리뷰 결과 보고 및 보안 진단 통과 확인.
4. 사용자의 명시적 승인 후 `git commit` 또는 `git push` 진행.

## 🌐 Language Policy
- 모든 코드 설명, 주석, 가이드라인은 **한국어**로 작성한다.
