import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from budget_app.models import AppError, Transaction
from budget_app.service import BudgetService
from budget_app.storage import Repository


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = Repository(self.root / "data")
        self.repo.initialize()
        self.service = BudgetService(self.repo)

    def add(self, **values):
        return self.service.add(**(dict(type="expense", date="2024-01-15", amount=100, category="food", memo="점심", tags="meal,work") | values))

    def cli(self, *args, input=None):
        return subprocess.run([sys.executable, "-m", "budget_app", "--data-dir", str(self.repo.directory), *args], input=input, capture_output=True, text=True)

    def test_initialization_and_persistence(self):
        self.assertEqual(len(list(self.repo.directory.glob("*.jsonl"))), 3)
        t = self.add()
        self.assertEqual(next(Repository(self.repo.directory).transactions()), t)

    def test_validation(self):
        for values in ({"date": "2024-02-30"}, {"date": "2024-1-01"}, {"amount": 0}, {"amount": -1}, {"amount": "1.2"}, {"type": "other"}, {"category": "missing"}):
            with self.subTest(values=values), self.assertRaises(AppError):
                self.add(**values)
        self.assertEqual(list(self.repo.transactions()), [])

    def test_latest_and_combined_search(self):
        first = self.add(date="2024-02-01")
        self.add(date="2023-12-31")
        last = self.add(date="2024-02-01", amount=200)
        self.assertEqual([t.id for t in self.service.newest(limit=2)], [last.id, first.id])
        rows = list(self.service.newest(start="2024-02-01", end="2024-02-29", category="food", type="expense", q="점", tag="work"))
        self.assertEqual([t.id for t in rows], [last.id, first.id])
        with self.assertRaises(AppError):
            list(self.service.filtered(start="2024-02-01", end="2024-01-01"))

    def test_update_delete_and_rollback(self):
        t = self.add()
        self.service.change(t.id, {"amount": "350", "memo": "", "tags": ""})
        changed = next(self.repo.transactions())
        self.assertEqual((changed.amount, changed.memo, changed.tags), (350, "", ()))
        before = self.repo.path("transactions").read_bytes()
        for id, values in (("missing", None), (t.id, {"amount": "0"}), (t.id, {"category": "missing"})):
            with self.assertRaises(AppError):
                self.service.change(id, values)
            self.assertEqual(before, self.repo.path("transactions").read_bytes())
        self.service.change(t.id, None)
        self.assertEqual(list(self.repo.transactions()), [])

    def test_category_usage(self):
        self.service.category("add", "books")
        t = self.add(category="books")
        with self.assertRaises(AppError):
            self.service.category("remove", "books")
        self.service.change(t.id, None)
        self.service.category("remove", "books")
        self.assertNotIn("books", self.service.categories())

    def test_summary_budget_persistence(self):
        self.add(amount=150)
        self.add(amount=1000, type="income", category="salary")
        self.add(amount=50, category="rent")
        self.service.set_budget("2024-01", "100")
        s = BudgetService(Repository(self.repo.directory)).summary("2024-01")
        self.assertEqual((s["income"], s["expense"], s["budget"]), (1000, 200, 100))
        result = self.cli("summary", "--month", "2024-01", "--top", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("200.0%", result.stdout)
        self.assertIn("예산 초과", result.stdout)
        self.assertIn("데이터 없음", self.cli("summary", "--month", "2025-01").stdout)

    def test_summary_large_amounts(self):
        self.add(amount=10 ** 309)
        self.service.set_budget("2024-01", "1")
        result = self.cli("summary", "--month", "2024-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"사용률 {10 ** 311}.0%", result.stdout)
        self.assertIn("예산 초과", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_summary_percentage_rounding(self):
        t = self.add(amount=1)
        for expense, budget, expected in ((1, 16, "6.2"), (3, 16, "18.8"),
                                           (1, 3, "33.3"), (2, 3, "66.7")):
            with self.subTest(expense=expense, budget=budget):
                self.service.change(t.id, {"amount": expense})
                self.service.set_budget("2024-01", str(budget))
                result = self.cli("summary", "--month", "2024-01")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"사용률 {expected}%", result.stdout)

    def test_import_unknown_category_rolls_back(self):
        self.add()
        before = self.repo.path("transactions").read_bytes()
        path = self.root / "invalid-category.csv"
        path.write_text("date,type,category,amount\n2024-01-01,expense,food,100\n"
                        "2024-01-02,expense,missing,200\n", encoding="utf-8")
        with self.assertRaisesRegex(AppError, "CSV 3행 오류"):
            self.service.import_csv(path)
        self.assertEqual(self.repo.path("transactions").read_bytes(), before)

    def test_csv_roundtrip_and_atomic_failure(self):
        t = self.add(memo='한글, "메모"\n둘째 줄')
        path = self.root / "export.csv"
        self.assertEqual(self.service.export_csv(path, month="2024-01"), 1)
        self.assertEqual(self.service.import_csv(path), 1)
        rows = list(self.repo.transactions())
        self.assertEqual(rows[1].memo, t.memo)
        self.assertEqual(rows[1].tags, t.tags)
        self.assertNotEqual(rows[0].id, rows[1].id)
        before = self.repo.path("transactions").read_bytes()
        path.write_text("date,type,category,amount\n2024-01-01,expense,food,100\n2024-01-02,expense,food,0\n", encoding="utf-8")
        with self.assertRaises(AppError):
            self.service.import_csv(path)
        self.assertEqual(before, self.repo.path("transactions").read_bytes())

    def test_export_requires_filter_preserves_destination(self):
        path = self.root / "output.csv"
        path.write_text("original")
        for filters in ({}, {"start": "2024-01-01"}, {"month": "2024-13"}, {"month": "2024-01", "end": "2024-02-01"}):
            with self.assertRaises(AppError):
                self.service.export_csv(path, **filters)
            self.assertEqual(path.read_text(), "original")
        with self.assertRaises(AppError):
            self.service.export_csv(self.repo.path("transactions"), month="2024-01")

    def test_replace_failure_preserves_original(self):
        self.add()
        before = self.repo.path("transactions").read_bytes()
        with patch("budget_app.storage.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.add(amount=200)
        self.assertEqual(before, self.repo.path("transactions").read_bytes())
        self.assertFalse(list(self.repo.directory.glob(".transactions*")))

    def test_corrupt_storage_is_not_overwritten(self):
        path = self.repo.path("transactions")
        for content in ('{"broken"\n', '{"amount": 1}\n'):
            path.write_text(content)
            with self.assertRaises(AppError):
                self.add()
            self.assertEqual(path.read_text(), content)

    def test_lock(self):
        with self.repo.session():
            with self.assertRaises(AppError):
                with self.repo.session():
                    pass
        self.assertFalse((self.repo.directory / ".lock").exists())

    def test_cli_interactive_and_errors(self):
        result = self.cli("add", input="2024-01-01\nexpense\nfood\n1200\n점심\nmeal\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("id=TX-", result.stdout)
        for args in (("delete", "--id", "missing"), ("list", "--limit", "0"), ("summary", "--month", "bad"), ("update", "--id", "missing"), ("import", "--from", str(self.root / "missing.csv"))):
            result = self.cli(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
        result = self.cli("add", input="")
        self.assertEqual(result.returncode, 130)

    def test_cli_full_workflow(self):
        def ok(*args, input=None):
            result = self.cli(*args, input=input)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout
        ok("category", "add", input="books\n")
        ok("import", "--from", "examples/import.csv")
        ok("budget", "set", "--month", "2024-01", "--amount", "500000")
        self.assertIn("500000", ok("budget", "list", "--month", "2024-01"))
        self.assertIn("43.0%", ok("summary", "--month", "2024-01"))
        self.assertIn("45000", ok("search", "--tag", "meal", "--category", "food"))
        t = next(self.repo.transactions())
        ok("update", "--id", t.id, "--memo", "changed")
        self.assertIn("changed", ok("search", "--q", "changed"))
        path = self.root / "roundtrip.csv"
        ok("export", "--out", str(path), "--from", "2024-01-01", "--to", "2024-01-31")
        with path.open(newline="") as stream:
            self.assertEqual(len(list(csv.DictReader(stream))), 4)
        ok("delete", "--id", t.id)
        ok("category", "remove", "--name", "books")
        self.assertEqual(len(list(self.repo.transactions())), 3)

    def test_large_streaming_order(self):
        # 날짜가 뒤섞인 파일에서도 제한 조회와 디스크 정렬의 결과가 같아야 한다.
        self.repo.write("transactions", (Transaction.create(id=f"TX-{i}", type="expense", date=f"2024-01-{i % 28 + 1:02}", category="food", amount=i + 1).record() for i in range(5000)))
        top = list(self.service.newest(limit=7))
        rows = self.service.newest()
        self.assertEqual([next(rows) for _ in range(7)], top)
        rows.close()
        self.assertEqual(self.service.summary("2024-01")["expense"], 5000 * 5001 // 2)

    def test_empty_date_options_are_errors(self):
        for args in (("summary", "--month", ""), ("search", "--from", ""),
                     ("search", "--to", ""), ("budget", "list", "--month", "")):
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("[힌트]", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        path = self.root / "existing.csv"
        path.write_text("original")
        result = self.cli("export", "--out", str(path), "--month", "2024-01", "--from", "")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), "original")

    def test_null_stored_id_is_rejected_without_rewrite(self):
        record = self.add().record()
        record["id"] = None
        self.repo.write("transactions", [record])
        before = self.repo.path("transactions").read_bytes()
        result = self.cli("list")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[힌트]", result.stderr)
        with self.assertRaises(AppError):
            self.add()
        self.assertEqual(self.repo.path("transactions").read_bytes(), before)

    def test_command_syntax_errors_include_hint(self):
        for args in (("unknown",), ("update",), ("search", "--type", "wrong"),
                     ("list", "--limit", "abc"), ("budget", "set")):
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("[오류]", result.stderr)
                self.assertIn("[힌트]", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_all_help(self):
        for args in ((), ("add",), ("list",), ("search",), ("summary",), ("update",), ("delete",), ("import",), ("export",), ("category",), ("category", "add"), ("category", "list"), ("category", "remove"), ("budget",), ("budget", "set"), ("budget", "list")):
            result = self.cli(*args, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
