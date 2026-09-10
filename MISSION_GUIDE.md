# B2-1 단계별 미션 학습 가이드

기준은 [WORK_LOG.md](WORK_LOG.md)의 `2026-09-09T14:57:31` 사용자 제공 원문 요약입니다. 기존 구현을 이해하는 순서이며 코드를 처음부터 다시 만들거나 현재 데이터를 초기화하는 지침은 아닙니다.

## 1. 실행과 결과부터 보기

Python 3.10 이상, 표준 라이브러리만 사용합니다. [README](README.md)의 실행 방법으로 `python3.12 -m budget_app --help`를 확인합니다. `-m`은 패키지를 실행한다는 뜻이고 `--help`는 사용법입니다.

**완료 기준:** 프로그램이 웹사이트가 아닌 콘솔 가계부임을 설명하고, 모든 명령·하위 명령의 도움말을 찾습니다.

## 2. 거래 한 건의 모양 이해하기

[models.py](budget_app/models.py)의 Transaction을 읽습니다. id는 식별자, type은 income/expense, date는 YYYY-MM-DD, amount는 양수 정수, category는 등록된 분류, memo/tags는 선택 항목입니다. dataclass는 이 항목들을 한 구조로 묶고 타입 힌트는 값의 종류를 전달합니다. 실제 검사는 valid_date, positive, create 등에서 합니다.

**완료 기준:** 잘못된 날짜·0/음수 금액·잘못된 타입을 왜 거부하는지 설명합니다. 카테고리 등록 여부는 서비스가 확인합니다.

## 3. 저장과 제너레이터 이해하기

[storage.py](budget_app/storage.py)의 initialize → records → transactions → write 순서로 읽습니다. JSONL은 한 줄에 JSON 객체 하나를 저장하는 방식입니다. 파일이 없으면 세 저장 파일을 만들고, 빈 카테고리는 기본 목록으로 초기화합니다.

`yield`는 한 건을 전달하고 다음 요청까지 실행을 잠시 멈춥니다. 전체 거래를 Python 리스트에 모으지 않도록 합니다. 최신순 정렬을 위해 전체 파일을 확인하는 일까지 없어지는 것은 아닙니다.

**완료 기준:** 프로그램을 종료하고 다시 실행해도 데이터가 남는 이유와 transactions/categories/budgets 세 파일의 차이를 설명합니다.

## 4. 필수 명령을 업무별로 연결하기

[service.py](budget_app/service.py)의 BudgetService를 읽습니다.

| 업무 | 명령·함수 |
| --- | --- |
| 추가·수정·삭제 | add, change; CLI의 add/update/delete |
| 조회·검색 | filtered, newest; list/search |
| 월별 합계와 예산 | summary, set_budget, budgets |
| 분류 관리 | categories, category |
| CSV 교환 | import_csv, export_csv |

최신순은 날짜 내림차순이며 같은 날짜는 추가 순서의 역순입니다. 제한 조회는 필요한 후보만 힙에 보관합니다. 무제한 조회는 임시 SQLite 파일에서 정렬하고 한 건씩 전달합니다. SQLite는 Python 표준 라이브러리이며 영구 저장은 JSONL입니다.

**완료 기준:** 10개 명령과 검색 옵션을 [발표 가이드](PRESENTATION_GUIDE.md)의 시연에 연결합니다. update는 옵션 방식, import는 오류 시 전체 취소, export는 월 또는 시작·종료일 조건이 필요함을 설명합니다.

## 5. 입력·오류 처리 연결하기

[cli.py](budget_app/cli.py)의 parser → main을 따라갑니다. add는 input으로 날짜·타입·분류·금액·메모·태그를 묻습니다. 오류 시 안내하고 종료하므로 수정하여 명령을 다시 실행합니다. update는 --id와 바꿀 필드를 지정합니다.

`@handle_errors`는 명령 실행을 감싸 공통 오류 안내를 담당합니다. `functools.wraps`는 원래 함수 정보를 보존합니다. 문법 오류는 ArgumentParser.error에서 처리합니다. 정상 0, 데이터·파일 오류 1, 문법 오류 2, 입력 중단 130으로 종료합니다.

**완료 기준:** “입력 → 검사 → 서비스 → 파일 저장 → 성공/실패 출력”을 실제 함수와 연결합니다.

## 6. 실패할 때 원본을 지키기

atomic_output은 같은 폴더의 임시 파일을 완성하고 flush/fsync 후 os.replace로 교체합니다. 교체 전 오류는 원본을 유지합니다. session의 잠금은 동시 실행 충돌을 막습니다. 강제 종료·전원 장애의 모든 상황이나 세 파일 전체의 동시 트랜잭션을 보장하지는 않습니다.

**완료 기준:** 잘못된 CSV와 없는 id가 기존 거래를 망가뜨리면 안 되는 이유를 설명합니다. 실습은 임시 폴더에서 합니다.

## 7. 검증하고 발표하기

[tests/test_app.py](tests/test_app.py)는 개발용 검사입니다. 원문의 필수 구현과 자동 검사 도구를 구분합니다. README의 검사 명령을 실행하고 [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md)의 대본·전체 요구사항 표로 설명 연습을 합니다.

**완료 기준:** CRUD·검색·요약·예산·카테고리·CSV, 클래스·모듈 분리, 제너레이터·데코레이터·타입 힌트, 데이터 보호를 자기 말로 설명합니다. 백업 명령·반복 거래·전체 열 정렬은 미구현 선택 기능으로 구분합니다.


## 2026-09-10 코드 정리 후 읽는 방법

cli.py의 `main()`은 명령을 골라 `run_add`, `run_update`, `run_summary` 등 해당 `run_명령` 함수로 전달합니다. 각 함수가 입력·출력을 담당하고 실제 처리 규칙은 BudgetService에 있습니다. 수정 흐름은 `main → run_update → service.change → Repository.write → atomic_output`입니다.

service.py의 `filtered()`는 검색 조건을 하나씩 검사하고 맞지 않으면 `continue`로 다음 거래로 넘어갑니다. 모두 통과하면 `yield`로 거래를 전달합니다. 추가·수정은 중간 변수로 데이터 변환 순서를 보여 줍니다. 저장 방식·잠금·최신순 정렬·입력 검증과 출력은 유지했습니다. 코드 정리 후 기존 테스트 21개가 Python 3.12에서 모두 통과했습니다.
