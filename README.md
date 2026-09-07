# B2-1 — 콘솔 가계부

Python 3.10 이상과 **표준 라이브러리만** 사용하는 파일 기반 가계부입니다. `pip install`은 필요 없습니다. 수입/지출 CRUD, 검색, 월별 요약, 예산, 카테고리, CSV 가져오기/내보내기를 지원합니다.

## 실행

이 README와 `budget_app` 폴더가 있는 저장소 루트에서 실행하세요. 환경에 따라 `python` 대신 `python3`를 사용합니다.

```sh
python -m budget_app --help
python -m budget_app category list
python -m budget_app add
python -m budget_app list --limit 20
```

`add`는 날짜 → 타입 → 카테고리 → 금액 → 메모 → 태그 순서의 **대화형 입력**입니다. 날짜는 `2024-01-15`, 타입은 `income`/`expense`, 금액은 `15000`처럼 쉼표 없는 양수 정수로 입력하세요. 메모/태그는 엔터로 생략합니다. 입력 오류는 원인과 힌트를 표시하고 실패 코드로 종료하므로 명령을 다시 실행하세요. 저장 성공 시 UUID 기반의 유일한 `TX-...` id를 출력합니다.

옵션은 상세 요구사항과 예시에 따라 **`--`로 통일**합니다. 모든 명령과 하위 명령에 `--help`를 지원합니다.

## 저장 위치와 형식

기본 위치는 **명령을 실행한 현재 디렉터리의 `./data`**입니다. 다른 곳에서 실행할 때는 같은 절대 경로를 지정해야 동일한 데이터를 사용합니다.

```sh
python -m budget_app --data-dir /tmp/my-ledger category list
python -m budget_app list --data-dir /tmp/my-ledger --limit 3
```

`--data-dir`는 최상위 또는 1단계 명령 뒤에 둡니다. `category add`와 같은 하위 명령에서는 `python -m budget_app --data-dir /tmp/my-ledger category add`처럼 사용하세요.

| 파일 | 형식 및 내용 |
| --- | --- |
| `data/transactions.jsonl` | 한 줄에 거래 객체 하나: `id,type,date,amount,category,memo,tags` |
| `data/categories.jsonl` | 한 줄에 `{"name":"food"}` 형태의 카테고리 |
| `data/budgets.jsonl` | 한 줄에 `{"month":"2024-01","amount":500000}` 형태의 월 예산 |

세 파일 모두 UTF-8 JSONL이며 첫 실행에 자동 생성됩니다. 카테고리 파일이 비어 있으면 `food, transport, rent, etc, salary`를 자동 등록합니다. 마지막 카테고리를 지우면 다음 실행 때 기본 카테고리가 다시 생성됩니다. 실제 사용자 데이터는 `.gitignore`로 제외합니다.

금액은 정수로 계산하고 태그는 JSON 문자열 배열로 저장합니다. 거래 id는 수정해도 유지되고, 삭제한 id를 재사용하지 않습니다.

## 주요 명령

```sh
# 거래일 최신순, 같은 날짜는 나중에 추가된 거래 우선
python -m budget_app list --limit 3

# 모든 조건은 AND. 기간 양 끝 포함, 태그는 정확히 일치
python -m budget_app search --from 2024-01-01 --to 2024-01-31 --category food --type expense --q 점심 --tag meal
python -m budget_app search --q 점심 --limit 10

# 월별 요약, 카테고리별 지출 TOP N (기본 3)
python -m budget_app summary --month 2024-01 --top 3
python -m budget_app budget set --month 2024-01 --amount 500000
python -m budget_app budget list
python -m budget_app budget list --month 2024-01

# add/remove는 이름을 생략하면 대화형 입력
python -m budget_app category add
python -m budget_app category add --name books
python -m budget_app category list
python -m budget_app category remove --name books

# 아래 TX-실제ID는 add/list에서 확인한 id로 교체
python -m budget_app update --id TX-실제ID --amount 18000 --memo 수정한메모 --tags meal,work
python -m budget_app update --id TX-실제ID --date 2024-01-16 --type expense --category food
python -m budget_app update --id TX-실제ID --memo "" --tags ""
python -m budget_app delete --id TX-실제ID
```

