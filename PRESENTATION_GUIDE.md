# B2-1 구현 설명과 시연 가이드

이 문서는 실제 코드에 맞춘 설명 자료입니다. 미션 기준은 [WORK_LOG.md](WORK_LOG.md)의 2026-09-09 원문 요약이며, 아래 7장의 전체 요구사항 표와 함께 사용하세요. 발표 전에 아래 명령을 한 번 직접 실행하고 결과가 나오는 이유를 설명해 보세요.

## 1. 시작할 때 말할 1분 설명

> 제가 구현한 것은 Python 표준 라이브러리만으로 동작하는 콘솔 가계부입니다. 거래 추가·조회·검색·수정·삭제와 월별 요약, 예산, 카테고리, CSV 가져오기·내보내기를 제공합니다.
>
> 거래·카테고리·예산은 각각 JSONL 파일에 저장해서 프로그램이 끝나도 유지됩니다. 거래 파일은 제너레이터로 한 건씩 읽고, 최신순 조회에는 힙이나 임시 디스크 정렬을 사용했습니다.
>
> 특히 저장 도중 오류가 나더라도 기존 데이터가 남도록 임시 파일에 먼저 쓰고 완성된 뒤 교체했습니다. 입력 오류는 공통 예외 처리 데코레이터로 안내하고, 정상 기능뿐 아니라 실패했을 때 원본이 유지되는지도 테스트했습니다.

## 2. 코드를 보여줄 순서

| 열어 볼 파일과 위치 | 쉽게 설명할 내용 |
| --- | --- |
| [models.py](budget_app/models.py)의 `Transaction` | “거래 한 건에 어떤 정보가 필요한지 dataclass로 정의했습니다. 날짜·금액·타입을 검사한 뒤 객체를 만듭니다.” |
| [storage.py](budget_app/storage.py)의 `records`, `transactions` | “파일을 한 줄 읽을 때마다 `yield`로 거래를 전달합니다. 다음 거래는 요청받을 때 읽습니다.” |
| [service.py](budget_app/service.py)의 `filtered`, `newest`, `summary` | “검색 조건, 최신순 정렬, 합계 계산 같은 가계부 규칙을 처리합니다.” |
| [storage.py](budget_app/storage.py)의 `atomic_output` | “원본에 바로 쓰지 않고 새 파일을 완성한 뒤 교체합니다.” |
| [cli.py](budget_app/cli.py)의 `handle_errors`, `main` | “사용자 명령을 서비스에 전달하고, 공통 오류는 데코레이터로 처리합니다.” |
| [test_app.py](tests/test_app.py) | “파일 교체 실패와 잘못된 CSV를 일부러 만들어 원본이 유지되는지 확인합니다.” |

### 명령 하나가 처리되는 흐름

```text
python -m budget_app update --id ... --amount 18000
  ↓
__main__.py → cli.main(): 명령과 옵션 읽기
  ↓
Repository.session(): 다른 작업과 충돌하지 않도록 잠금
  ↓
BudgetService.change(): id 찾기 → 지정 필드 변경 → 다시 검증
  ↓
Repository.write() → atomic_output(): 임시 파일 작성 → 교체
  ↓
CLI: 성공 메시지 출력, 정상 종료 코드 0
```

없는 id나 잘못된 금액이면 임시 파일만 정리하고 원본은 유지합니다. 예외는 `@handle_errors`가 받아 안내 메시지와 실패 코드 `1`로 바꿉니다. 명령어 문법 오류는 `ArgumentParser.error()`에서 별도로 처리하여 코드 `2`로 종료합니다.

## 3. 약 5분 실행 시연

README와 `budget_app` 폴더가 있는 저장소 루트에서 **같은 터미널**로 순서대로 실행하세요. 아래는 macOS/Linux의 zsh/bash 예시입니다. `python3`를 사용하며 시연 폴더는 매번 새로 만듭니다.

