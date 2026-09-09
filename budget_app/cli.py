"""명령 파싱과 콘솔 출력. update는 옵션 입력으로 고정."""
import argparse
import csv
from functools import wraps
from pathlib import Path
import sys
import sqlite3
from typing import Callable, Iterable, NoReturn
from .models import AppError, Transaction, positive
from .service import BudgetService
from .storage import Repository


def handle_errors(function: Callable[[], int]) -> Callable[[], int]:
    """공통 오류를 스택트레이스 없는 메시지와 실패 코드로 변환한다."""
    @wraps(function)
    def wrapped() -> int:
        try:
            return function()
        except (AppError, OSError, UnicodeError, csv.Error, ValueError, sqlite3.Error) as exc:
            print(f"[오류] {exc}\n[힌트] 입력값, 파일 형식과 접근 권한을 확인하고 --help를 참고하세요.", file=sys.stderr)
            return 1
        except (EOFError, KeyboardInterrupt):
            print("[취소] 입력이 중단되었습니다. 명령을 다시 실행하세요.", file=sys.stderr)
            return 130
    return wrapped


class ArgumentParser(argparse.ArgumentParser):
    """하위 명령까지 문법 오류에 원인과 해결 힌트를 제공한다."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"[오류] {message}\n[힌트] {self.prog} --help로 필수 옵션과 허용 값을 확인하세요.\n")


def parser() -> argparse.ArgumentParser:
    root = ArgumentParser(description="파일 기반 콘솔 가계부 (Python 표준 라이브러리)")
    root.add_argument("--data-dir", default="./data", help="JSONL 저장 폴더 (기본: ./data)")
    commands = root.add_subparsers(dest="command", required=True)
    def command(name: str, help: str) -> argparse.ArgumentParser:
        p = commands.add_parser(name, help=help, description=help)
        p.add_argument("--data-dir", default=argparse.SUPPRESS, help="JSONL 저장 폴더")
        return p
    command("add", "거래 대화형 추가")
    p = command("list", "최신순 거래 목록")
    p.add_argument("--limit", type=int, default=20)
    p = command("search", "조건별 거래 검색 (조건은 AND)")
    for flag in ("from", "to", "category", "q", "tag"):
        p.add_argument("--" + flag)
    p.add_argument("--type", choices=("income", "expense"))
    p.add_argument("--limit", type=int)
    p = command("summary", "월별 수입/지출/예산 요약")
    p.add_argument("--month", required=True)
    p.add_argument("--top", type=int, default=3)
    p = command("update", "거래 옵션 기반 수정")
    p.add_argument("--id", required=True)
    for flag in ("date", "category", "amount", "memo", "tags"):
        p.add_argument("--" + flag)
    p.add_argument("--type", choices=("income", "expense"))
    p = command("delete", "거래 삭제")
    p.add_argument("--id", required=True)
    p = command("import", "CSV 일괄 가져오기 (실패 시 전체 취소)")
    p.add_argument("--from", required=True, dest="source")
    p = command("export", "CSV 내보내기")
    p.add_argument("--out", required=True)
    for flag in ("month", "from", "to"):
        p.add_argument("--" + flag)
    p = command("category", "카테고리 관리")
    subs = p.add_subparsers(dest="action", required=True)
    for action in ("add", "list", "remove"):
        sub = subs.add_parser(action)
        if action != "list":
            sub.add_argument("--name", help="생략하면 대화형 입력")
    p = command("budget", "월별 예산 설정/조회")
    subs = p.add_subparsers(dest="action", required=True)
    sub = subs.add_parser("set")
    sub.add_argument("--month", required=True)
    sub.add_argument("--amount", required=True)
    sub = subs.add_parser("list")
    sub.add_argument("--month", help="생략하면 전체 조회")
    return root


def percentage(expense: int, budget: int) -> str:
    """정수 연산으로 사용률을 소수 한 자리까지 표시한다(동률은 짝수 반올림)."""
    tenths, remainder = divmod(expense * 1000, budget)
    if remainder * 2 > budget or (remainder * 2 == budget and tenths % 2):
        tenths += 1
    whole, decimal = divmod(tenths, 10)
    return f"{whole}.{decimal}"


def show(rows: Iterable[Transaction]) -> None:
    found = False
    for t in rows:
        found = True
        # JSON escaping prevents embedded line breaks / control characters from breaking rows.
        import json
        memo = json.dumps(t.memo, ensure_ascii=False)
        print(f"{t.id} | {t.date} | {t.type:7} | {t.category} | {t.amount} | {memo} | {','.join(t.tags)}")
    if not found:
        print("데이터 없음")


@handle_errors
def main() -> int:
    args = parser().parse_args()
    repo = Repository(Path(args.data_dir))
    with repo.session():
        service = BudgetService(repo)
        command = args.command
        if command == "add":
            print("등록된 카테고리: " + ", ".join(service.categories()))
            values = {key: input(prompt).strip() for key, prompt in (
                ("date", "날짜(YYYY-MM-DD): "), ("type", "타입(income/expense): "),
                ("category", "카테고리: "), ("amount", "금액(양수 정수): "),
                ("memo", "메모(선택): "), ("tags", "태그(쉼표로 구분, 선택): "))}
            print(f"[저장 완료] id={service.add(**values).id}")
        elif command == "list":
            show(service.newest(limit=args.limit))
        elif command == "search":
            show(service.newest(limit=args.limit, start=getattr(args, "from"), end=args.to,
                                category=args.category, type=args.type, q=args.q, tag=args.tag))
        elif command == "update":
            values = {key: getattr(args, key) for key in ("date", "type", "category", "amount", "memo", "tags") if getattr(args, key) is not None}
            if not values:
                raise AppError("수정할 필드가 없습니다. --amount 등 수정 옵션을 지정하세요.")
            service.change(args.id, values)
            print(f"[수정 완료] id={args.id}")
        elif command == "delete":
            service.change(args.id, None)
            print(f"[삭제 완료] id={args.id}")
        elif command == "category":
            if args.action == "list":
                print("\n".join("- " + n for n in service.categories()) or "카테고리 없음")
            else:
                name = args.name if args.name is not None else input("카테고리명: ")
                service.category(args.action, name)
                print(f"[완료] category {args.action}: {name}")
        elif command == "budget":
            if args.action == "set":
                service.set_budget(args.month, args.amount)
                print(f"[저장 완료] {args.month} 예산 {args.amount}원")
            else:
                from .models import valid_month
                if args.month is not None:
                    valid_month(args.month)
                rows = [(m, a) for m, a in sorted(service.budgets().items()) if not args.month or m == args.month]
                print("\n".join(f"{m}: {a}원" for m, a in rows) or "설정된 예산 없음")
        elif command == "summary":
            top = positive(args.top)
            s = service.summary(args.month)
            if not s["count"]:
                print("데이터 없음")
            print(f"총 수입: {s['income']}원\n총 지출: {s['expense']}원\n잔액: {s['income'] - s['expense']}원")
            if s["budget"] is not None:
                print(f"예산: {s['budget']}원 (사용률 {percentage(s['expense'], s['budget'])}%)")
                if s["expense"] > s["budget"]:
                    print("[경고] 예산 초과!")
            print(f"지출 TOP {top}")
            for i, (name, amount) in enumerate(sorted(s["categories"].items(), key=lambda item: (-item[1], item[0]))[:top], 1):
                print(f"{i}) {name} {amount}원")
        elif command == "import":
            print(f"[완료] imported={service.import_csv(Path(args.source))}, skipped=0")
        elif command == "export":
            count = service.export_csv(Path(args.out), month=args.month, start=getattr(args, "from"), end=args.to)
            print(f"[완료] {args.out} ({count} records)")
    return 0
