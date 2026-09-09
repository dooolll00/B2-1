# B2-1 구현 설명과 시연 가이드

이 문서는 실제 코드에 맞춘 설명 자료입니다. [README의 체크리스트](README.md#미션-구현-체크리스트)와 함께 사용하세요. 발표 전에 아래 명령을 한 번 직접 실행하고 결과가 나오는 이유를 설명해 보세요.

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

- [ ] README의 필수 기능 10개를 각 명령과 연결해 설명할 수 있다.
- [ ] 새 임시 폴더에서 위 시연을 한 번 끝까지 실행했다.
- [ ] 215,000원 지출과 43.0% 사용률의 계산을 설명할 수 있다.
- [ ] `yield`가 파일 전체를 읽지 않는다는 뜻과 다름을 설명할 수 있다.
- [ ] 데코레이터, 타입 힌트, 원자적 교체를 실제 함수에서 가리킬 수 있다.
- [ ] 의도적인 실패와 종료 코드 `1`을 보여줄 수 있다.
- [ ] 구현한 기능과 선택 보너스, 데이터 보호의 한계를 구분해 말할 수 있다.

이 항목은 발표자의 직접 준비 확인용이므로 실행·연습한 뒤 체크하세요.