먼저 `python3 --version`으로 **3.10 이상**인지 확인하세요. macOS 기본 Python은 3.9일 수 있습니다. 이 경우 설치된 `python3.12 --version` 등을 확인하고 아래 명령의 `python3`를 해당 실행 파일로 바꾸세요. 셸 별칭은 Python의 `subprocess`에 전달되지 않으므로 자동화 스크립트에서는 `sys.executable`로 현재 인터프리터를 사용하는 것이 정확합니다.

### 준비: 시연용 폴더와 기본 파일 생성

```sh
DEMO_DIR=$(mktemp -d)
python3 -m budget_app --data-dir "$DEMO_DIR/data" category list
```

기본 카테고리 다섯 개를 보여주며 “첫 실행에 JSONL 파일 세 개가 생성됩니다”라고 설명합니다. 실제 `./data` 대신 임시 폴더를 사용합니다. 다시 시연할 때는 준비 단계부터 새 폴더로 시작하세요.

### 거래 가져오기, 조회와 검색

```sh
python3 -m budget_app --data-dir "$DEMO_DIR/data" import --from examples/import.csv
python3 -m budget_app --data-dir "$DEMO_DIR/data" list --limit 3
python3 -m budget_app --data-dir "$DEMO_DIR/data" search --category food --tag meal
```

예상 결과는 `imported=4, skipped=0`, 최신 거래 최대 3건, 검색에서는 food 거래 45,000원 한 건입니다. “각 명령이 종료된 뒤 다음 명령에서도 데이터가 남습니다”라고 영속 저장을 설명합니다.

### 월별 요약과 예산 경고

```sh
python3 -m budget_app --data-dir "$DEMO_DIR/data" budget set --month 2024-01 --amount 500000
python3 -m budget_app --data-dir "$DEMO_DIR/data" budget list --month 2024-01
python3 -m budget_app --data-dir "$DEMO_DIR/data" summary --month 2024-01 --top 3
```

| 항목 | 예상 결과 |
| --- | --- |
| 총수입 | 3,000,000원 |
| 총지출 | 215,000원 |
| 잔액 | 2,785,000원 |
| 예산 사용률 | 43.0% |
| 지출 TOP 3 | rent 150,000원 → food 45,000원 → transport 20,000원 |

```sh
python3 -m budget_app --data-dir "$DEMO_DIR/data" budget set --month 2024-01 --amount 100000
python3 -m budget_app --data-dir "$DEMO_DIR/data" summary --month 2024-01
```

같은 월의 예산이 수정되고 사용률 **215.0%**와 초과 경고가 나옵니다.

### 직접 추가하고 수정·삭제

```sh
python3 -m budget_app --data-dir "$DEMO_DIR/data" category add --name books
python3 -m budget_app --data-dir "$DEMO_DIR/data" add
```

다음 여섯 값을 순서대로 입력합니다.

```text
2024-02-01
expense
books
10000
파이썬 책
study
```

성공 메시지의 `TX-...` id를 복사합니다. 다음 명령은 실행하면 id 입력을 기다리므로 복사한 값을 붙여넣고 엔터를 누르세요.

```sh
read -r DEMO_TX_ID
python3 -m budget_app --data-dir "$DEMO_DIR/data" update --id "$DEMO_TX_ID" --amount 12000
python3 -m budget_app --data-dir "$DEMO_DIR/data" search --category books
python3 -m budget_app --data-dir "$DEMO_DIR/data" category remove --name books
```

수정된 금액 12,000원을 확인합니다. 마지막 명령은 **의도적으로 실패**합니다. 거래가 사용하는 카테고리라 삭제를 막는 것이 정상입니다.

```sh
python3 -m budget_app --data-dir "$DEMO_DIR/data" delete --id "$DEMO_TX_ID"
python3 -m budget_app --data-dir "$DEMO_DIR/data" category remove --name books
```

거래 삭제 후에는 카테고리도 삭제할 수 있습니다.

### 내보내기와 오류 종료

```sh
python3 -m budget_app --data-dir "$DEMO_DIR/data" export --out "$DEMO_DIR/january.csv" --month 2024-01
cat "$DEMO_DIR/january.csv"
python3 -m budget_app --data-dir "$DEMO_DIR/data" delete --id DOES-NOT-EXIST
echo $?
```

