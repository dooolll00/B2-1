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


class BudgetService:
    def __init__(self, repository: Repository):
        self.repo = repository

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
            if any(t.category == name for t in self.repo.transactions()):
                raise AppError("사용 중인 카테고리입니다. 거래를 수정/삭제한 뒤 다시 시도하세요.")
            names.remove(name)
        self.repo.write("categories", ({"name": n} for n in names))

    def checked(self, **values: Any) -> Transaction:
        t = Transaction.create(**values)
        if t.category not in self.categories():
            raise AppError("등록되지 않은 카테고리입니다. category list 또는 category add를 사용하세요.")
        return t

    def add(self, **values: Any) -> Transaction:
        t = self.checked(**values)
        self.repo.write("transactions", (x.record() for x in chain(self.repo.transactions(), [t])))
        return t

    def change(self, id: str, values: dict[str, Any] | None) -> None:
        found = False
        def rows() -> Iterator[dict[str, Any]]:
            nonlocal found
            for t in self.repo.transactions():
                if t.id == id:
                    if found:
                        raise AppError("중복 id로 파일이 손상되었습니다. 백업을 복원하세요.")
                    found = True
                    if values is not None:
                        yield self.checked(**(t.record() | values)).record()
                else:
                    yield t.record()
            if not found:
                raise AppError("없는 데이터입니다. list에서 id를 확인하세요.")
        self.repo.write("transactions", rows())

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
            if (not start or t.date >= start) and (not end or t.date <= end) and (not month or t.date.startswith(month)) and (category is None or t.category == category) and (not type or t.type == type) and (q is None or q.casefold() in t.memo.casefold()) and (tag is None or tag in t.tags):
                yield t

    def newest(self, limit: int | None = None, **filters: Any) -> Iterator[Transaction]:
        if limit is not None:
            # 거래일이 같으면 파일 뒤에 추가된 거래를 먼저 표시. 메모리 O(limit).
            rows = heapq.nlargest(positive(limit), enumerate(self.filtered(**filters)), key=lambda item: (item[1].date, item[0]))
            yield from (t for _, t in rows)
        else:
            # 무제한 검색도 메모리에 전체 목록을 올리지 않는다. 디스크 임시 정렬.
            with tempfile.TemporaryDirectory(prefix="budget-sort-") as directory:
                with sqlite3.connect(str(Path(directory) / "sort.db")) as db:
                    db.execute("PRAGMA temp_store=FILE")
                    db.execute("PRAGMA cache_size=-2048")
                    db.execute("CREATE TABLE rows (seq INTEGER, date TEXT, record TEXT)")
                    db.executemany("INSERT INTO rows VALUES (?, ?, ?)", ((i, t.date, json.dumps(t.record())) for i, t in enumerate(self.filtered(**filters))))
                    for (record,) in db.execute("SELECT record FROM rows ORDER BY date DESC, seq DESC"):
                        yield Transaction.create(**json.loads(record))

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
        budgets[month] = amount_value
        self.repo.write("budgets", ({"month": m, "amount": a} for m, a in sorted(budgets.items())))

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

    def import_csv(self, path: Path) -> int:
        count = 0
        def imported() -> Iterator[dict[str, Any]]:
            nonlocal count
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, strict=True)
                headers = reader.fieldnames
                if not headers or not set(CSV_FIELDS[:4]).issubset(headers) or len(headers) != len(set(headers)) or set(headers) - set(CSV_FIELDS):
                    raise AppError("CSV 헤더 오류. README의 date,type,category,amount,memo,tags 스키마를 확인하세요.")
                for row in reader:
                    try:
                        if None in row or any(v is None for v in row.values()):
                            raise AppError("열 개수가 맞지 않습니다. 쉼표가 있는 값은 큰따옴표로 감싸세요.")
                        yield self.checked(**row).record()
                        count += 1
                    except (AppError, TypeError, ValueError) as exc:
                        raise AppError(f"CSV {reader.line_num}행 오류: {exc} 전체 가져오기를 취소했습니다.") from exc
        self.repo.write("transactions", chain((t.record() for t in self.repo.transactions()), imported()))
        return count

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
                del row["id"]
                row["tags"] = ",".join(t.tags)
                writer.writerow(row)
                count += 1
        return count