**update는 옵션 방식으로 고정**합니다. 지정한 필드만 수정하고 `--memo ""`, `--tags ""`로 해당 값을 비웁니다. 수정 옵션 없이 실행하거나 없는 id를 지정하면 실패합니다. 사용 중인 카테고리는 삭제할 수 없습니다. 해당 거래의 카테고리를 먼저 수정하거나 거래를 삭제하세요.

검색의 메모는 대소문자 구분 없는 부분 일치이며 카테고리와 태그는 대소문자를 구분합니다. 결과가 없으면 `데이터 없음`을 출력합니다. 월별 요약은 총수입, 총지출, 잔액, 지출 TOP N을 표시하고 예산이 있으면 사용률을 표시합니다. 지출이 예산보다 **큰 경우** 초과 경고가 나옵니다. 빈 달에도 설정된 예산을 조회할 수 있습니다.

## CSV 가져오기/내보내기

```sh
python -m budget_app import --from examples/import.csv
python -m budget_app export --out january.csv --month 2024-01
python -m budget_app export --out period.csv --from 2024-01-01 --to 2024-01-31
```

내보내기는 `--month` 또는 `--from`과 `--to` **둘 다** 필요합니다. 월과 기간 옵션을 혼용할 수 없습니다. 최신순으로 출력하고 데이터가 없으면 헤더만 생성합니다. 저장 데이터 보호를 위해 저장 폴더 밖으로 내보내세요. 대상 CSV가 있으면 완성된 파일로 교체합니다.

CSV 스키마는 아래와 같습니다. UTF-8, 헤더 필수이며 가져오기는 UTF-8 BOM도 허용합니다. 내보내기는 아래 순서를 고정합니다. 가져오기는 열 순서를 바꿀 수 있으나 중복/알 수 없는 열은 거부합니다.

| column | 필수 | 설명 |
| --- | --- | --- |
| date | Y | 실제 존재하는 날짜, `YYYY-MM-DD` |
| type | Y | `income` 또는 `expense` |
| category | Y | 등록된 카테고리 |
| amount | Y | 0보다 큰 정수, 소수/천 단위 쉼표 불가 |
| memo | N | 문자열, 열 생략 시 빈 문자열 |
| tags | N | 쉼표로 구분한 태그, 열 생략 시 빈 목록 |

```csv
date,type,category,amount,memo,tags
2024-01-15,expense,food,15000,"점심, 커피","meal,work"
```

쉼표나 줄바꿈이 포함된 셀은 CSV 규칙에 맞게 큰따옴표로 감쌉니다. `examples/import.csv`에 실행 가능한 예제가 있습니다. 가져오기는 각 행에 **새 id**를 부여합니다. 같은 파일을 다시 가져오면 새 거래로 중복 등록되므로 한 번만 실행하세요. CSV는 id를 포함하지 않으며 완전한 백업은 JSONL 파일 3개를 함께 복사해야 합니다.

**가져오기 정책: 전체 성공 또는 전체 취소.** 잘못된 행, 미등록 카테고리, 인코딩 오류 등이 하나라도 있으면 기존 거래는 그대로 유지됩니다. 성공 시 `imported=N, skipped=0`을 표시합니다. 카테고리를 자동 추가하지 않습니다.

## 구조와 데이터 안전성

- `models.py`: 불변 `Transaction` dataclass, 양수 정수/날짜/타입 검증과 타입 힌트.
- `storage.py`: `Repository`, `yield` 기반 JSONL 읽기, 임시 파일 기록과 원자적 교체.
- `service.py`: `BudgetService`, CRUD/검색/요약/CSV 등 업무 규칙.
- `cli.py`: argparse, 대화형 입력, 화면 출력. `@handle_errors` 데코레이터가 오류 메시지와 종료 코드를 공통 처리합니다.