CSV 헤더와 4건을 확인합니다. 없는 id 삭제는 원인과 힌트를 출력하며, 바로 다음 `echo $?`는 `1`입니다.

마지막으로 자동 테스트를 실행합니다.

```sh
python3 -m unittest discover -v
```

“21개의 테스트가 정상 동작과 실패 시 데이터 보존을 확인합니다. 현재 수정본은 Python 3.12에서 검증했고, 이전 구현은 Python 3.10·3.12·3.14에서 CI 검증을 통과했습니다”라고 설명할 수 있습니다.

## 4. 예상 질문과 답변

### JSONL을 고른 이유는 무엇인가요?

JSONL은 한 줄이 거래 한 건이라 한 줄씩 읽어 처리하기 쉽습니다. JSON 배열 전체를 한 번에 읽을 필요가 없어 제너레이터와 잘 맞습니다. CSV는 다른 프로그램과 데이터를 교환하는 용도로 사용했습니다.

### 제너레이터를 쓰면 파일 일부만 읽나요?

한 번에 메모리에 보관하는 양을 줄이는 것입니다. 최신 3건을 찾으려면 날짜가 섞인 파일 전체를 확인해야 합니다. `list --limit 3`은 모든 거래를 순회하지만 후보 3건만 힙에 유지합니다. 따라서 전체 거래 수와 무관하게 후보의 메모리 사용량을 제한합니다.

### 검색 전체를 최신순으로 보여주면서 어떻게 스트리밍하나요?

먼저 제너레이터로 읽고 필터링합니다. 제한 개수가 있으면 힙을 쓰고, 없으면 임시 SQLite 파일에 정렬할 데이터를 넣은 뒤 커서로 한 건씩 가져옵니다. 결과 전체를 Python 리스트로 만들지 않습니다. 정렬을 준비하는 시간과 임시 디스크 공간은 필요합니다. 영구 저장 파일은 여전히 JSONL 세 개입니다.

### Repository와 Service를 왜 나눴나요?

Repository는 파일을 읽고 쓰는 방법을 담당합니다. Service는 거래 검색, 합계, 사용 중인 카테고리 삭제 금지 같은 규칙을 담당합니다. CLI는 입력과 출력에 집중합니다. 수정할 책임이 어디에 있는지 찾기 쉽고 서비스를 콘솔 입력 없이 테스트할 수 있습니다.

### dataclass와 타입 힌트의 역할은 무엇인가요?

`Transaction` dataclass가 거래의 필드와 기본값을 명확히 합니다. `frozen=True`라 생성된 거래를 직접 변경하지 않고 검증한 새 거래로 수정합니다. `transactions() -> Iterator[Transaction]`은 거래를 한 건씩 돌려주는 함수라는 뜻입니다. 타입 힌트 자체가 입력을 검사하지는 않으므로 실제 검증 함수도 함께 사용합니다.

### 데코레이터는 어디에 적용했나요?

`cli.py`의 `main()` 위에 `@handle_errors`를 붙였습니다. 본래 함수 실행을 감싸서 예상 가능한 예외를 안내 메시지와 종료 코드로 바꿉니다. 여러 명령에 같은 예외 처리 코드를 반복하지 않도록 공통 처리했습니다. `functools.wraps`는 원래 함수의 이름과 설명 같은 정보를 유지합니다.

### 저장 중 오류가 나면 어떻게 되나요?

`atomic_output()`은 원본과 같은 폴더의 임시 파일에 쓰고 `flush()`와 `fsync()`를 실행한 뒤 `os.replace()`로 교체합니다. 교체 전에 검증이나 쓰기가 실패하면 원본을 유지합니다. 테스트에서는 `os.replace()`가 실패하도록 의도적으로 바꿔 원본 바이트가 그대로인지 확인했습니다.

### 여러 명령이 동시에 저장하면요?

`.lock` 파일을 배타적으로 만들어 한 번에 한 작업만 허용합니다. 다른 작업이 있으면 재시도 안내를 냅니다. 일반 종료에는 잠금을 제거하지만 강제 종료에는 남을 수 있어 복구 방법을 README에 적었습니다.

### 왜 잘못된 CSV 행만 건너뛰지 않았나요?

