# B2-1 파일별 역할 안내

B2-1은 터미널에 명령을 입력하는 **Python 콘솔 가계부**입니다. B1-1처럼 HTML·CSS·JavaScript로 화면을 만드는 프로젝트가 아닙니다. 여기서는 **Python이 미션의 핵심 구현 언어**입니다.

## 핵심 코드부터 읽기

| 파일 | 무엇을 하나요? | 먼저 찾을 이름 |
| --- | --- | --- |
| [budget_app/models.py](budget_app/models.py) | 거래 한 건의 항목과 올바른 날짜·금액·타입을 정합니다. | Transaction, valid_date, positive |
| [budget_app/storage.py](budget_app/storage.py) | 거래를 파일에서 읽고 안전하게 저장합니다. | Repository, records, transactions, atomic_output |
| [budget_app/service.py](budget_app/service.py) | 검색·수정·삭제·요약·예산·카테고리·CSV 처리 규칙입니다. | BudgetService, add, change, newest, summary |
| [budget_app/cli.py](budget_app/cli.py) | 사용자의 명령과 입력을 읽고 처리 결과·오류를 출력합니다. | parser, main, handle_errors, show |
| [budget_app/__main__.py](budget_app/__main__.py) | `python -m budget_app` 실행을 시작해 CLI로 연결합니다. | main 호출, SystemExit |
| [budget_app/__init__.py](budget_app/__init__.py) | budget_app을 Python 패키지로 구성하는 파일입니다. 현재는 패키지 설명이 있습니다. | 상단 설명 |

**추천 읽기 순서:** models → storage → service → cli. 그다음 __main__에서 전체 실행 시작을 확인합니다. 모듈은 Python 파일 하나, 패키지는 관련 모듈을 묶은 폴더라고 이해하면 됩니다.

```text
사용자가 명령 입력
→ cli.py가 명령 해석
→ service.py가 업무 규칙 처리 (models.py로 데이터 검사)
→ storage.py가 파일 읽기·쓰기
→ cli.py가 결과 출력
```

## 문서와 예제

| 파일 | 역할 |
| --- | --- |
| [README.md](README.md) | 실행 방법·명령 예시·저장 방식·CSV 규격·오류/복구 정책·검사 방법을 소개합니다. |
| [MISSION_GUIDE.md](MISSION_GUIDE.md) | 미션을 단계별로 공부하는 순서와 완료 기준입니다. |
| [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md) | 쉬운 설명·발표 대본·실제 시연·예상 질문·전체 미션 확인표입니다. |
| [FILE_GUIDE.md](FILE_GUIDE.md) | 지금 읽는 파일 역할 안내입니다. |
| [WORK_LOG.md](WORK_LOG.md) | 작업 이력과 미션 요약입니다. `2026-09-09T14:57:31` 기록이 원문 요구사항 정리입니다. |
| [AGENTS.md](AGENTS.md) | Codex의 작업 규칙입니다. 가계부 실행 기능은 아닙니다. |
| [examples/import.csv](examples/import.csv) | 가져오기를 연습할 수 있는 거래 4건의 CSV입니다. 실제 가계부 데이터는 별도로 저장됩니다. |

`.md`는 Markdown 설명 문서입니다. VS Code의 ‘미리 보기 열기’로 표와 제목을 읽으면 편합니다.

## tests는 왜 있나요?

[tests/test_app.py](tests/test_app.py)는 이전 구현 과정에서 추가한 **개발용 자동 검사 파일**입니다. 거래 추가·검색·예산 계산뿐 아니라 파일 저장 실패 때 원본이 남는지도 검사합니다. 가계부를 실행할 때 자동으로 실행되지 않으며, 미션 원문에서 이 이름의 테스트 파일을 필수로 지정하지는 않았습니다.

B1-1의 review.py와 목적은 비슷하지만 **Chrome이나 Playwright 없이 Python 표준 라이브러리 unittest만** 사용합니다. Python 프로그램 자체와 명령 실행 결과를 확인합니다. `tests/__init__.py`는 tests를 패키지로 구성해 테스트 탐색을 돕는 파일입니다.

| 검사 표현 | 쉬운 뜻 |
| --- | --- |
| setUp | 각 검사 전에 새로운 임시 데이터 폴더 준비 |
| test_로 시작하는 함수 | 확인할 상황 하나 |
| assertEqual 등 | 예상 결과와 실제 결과 비교 |
| patch | 파일 교체 실패 같은 상황을 검사 중에만 재현 |
| OK | 이번에 실행한 검사 전부 통과 |

B2-1 루트에서 Python 3.10 이상으로 실행합니다.

```sh
python3.12 -m unittest discover -v
```

현재 검사는 21개이며 임시 폴더를 사용합니다. 전체 환경의 무오류나 실제 미션 채점 통과를 보장하는 것은 아닙니다. 처음 공부할 때는 핵심 코드 네 파일부터 읽고, 테스트는 기능을 바꾼 뒤 확인하는 도구로 사용하세요.

## 설정과 실행 중 생기는 파일

| 파일·폴더 | 역할 |
| --- | --- |
| [.github/workflows/tests.yml](.github/workflows/tests.yml) | GitHub push/PR 때 Python 3.10·3.12·3.14에서 자동 검사를 실행하는 설정입니다. 검사 설정 존재와 실제 실행 성공은 구분합니다. |
| [.gitignore](.gitignore) | data/, Python 캐시, .venv/ 등 Git에서 새로 추적하지 않을 경로를 정합니다. |
| .git/ | Git 변경 이력을 보관하는 내부 폴더입니다. |
| data/transactions.jsonl | 실행 후 생기는 거래 저장 파일. 한 줄에 한 거래입니다. |
| data/categories.jsonl | 카테고리 목록입니다. |
| data/budgets.jsonl | 월별 예산입니다. |
| data/.lock | 한 번에 한 작업만 실행하도록 표시하는 임시 잠금 파일입니다. |
| __pycache__/ | Python 실행 중 생성되는 캐시입니다. 직접 작성하는 핵심 코드가 아닙니다. |

기본 data는 **명령을 실행한 위치**에 생성됩니다. `--data-dir`로 바꿀 수 있습니다. 실제 돈 기록은 문서나 예제와 다르므로 연습에는 발표 가이드의 임시 폴더를 사용하세요.


## 2026-09-10 코드 정리 후 읽는 방법

cli.py의 `main()`은 명령을 골라 `run_add`, `run_update`, `run_summary` 등 해당 `run_명령` 함수로 전달합니다. 각 함수가 입력·출력을 담당하고 실제 처리 규칙은 BudgetService에 있습니다. 수정 흐름은 `main → run_update → service.change → Repository.write → atomic_output`입니다.

service.py의 `filtered()`는 검색 조건을 하나씩 검사하고 맞지 않으면 `continue`로 다음 거래로 넘어갑니다. 모두 통과하면 `yield`로 거래를 전달합니다. 추가·수정은 중간 변수로 데이터 변환 순서를 보여 줍니다. 저장 방식·잠금·최신순 정렬·입력 검증과 출력은 유지했습니다. 코드 정리 후 기존 테스트 21개가 Python 3.12에서 모두 통과했습니다.