거래는 한 줄씩 읽습니다. `list --limit N`은 힙으로 최신 N개만 보관하므로 메모리는 O(N)입니다. `search`에 limit이 없으면 임시 디스크 SQLite로 정렬한 뒤 커서에서 한 건씩 `yield`합니다. SQLite는 **일회성 정렬용**이며 영구 저장 형식은 세 JSONL 파일입니다. 검색 결과 전체를 Python 리스트로 만들지 않고, 임시 정렬 파일은 완료/오류 시 제거합니다. 요약은 거래를 한 번 순회하며 카테고리 합계만 보관합니다.

모든 저장 변경은 같은 폴더의 임시 파일에 쓰고 `flush`/`fsync` 후 `os.replace`로 교체합니다. 추가/수정/삭제/가져오기가 실패하면 원본을 유지하며 실패한 임시 파일은 정리합니다. 이 때문에 거래 추가도 기존 파일을 순회하는 O(전체 거래 수) 작업입니다. 업데이트/가져오기에는 원본 크기 이상의 추가 디스크 공간이 필요합니다.

프로세스 간 충돌은 `data/.lock`의 배타적 생성으로 방지하며 조회도 같은 잠금을 사용합니다. 다른 작업이 있으면 기다리지 않고 원인과 재시도 안내를 출력합니다. 강제 종료로 `.lock`이 남았다면 실행 중인 가계부 프로그램이 없는지 확인한 뒤에만 잠금 파일을 삭제하세요. 전원 장애의 모든 상황을 보장하는 데이터베이스는 아니므로 중요한 데이터는 종료 상태에서 세 파일을 함께 백업하세요.

정상 종료 코드 `0`, 데이터/파일 오류 `1`, 명령 문법 오류 `2`, 입력 중단 `130`입니다. 예상 가능한 입력/파일 오류에는 스택트레이스를 출력하지 않습니다. 손상된 JSONL은 자동으로 덮어쓰지 않으며 복원 안내를 표시합니다.

## 검증

```sh
python -m unittest discover -v
```

테스트는 임시 폴더만 사용합니다. 입력 검증, 영속 저장, CRUD, 최신순/동시 검색 조건, 예산/요약, 카테고리 보호, CSV 왕복 및 부분 실패, 파일 교체 실패, 파일 손상, 잠금 충돌, CLI 입력/종료 코드와 모든 도움말을 검증합니다. GitHub Actions에 Python 3.10/3.12/3.14 검증을 설정했습니다.

샘플 결과: 별도 빈 데이터 폴더에 `examples/import.csv`를 가져오면 2024-01 총수입 3,000,000원, 총지출 215,000원, 잔액 2,785,000원입니다. 예산 500,000원을 설정하면 사용률은 43.0%입니다.

## 미션 구현 체크리스트

아래 체크는 **원래 미션의 필수 요구사항과 현재 구현**을 기준으로 합니다. 실제 채점 결과를 의미하지는 않습니다. 설명 준비는 [발표·시연 가이드](PRESENTATION_GUIDE.md)를 참고하세요.

### 실행과 데이터 모델

- [x] Python 3.10 이상, 표준 라이브러리만 사용하며 별도 설치가 필요 없다.
- [x] `python -m budget_app <command>`로 실행하고 모든 명령·하위 명령에 `--help`를 제공한다.
- [x] 긴 옵션을 `--`로 통일하고 `--data-dir`로 저장 위치를 바꿀 수 있다.
- [x] `Transaction` dataclass에 `id/type/date/amount/category/memo/tags`를 정의한다.
- [x] `Transaction`, `Repository`, `BudgetService` 등 최소 2개 이상의 클래스를 사용한다.
- [x] 날짜·타입·양수 정수 금액·등록된 카테고리를 검증한다.

### 필수 기능 10개