이번 구현은 전체 성공 또는 전체 취소를 선택했습니다. 정상 행 일부만 저장되어 사용자가 전체를 가져왔다고 오해하는 일을 피하기 위한 정책입니다. CSV를 수정해서 다시 가져올 때 부분 반영으로 인한 중복도 피할 수 있습니다. 단, 이미 성공한 파일을 다시 가져오면 새 id로 중복 등록됩니다. 원래 미션은 오류 행 건너뛰기를 강제하지 않습니다.

### 예산 조회는 왜 budget get이 아닌가요?

`budget list`로 전체를, `budget list --month YYYY-MM`로 해당 월을 조회합니다. 원래 미션의 설정/조회 기능을 충족하는 명령으로 선택하고 README에 명시했습니다.

### 어떤 테스트가 특히 중요한가요?

`test_replace_failure_preserves_original`은 저장 교체 실패, `test_csv_roundtrip_and_atomic_failure`는 CSV 왕복과 일부 행 오류 시 전체 취소를 확인합니다. `test_large_streaming_order`는 5,000건의 정렬을 확인합니다. 이후 빈 날짜 옵션, 손상된 null id, 문법 오류 안내를 확인하는 회귀 테스트도 추가했습니다.

### 현재 한계나 다음 개선점은 무엇인가요?

거래 추가도 원본을 재작성하므로 데이터가 커지면 시간이 늘고 임시 디스크 공간이 필요합니다. 전원 장애의 모든 상황이나 파일 세 개를 동시에 바꾸는 트랜잭션까지 보장하지는 않습니다. 백업 명령, 반복 거래, 전체 열 폭을 맞춘 표 출력은 선택 보너스로 남겨 두었습니다.

## 5. 발표 직전 확인

- [ ] 이 문서의 필수 기능 10개를 각 명령과 연결해 설명할 수 있다.
- [ ] 새 임시 폴더에서 위 시연을 한 번 끝까지 실행했다.
- [ ] 215,000원 지출과 43.0% 사용률의 계산을 설명할 수 있다.
- [ ] `yield`가 파일 전체를 읽지 않는다는 뜻과 다름을 설명할 수 있다.
- [ ] 데코레이터, 타입 힌트, 원자적 교체를 실제 함수에서 가리킬 수 있다.
- [ ] 의도적인 실패와 종료 코드 `1`을 보여줄 수 있다.
- [ ] 구현한 기능과 선택 보너스, 데이터 보호의 한계를 구분해 말할 수 있다.

이 항목은 발표자의 직접 준비 확인용이므로 실행·연습한 뒤 체크하세요.


## 6. 비전공자용 5~7분 설명 대본

파일 역할은 [FILE_GUIDE.md](FILE_GUIDE.md), 단계별 공부 순서는 [MISSION_GUIDE.md](MISSION_GUIDE.md)에 있습니다. 이 프로젝트는 웹 화면의 이벤트·DOM이 아니라 **명령 입력 → 검증 → 업무 처리 → 파일 저장 → 결과 출력**을 설명합니다.

### 0~1분: 무엇을 만들었나요?

> “터미널에서 명령을 입력하는 가계부입니다. add로 거래를 만들고 list/search로 조회하며 update/delete로 수정·삭제합니다. 이를 CRUD라고 부릅니다. 월별 합계와 예산도 확인하고 CSV로 다른 프로그램과 데이터를 주고받습니다. Python 3.10 이상과 기본 제공 도구만 사용하므로 pip 설치가 필요하지 않습니다.”

**시연:** `--help`와 거래 목록을 보여 줍니다. 터미널은 글로 명령을 주고받는 창이고, 옵션은 명령에 붙이는 조건입니다.

### 1~2분: 파일을 왜 나눴나요?

> “models는 거래의 항목과 값 검사를, storage는 읽고 쓰는 방법을, service는 가계부 규칙을, cli는 명령 입력과 결과 출력을 맡습니다. Transaction은 거래 한 건, Repository는 저장 담당, BudgetService는 업무 담당 클래스입니다. 클래스는 관련 데이터와 기능을 묶는 틀입니다.”

