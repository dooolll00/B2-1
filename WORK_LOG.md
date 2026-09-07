# B2-1 작업 기록

> 이 파일은 Codex 채팅이 사라져도 프로젝트 작업 흐름을 이어가기 위한 기록입니다.
> Codex는 작업 시작 시 이 파일을 읽고, 작업 종료 시 새 기록을 맨 아래에 추가합니다.

## 프로젝트 상태

- 프로젝트: B2-1
- 상태: 새 프로젝트 시작 전
- 기본 브랜치: `main`
- 현재 원칙: 미션 요구사항을 받은 뒤 프로젝트 구조와 기술을 결정한다.

---

## 2026-09-07 — 프로젝트 기록 시작

### 요청
- B2-1은 앞으로 새로 만들 예정이다.
- Codex 채팅 기록이 사라져도 개발 내용을 이어갈 수 있도록 기록 체계를 먼저 만든다.

### 변경 파일
- `AGENTS.md` 추가
- `WORK_LOG.md` 추가

### 현재 상태
- 아직 실제 미션 구현은 시작하지 않았다.
- 미션 요구사항을 받은 뒤 필요한 파일과 기능을 만든다.

### 다음 작업
1. B2-1 미션 요구사항 확인
2. 요구사항을 `WORK_LOG.md`에 요약
3. 프로젝트 구조 결정
4. 구현 및 테스트
5. 작업 결과와 다음 할 일을 이 파일에 계속 기록

## 2026-09-07T18:18:05+09:00 — 미션 구현 및 푸시 요청 접수

- 요청: B2-1 미션 구현, 검증, GitHub 푸시까지 수행.
- 수정 파일: `WORK_LOG.md` (이번 접수 기록 추가).
- 확인: 작업 기록과 `AGENTS.md`, 디렉터리 구조 및 상위 Git 상태/원격 확인. 현재 미션 문서와 구현 파일은 없음.
- 명령 결과: 파일 목록 조회 성공. 상위 경로에는 별도 Git 저장소가 있고 실제 기록은 하위 `B2-1`에 있음. 구현 시 저장소 경계를 확인해야 함.
- 테스트: 구현 전이므로 실행하지 않음.
- 미해결: 미션 요구사항이 아직 전달되지 않음.
- 다음 작업: 미션 본문과 통과 조건을 받은 뒤 구현, 테스트, 커밋 및 푸시 수행. 사용자에게서 푸시 권한을 이미 받음.
- 커밋/푸시: 이번에는 수행하지 않음.

## 2026-09-07T18:26:58+09:00 — 콘솔 가계부 미션 구현 및 검증

- 요청: 첨부된 B2-1 Python 콘솔 가계부 미션 전체 구현, 검증, GitHub 푸시.
- 저장소: `/Users/dooolll5969/Desktop/B2-1/B2-1`, 원격 `dooolll00/B2-1`, 브랜치 `main`. 상위 폴더에도 별도 .git이 있으므로 실제 코드 작업은 이 하위 저장소에서 수행.
- 추가/수정 파일: `budget_app/__init__.py`, `__main__.py`, `models.py`, `storage.py`, `service.py`, `cli.py`, `tests/__init__.py`, `tests/test_app.py`, `examples/import.csv`, `.github/workflows/tests.yml`, `.gitignore`, `README.md`, `WORK_LOG.md`.
- 핵심 작업: 대화형 add, 최신순 list/search, 옵션 update, delete, summary, budget set/list, category add/list/remove, CSV import/export 구현. 3개 JSONL 영속 저장, 양수 정수 금액, dataclass와 타입 힌트, 공통 예외 데코레이터, 원자적 파일 교체, 배타적 잠금 적용.
- 결정: 상세 요구사항에 맞춰 옵션은 -- 사용. 기본 카테고리 자동 생성. CSV 오류 시 전체 취소, 재가져오기는 새 id로 등록. 제한 조회는 O(limit) 힙, 무제한 검색은 임시 SQLite 디스크 정렬 후 yield; 영속 데이터는 JSONL만 사용. 최신순은 거래일 내림차순, 같은 날짜는 추가 순서 역순.
- 실행: 저장소 루트에서 `python3 -m budget_app --help`, 저장 폴더 변경은 최상위 `--data-dir`. README에 전체 예시와 CSV 스키마, 실패/복구 정책 작성.
- 테스트: Python 3.12.13에서 `python3 -m unittest discover -v` 15개 모두 성공. 전체 CLI 흐름, 5,000건 정렬, CSV 왕복/부분 실패, 저장 교체 실패 시 원본 유지, 손상 파일, 잠금, 입력 오류와 도움말 검증. `python3 -m compileall -q budget_app tests`, `git diff --check` 성공. 예제 월 지출 215000원 및 예산 사용률 43.0% 확인.
- 미해결/한계: 실제 채점기는 제공되지 않아 채점 결과는 미확인. Python 3.10/3.14는 GitHub Actions 검증 설정만 완료. 강제 종료 후 남는 .lock 복구 방법은 README 참고. 선택 보너스 중 반복 거래 및 backup 명령은 구현 범위에 포함하지 않음.
- 커밋 예정 메시지: `feat: implement safe streaming console budget app`. 현재 푸시 전이며 결과는 다음 기록에 추가.
- 다음 작업: main 커밋/푸시 및 원격 반영 확인.