- [x] **add**: 대화형 입력, 선택 메모·태그, 검증 후 저장, 생성 id 출력.
- [x] **list**: 거래일 최신순, 기본 20건, `--limit` 양수 검증, 스트리밍 조회.
- [x] **search**: `--from/--to/--category/--type/--q/--tag`, 복합 AND 조건, 최신순 결과.
- [x] **summary**: `--month/--top`, 총수입·총지출·잔액·카테고리 지출 TOP N, 빈 달 안내.
- [x] **budget**: `set`으로 저장·수정, `list`로 전체/월별 조회, 요약에 사용률·초과 경고 표시.
- [x] **category**: `add/list/remove`, 중복 등록 거부, 사용 중인 카테고리 삭제 금지.
- [x] **update**: `--id` 기반 옵션 방식, 지정 필드만 수정·재검증, 없는 id 오류.
- [x] **delete**: `--id` 기반 삭제, 없는 id 오류, 안전한 파일 교체.
- [x] **import**: UTF-8 CSV 헤더·행 검증, 새 id 생성, 처리 건수 출력, 오류 시 전체 취소.
- [x] **export**: 월 또는 시작일·종료일 조건 필수, 고정 CSV 스키마, 실제 파일 생성·건수 출력.

### 저장과 설계

- [x] `transactions.jsonl/categories.jsonl/budgets.jsonl` 세 파일에 영구 저장한다.
- [x] 첫 실행에 파일을 생성하고 빈 카테고리 파일에는 기본 카테고리를 등록한다.
- [x] `Repository.records()`와 `transactions()`에서 `yield`로 한 건씩 읽는다.
- [x] 목록·검색·요약·카테고리 사용 여부 확인에 제너레이터를 실제 연결한다.
- [x] 제한 조회는 힙, 무제한 검색은 임시 디스크 정렬로 전체 거래의 Python 리스트화를 피한다.
- [x] 모델·저장소·서비스·CLI를 최소 3개 이상의 모듈로 분리한다.
- [x] 주요 함수와 데이터 구조에 타입 힌트를 적용한다.
- [x] `@handle_errors` 데코레이터를 실제 CLI 진입점에 적용하고 `functools.wraps`를 사용한다.
- [x] 임시 파일 → `flush/fsync` → `os.replace`로 기존 파일을 안전하게 교체한다.
- [x] 잠금 파일로 동시에 실행되는 작업의 충돌을 막는다.

### 예외 처리와 문서·검증

- [x] 잘못된 날짜·월·빈 날짜 옵션, 0/음수/문자 금액, 잘못된 타입을 거부한다.
- [x] 미등록/중복 카테고리, 사용 중 카테고리 삭제, 없는 거래 id를 처리한다.
- [x] CSV 헤더·행 오류, 없는 파일, 조건 없는 export, 역전된 날짜 범위를 처리한다.
- [x] 손상된 JSONL과 유효하지 않은 저장 id를 거부하고 재작성 시 원본을 유지한다.
- [x] 예상 가능한 입력·파일 오류는 스택트레이스 대신 원인·해결 힌트를 출력한다.
- [x] 정상 `0`, 데이터·파일 오류 `1`, 문법 오류 `2`, 입력 중단 `130`으로 종료한다.
- [x] README에 실행법·저장 위치/형식·명령 예시·CSV 스키마와 정책을 명시한다.
- [x] 자동 테스트 18개로 정상 기능과 오류·원본 보존·5,000건 정렬을 검증한다.
- [x] 구현 커밋 `8af3c1c`의 GitHub Actions에서 Python 3.10/3.12/3.14 테스트가 성공했다.

### 선택 항목과 가이드와의 차이

| 항목 | 현재 선택과 이유 |
| --- | --- |
| 예산 조회 명령 | `budget list --month` 사용. 가이드의 `budget get`과 동일한 조회 목적을 충족한다. |
| CSV 일부 오류 | 전체 취소. 원래 미션은 오류 행 건너뛰기를 강제하지 않으며, 부분 반영을 피하는 정책을 문서화했다. |
| 거래 id | 순번 대신 UUID 사용. 예제의 `TX-000001`은 필수 형식이 아니다. |
| 모듈 이름/개수 | 현재 4개 주요 모듈로 책임 분리. 가이드의 파일 이름을 그대로 맞출 필요는 없다. |
| 원자성 강화 | 구현 완료. 거래뿐 아니라 카테고리와 예산 저장에도 적용한다. |
| 표 정렬 보너스 | 구분자와 타입 열 정렬만 제공한다. 전체 열 폭을 맞추는 표는 미구현이다. |
| backup / 반복 거래 | 선택 보너스로 미구현. 필수 기능 체크와 구분한다. |