**코드:** models.Transaction → storage.Repository → service.BudgetService → cli.main 순서로 짚습니다. 최소 클래스 2개·모듈 3개 조건과 실제 구조를 연결합니다.

### 2~3분: 데이터가 어떻게 남나요?

> “프로그램의 메모리 값은 종료하면 사라지지만 파일로 저장하면 다시 읽을 수 있습니다. 거래·카테고리·예산을 JSONL 세 파일에 저장합니다. 한 줄에 한 기록이므로 yield로 한 건씩 전달하기 좋습니다. 처음 실행하면 파일을 만들고 기본 분류를 등록합니다.”

**시연:** 임시 폴더에서 import 후 별도 list 명령을 실행합니다. 기본 분류는 food/transport/rent/etc/salary입니다. 저장 위치는 --data-dir로 바꿀 수 있습니다.

### 3~4분: 많은 데이터와 공통 처리는요?

> “제너레이터는 값을 한 번에 모으지 않고 필요할 때 한 건씩 전달합니다. 최신 N건은 힙이라는 후보 관리 구조로 N개만 보관하고, 무제한 결과는 임시 디스크에서 정렬합니다. 날짜가 섞여 있으면 전체를 읽어야 하므로 언제나 즉시 결과가 나오는 것은 아닙니다.”
>
> “데코레이터는 기존 함수를 감싸 공통 동작을 붙이는 방법입니다. handle_errors가 예상 가능한 오류를 원인과 힌트로 바꿉니다. 타입 힌트는 함수가 어떤 값을 받거나 주는지 알려 주지만, 입력을 자동 검사하지는 않습니다.”

**코드:** newest, transactions의 yield, main 위 @handle_errors, Iterator[Transaction].

### 4~5분: 수정·삭제에 실패하면요?

> “원본을 지우고 쓰는 대신 임시 파일을 먼저 완성하고 교체합니다. 없는 id, 잘못된 금액, 저장 오류가 발생하면 원본을 유지합니다. 동시에 두 작업이 실행되지 않도록 잠금 파일도 사용합니다. CSV는 한 행이라도 잘못되면 전체 가져오기를 취소합니다.”

**시연:** 없는 id 삭제와 사용 중 카테고리 삭제를 보여 줍니다. `@handle_errors`와 atomic_output은 다른 역할입니다. 전자는 안내, 후자는 파일 교체입니다. 원자적 교체는 백업과 같은 뜻이 아닙니다.

### 5~7분: 계산·검증과 한계

> “예제의 수입은 300만 원, 지출은 21만 5천 원이고 차액은 278만 5천 원입니다. 예산 50만 원에 대한 지출 비율은 43%입니다. 10만 원으로 예산을 바꾸면 215%여서 초과 경고를 보여 줍니다. 큰 정수도 처리하도록 비율은 정수 계산을 사용합니다.”
>
> “자동 검사는 별도 테스트 파일에서 임시 데이터를 사용합니다. 정상 동작뿐 아니라 CSV 오류와 저장 실패도 확인합니다. 구현 검증과 실제 채점 결과는 다릅니다. 백업 명령과 반복 거래는 아직 구현하지 않은 선택 기능입니다.”

**시연:** 3장의 summary·budget 명령과 오류 종료 코드. 2026-09-10 문서 정리 후에도 Python 3.12.13에서 기존 21개 테스트가 모두 통과했습니다. 2026-09-07의 이전 CI는 당시 18개 검사였으며 현재 커밋의 CI 결과는 별도 확인이 필요합니다. 이번 문서 정리는 아직 원격에 반영하지 않았습니다.

## 7. 미션 전체 요구사항 설명 준비표

체크는 발표자가 **직접 설명·시연할 준비가 됐는지** 표시합니다. 실제 채점 결과나 자동 합격 표시는 아닙니다. 원문에 없는 웹 배포·스크린샷 제출 조건을 추가하지 않습니다.

