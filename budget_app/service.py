"""가계부 규칙. 거래 파일은 언제나 제너레이터로 읽는다."""
import csv
import heapq
from itertools import chain
from pathlib import Path
import json
import sqlite3
import tempfile
from typing import Any, Iterator
from .models import AppError, Transaction, positive, valid_date, valid_month
from .storage import Repository, atomic_output

CSV_FIELDS = ("date", "type", "category", "amount", "memo", "tags")


# 가계부의 업무 규칙을 담당합니다. 실제 파일 읽기·쓰기는 Repository에 맡깁니다.
class BudgetService:
    def __init__(self, repository: Repository):
        self.repo = repository

    # 거래와 달리 작은 설정 목록인 카테고리는 리스트로 관리합니다.
    def categories(self) -> list[str]:
        result = []
        for row in self.repo.records("categories"):
            name = row.get("name")
            if not isinstance(name, str) or not name.strip():
                raise AppError("카테고리 파일 손상. name 문자열을 확인하거나 백업을 복원하세요.")
            result.append(name)
        return result

    def category(self, action: str, name: str) -> None:
        name = name.strip()
        names = self.categories()
        if not name:
            raise AppError("카테고리 이름을 입력하세요.")
        if action == "add":
            if name in names:
                raise AppError("이미 등록된 카테고리입니다. category list로 확인하세요.")
            names.append(name)
        else:
            if name not in names:
                raise AppError("없는 카테고리입니다. category list로 확인하세요.")
            # 기존 거래가 사용하는 분류를 지우면 연결이 끊어지므로 삭제를 막습니다.
            if any(t.category == name for t in self.repo.transactions()):
                raise AppError("사용 중인 카테고리입니다. 거래를 수정/삭제한 뒤 다시 시도하세요.")
            names.remove(name)
        self.repo.write("categories", ({"name": n} for n in names))

    # 모델의 입력 검사에 더해, 카테고리가 실제 등록되어 있는지 확인합니다.
    def checked(self, **values: Any) -> Transaction:
        t = Transaction.create(**values)
        if t.category not in self.categories():
            raise AppError("등록되지 않은 카테고리입니다. category list 또는 category add를 사용하세요.")
        return t

    def add(self, **values: Any) -> Transaction:
        t = self.checked(**values)
        # chain은 기존 거래를 읽은 뒤 새 거래를 전달합니다. 전체 거래 리스트를 만들지 않습니다.
        transactions = chain(self.repo.transactions(), [t])
        records = (transaction.record() for transaction in transactions)
        self.repo.write("transactions", records)
        return t

    # 수정과 삭제는 같은 파일 재작성 흐름을 씁니다. values가 None이면 삭제입니다.
    def change(self, id: str, values: dict[str, Any] | None) -> None:
        found = False
        def rows() -> Iterator[dict[str, Any]]:
            # 안쪽 함수에서도 바깥의 found를 바꿔 대상 거래를 찾았는지 기록합니다.
            nonlocal found
            for t in self.repo.transactions():
                if t.id == id:
                    if found:
                        raise AppError("중복 id로 파일이 손상되었습니다. 백업을 복원하세요.")
                    found = True
                    # 수정이면 바뀐 거래를 전달합니다. 삭제이면 전달하지 않아 새 파일에서 빠집니다.
                    if values is not None:
                        updated_values = t.record()
                        # 요청한 필드만 바꾸고 나머지 값과 id는 유지합니다.
                        updated_values.update(values)
                        updated = self.checked(**updated_values)
                        yield updated.record()
                else:
                    yield t.record()
            # 없는 id 오류도 임시 파일 작성 중에 발생하므로 원본은 교체되지 않습니다.
            if not found:
                raise AppError("없는 데이터입니다. list에서 id를 확인하세요.")
        self.repo.write("transactions", rows())

    # 모든 검색 조건을 만족하는 거래만 한 건씩 전달합니다(AND 검색).
    def filtered(self, *, start: str | None = None, end: str | None = None,
                 month: str | None = None, category: str | None = None,
                 type: str | None = None, q: str | None = None,
                 tag: str | None = None) -> Iterator[Transaction]:
        if start is not None:
            valid_date(start)
        if end is not None:
            valid_date(end)
        if start and end and start > end:
            raise AppError("시작일이 종료일보다 늦습니다. --from/--to를 확인하세요.")
        if month is not None:
            valid_month(month)
        if category is not None and category not in self.categories():
            raise AppError("등록되지 않은 카테고리입니다. category list로 확인하세요.")
        for t in self.repo.transactions():
            # 조건에 맞지 않으면 다음 거래로 넘어갑니다. 모두 통과한 거래만 전달합니다.
            if start and t.date < start:
                continue
            if end and t.date > end:
                continue
            if month and not t.date.startswith(month):
                continue
            if category is not None and t.category != category:
                continue
            if type and t.type != type:
                continue
            if q is not None and q.casefold() not in t.memo.casefold():
                continue
            if tag is not None and tag not in t.tags:
                continue
            yield t

    # 최신순 정렬에는 전체 후보 확인이 필요합니다. limit 유무에 따라 메모리 절약 방법을 나눕니다.
    def newest(self, limit: int | None = None, **filters: Any) -> Iterator[Transaction]:
        if limit is not None:
            # 거래일이 같으면 파일 뒤에 추가된 거래를 먼저 표시. 메모리 O(limit).
            # nlargest는 최신 N건의 후보만 보관하며, enumerate의 순번으로 같은 날짜의 순서를 정합니다.
            rows = heapq.nlargest(positive(limit), enumerate(self.filtered(**filters)), key=lambda item: (item[1].date, item[0]))
            yield from (t for _, t in rows)
        else:
            # 무제한 검색도 메모리에 전체 목록을 올리지 않는다. 디스크 임시 정렬.
            # SQLite는 표준 라이브러리이며 임시 정렬에만 씁니다. 영구 저장은 JSONL입니다.
            with tempfile.TemporaryDirectory(prefix="budget-sort-") as directory:
                with sqlite3.connect(str(Path(directory) / "sort.db")) as db:
                    db.execute("PRAGMA temp_store=FILE")
                    db.execute("PRAGMA cache_size=-2048")
                    db.execute("CREATE TABLE rows (seq INTEGER, date TEXT, record TEXT)")
                    db.executemany("INSERT INTO rows VALUES (?, ?, ?)", ((i, t.date, json.dumps(t.record())) for i, t in enumerate(self.filtered(**filters))))
                    # 정렬 결과도 한 건씩 전달합니다. with가 끝나면 임시 폴더를 정리합니다.
                    for (record,) in db.execute("SELECT record FROM rows ORDER BY date DESC, seq DESC"):
                        yield Transaction.create(**json.loads(record))

    # 월을 키로, 금액을 값으로 읽어 해당 월의 예산을 쉽게 찾게 합니다.
    def budgets(self) -> dict[str, int]:
        result = {}
        for row in self.repo.records("budgets"):
            try:
                result[valid_month(row["month"])] = positive(row["amount"])
            except (KeyError, TypeError, AppError) as exc:
                raise AppError("예산 파일 손상. month/amount를 확인하거나 백업을 복원하세요.") from exc
        return result

    def set_budget(self, month: str, amount: str) -> None:
        month, amount_value = valid_month(month), positive(amount)
        budgets = self.budgets()
        # 같은 월은 갱신하고, 새로운 월은 추가한 뒤 파일에 저장합니다.
        budgets[month] = amount_value
        self.repo.write("budgets", ({"month": m, "amount": a} for m, a in sorted(budgets.items())))

    # 거래를 모아 두지 않고 합계만 누적합니다. 카테고리별 합계에는 지출만 포함합니다.
    def summary(self, month: str) -> dict[str, Any]:
        income = expense = count = 0
        categories: dict[str, int] = {}
        for t in self.filtered(month=month):
            count += 1
            if t.type == "income":
                income += t.amount
            else:
                expense += t.amount
                categories[t.category] = categories.get(t.category, 0) + t.amount
        return dict(income=income, expense=expense, count=count, categories=categories, budget=self.budgets().get(month))

    # 한 행이라도 잘못되면 전체 가져오기를 취소하는 정책입니다.
    def import_csv(self, path: Path) -> int:
        count = 0
        # CSV 행마다 분류 파일을 다시 읽지 않도록 목록을 한 번 준비합니다.
        category_names = set(self.categories())
        def imported() -> Iterator[dict[str, Any]]:
            nonlocal count
            with path.open(encoding="utf-8-sig", newline="") as stream:
                # 첫 줄의 열 이름을 키로 사용합니다. 필수 4개 열과 허용된 선택 열을 검사합니다.
                reader = csv.DictReader(stream, strict=True)
                headers = reader.fieldnames
                if not headers or not set(CSV_FIELDS[:4]).issubset(headers) or len(headers) != len(set(headers)) or set(headers) - set(CSV_FIELDS):
                    raise AppError("CSV 헤더 오류. README의 date,type,category,amount,memo,tags 스키마를 확인하세요.")
                for row in reader:
                    try:
                        if None in row or any(v is None for v in row.values()):
                            raise AppError("열 개수가 맞지 않습니다. 쉼표가 있는 값은 큰따옴표로 감싸세요.")
                        transaction = Transaction.create(**row)
                        if transaction.category not in category_names:
                            raise AppError("등록되지 않은 카테고리입니다. category list 또는 category add를 사용하세요.")
                        yield transaction.record()
                        count += 1
                    except (AppError, TypeError, ValueError) as exc:
                        raise AppError(f"CSV {reader.line_num}행 오류: {exc} 전체 가져오기를 취소했습니다.") from exc
        # 기존 거래와 새 행을 임시 파일에 씁니다. 모든 행이 통과해야 원본에 반영됩니다.
        self.repo.write("transactions", chain((t.record() for t in self.repo.transactions()), imported()))
        return count

    # 월 또는 시작·종료일 조건을 요구하고 저장 데이터 폴더 밖으로 CSV를 내보냅니다.
    def export_csv(self, path: Path, **filters: Any) -> int:
        if filters.get("month") is None and (filters.get("start") is None or filters.get("end") is None):
            raise AppError("내보내기 조건이 필요합니다. --month 또는 --from과 --to를 함께 지정하세요.")
        if filters.get("month") is not None and (filters.get("start") is not None or filters.get("end") is not None):
            raise AppError("--month와 기간 조건 중 한 방식만 선택하세요.")
        if path.resolve().parent == self.repo.directory:
            raise AppError("저장 데이터 보호를 위해 data 폴더 밖의 CSV 경로를 지정하세요.")
        count = 0
        with atomic_output(path) as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for t in self.newest(**filters):
                row = t.record()
                # 교환용 CSV에는 id를 넣지 않습니다. 다시 가져올 때 새 id로 등록합니다.
                del row["id"]
                # 태그 묶음을 CSV 규격의 쉼표 구분 문자열로 바꿉니다.
                row["tags"] = ",".join(t.tags)
                writer.writerow(row)
                count += 1
        return count