| 준비 | 요구사항 | 코드·설명 위치 |
| --- | --- | --- |
| [ ] | Python 3.10 이상, 표준 라이브러리만 사용, 외부 pip 의존성 없음 | README 실행, 각 모듈 import |
| [ ] | python -m budget_app, 모든 명령·하위 명령 --help, 긴 옵션 -- | __main__, cli.parser, 3장 |
| [ ] | add는 input 기반 순차 입력, 날짜·타입·분류·양수 금액 검증, 성공 id, 선택 메모/태그 | cli.main, Transaction.create, checked |
| [ ] | list 기본값·--limit, 최신순 제너레이터 | parser 기본 20, newest |
| [ ] | search --from/--to/--category/--type/--q/--tag, 최신순 스트리밍 | filtered, newest |
| [ ] | update --id와 선택 date/type/category/amount/memo/tags, 옵션 방식 README 명시 | change, README 수정/삭제 |
| [ ] | delete --id, 없는 id 안내, 안전한 재작성 | change, atomic_output |
| [ ] | summary --month/--top, 수입·지출·잔액·지출 TOP N, 빈 달 안내 | summary, cli.main |
| [ ] | budget set 월·금액, 조회, 영구 저장, 사용률·초과 경고 | set_budget, budgets, percentage |
| [ ] | category add/list/remove, 사용 중 분류 삭제 차단 | category, categories |
| [ ] | import --from CSV 일괄 등록·건수·반영 안내 | import_csv, 전체 취소 정책 |
| [ ] | export --out, 월 또는 시작/종료 기간, CSV 실제 생성·건수 | export_csv, README 조건 |
| [ ] | 유일 id, income/expense, 날짜, 양수 amount, category, 선택 memo/tags | Transaction |
| [ ] | dataclass 또는 동등 구조, 클래스 2개 이상·모듈 3개 이상 | Transaction/Repository/BudgetService, 주요 4모듈 |
| [ ] | 함수·데이터 구조 타입 힌트, 실제 이점 설명 | Iterator[Transaction], 4·6장 |
| [ ] | JSONL/CSV 중 저장 선택, 세 파일 이상, 위치 변경, 초기 파일 정책 | Repository.initialize, --data-dir |
| [ ] | 빈 카테고리 파일 정책 명시 | 기본 5개 자동 등록, README |
| [ ] | yield 기반 list/search, 전체 거래를 한 번에 메모리에 읽지 않기 | records, transactions, newest; 정렬 한계 4장 |
| [ ] | 실제 사용하는 공통 데코레이터 최소 1개 | @handle_errors, wraps |
| [ ] | 오류 원인·힌트, 예상 오류의 traceback 방지, 정상 0·오류 비0 | cli, 0/1/2/130 |
| [ ] | 수정/삭제 저장 안정성 고려 | atomic_output, 4장 한계 |
| [ ] | UTF-8 헤더 CSV, date/type/category/amount 필수, memo/tags 선택 | CSV_FIELDS, README CSV 표 |
| [ ] | tags 쉼표 구분, amount 양수 정수 | Transaction.create, positive |
| [ ] | README 실행·저장 위치/형식·주요 명령·CSV 스키마·update 방식·초기 분류 정책 | README의 해당 절 모두 유지 |
| [ ] | CRUD·검색·요약·입출력과 영속 저장을 설명 | 1·3·6장 |
| [ ] | 책임 분리·제너레이터·데코레이터·타입 힌트의 이유 설명 | 2·4·6장 |
| [ ] | 선택: 타임스탬프 백업, 반복 거래 | 전용 명령 미구현 |
| [ ] | 선택: 정렬된 표 출력 | 구분자·타입 열만 정렬, 전체 열 폭 정렬 미구현 |
| [ ] | 권장/선택: 임시 파일 후 rename에 의한 원자성 강화 | os.replace로 구현 |
| [ ] | 출력 예시는 참고, 고정 id 형식·skipped 정책 강제 아님 | UUID, CSV 전체 취소, WORK_LOG 원문 해석 |

## 8. 기존 구현 근거와 선택 사항

다음은 기존 README에 있던 구현 근거를 옮긴 내용입니다. 위 설명 준비표와 달리 코드·과거 검증에 대한 기록이며 실제 채점 결과를 뜻하지 않습니다.

### 구현 확인 기록

아래 체크는 **원래 미션의 필수 요구사항과 현재 구현**을 기준으로 합니다.

#### 실행과 데이터 모델

- [x] Python 3.10 이상, 표준 라이브러리만 사용하며 별도 설치가 필요 없다.
- [x] `python -m budget_app <command>`로 실행하고 모든 명령·하위 명령에 `--help`를 제공한다.
- [x] 긴 옵션을 `--`로 통일하고 `--data-dir`로 저장 위치를 바꿀 수 있다.
- [x] `Transaction` dataclass에 `id/type/date/amount/category/memo/tags`를 정의한다.
- [x] `Transaction`, `Repository`, `BudgetService` 등 최소 2개 이상의 클래스를 사용한다.
- [x] 날짜·타입·양수 정수 금액·등록된 카테고리를 검증한다.

#### 필수 기능 10개

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

#### 저장과 설계

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

#### 예외 처리와 문서·검증

- [x] 잘못된 날짜·월·빈 날짜 옵션, 0/음수/문자 금액, 잘못된 타입을 거부한다.
- [x] 미등록/중복 카테고리, 사용 중 카테고리 삭제, 없는 거래 id를 처리한다.
- [x] CSV 헤더·행 오류, 없는 파일, 조건 없는 export, 역전된 날짜 범위를 처리한다.
- [x] 손상된 JSONL과 유효하지 않은 저장 id를 거부하고 재작성 시 원본을 유지한다.
- [x] 예상 가능한 입력·파일 오류는 스택트레이스 대신 원인·해결 힌트를 출력한다.
- [x] 정상 `0`, 데이터·파일 오류 `1`, 문법 오류 `2`, 입력 중단 `130`으로 종료한다.
- [x] README에 실행법·저장 위치/형식·명령 예시·CSV 스키마와 정책을 명시한다.
- [x] 자동 테스트 21개로 정상 기능과 오류·원본 보존·5,000건 정렬을 검증한다.
- [x] 구현 커밋 `8af3c1c`의 GitHub Actions에서 Python 3.10/3.12/3.14 테스트가 성공했다.

#### 선택 항목과 가이드와의 차이

| 항목 | 현재 선택과 이유 |
| --- | --- |
| 예산 조회 명령 | `budget list --month` 사용. 가이드의 `budget get`과 동일한 조회 목적을 충족한다. |
| CSV 일부 오류 | 전체 취소. 원래 미션은 오류 행 건너뛰기를 강제하지 않으며, 부분 반영을 피하는 정책을 문서화했다. |
| 거래 id | 순번 대신 UUID 사용. 예제의 `TX-000001`은 필수 형식이 아니다. |
| 모듈 이름/개수 | 현재 4개 주요 모듈로 책임 분리. 가이드의 파일 이름을 그대로 맞출 필요는 없다. |
| 원자성 강화 | 구현 완료. 거래뿐 아니라 카테고리와 예산 저장에도 적용한다. |
| 표 정렬 보너스 | 구분자와 타입 열 정렬만 제공한다. 전체 열 폭을 맞추는 표는 미구현이다. |
| backup / 반복 거래 | 선택 보너스로 미구현. 필수 기능 체크와 구분한다. |


## 2026-09-10 코드 정리 후 읽는 방법

cli.py의 `main()`은 명령을 골라 `run_add`, `run_update`, `run_summary` 등 해당 `run_명령` 함수로 전달합니다. 각 함수가 입력·출력을 담당하고 실제 처리 규칙은 BudgetService에 있습니다. 수정 흐름은 `main → run_update → service.change → Repository.write → atomic_output`입니다.

service.py의 `filtered()`는 검색 조건을 하나씩 검사하고 맞지 않으면 `continue`로 다음 거래로 넘어갑니다. 모두 통과하면 `yield`로 거래를 전달합니다. 추가·수정은 중간 변수로 데이터 변환 순서를 보여 줍니다. 저장 방식·잠금·최신순 정렬·입력 검증과 출력은 유지했습니다. 코드 정리 후 기존 테스트 21개가 Python 3.12에서 모두 통과했습니다.
