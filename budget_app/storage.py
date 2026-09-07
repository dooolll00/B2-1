"""JSONL 스트리밍, 원자적 파일 교체, 프로세스 간 쓰기 보호."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator, Iterable
from .models import AppError, Transaction


@contextmanager
def atomic_output(path: Path) -> Iterator[Any]:
    """동일 파일 시스템에 완전히 기록한 뒤 교체한다. 실패 시 원본 유지."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Repository:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def session(self) -> Iterator[None]:
        lock = self.directory / ".lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise AppError("다른 작업이 진행 중입니다. 잠시 후 재시도하세요. 강제 종료 후라면 실행 중인 프로그램이 없는지 확인하고 data 폴더의 .lock을 삭제하세요.") from exc
        try:
            os.close(fd)
            self.initialize()
            yield
        finally:
            lock.unlink()

    def initialize(self) -> None:
        for name in ("transactions", "categories", "budgets"):
            path = self.path(name)
            if not path.exists():
                self.write(name, [])
        if self.path("categories").stat().st_size == 0:
            self.write("categories", ({"name": n} for n in ("food", "transport", "rent", "etc", "salary")))

    def path(self, name: str) -> Path:
        return self.directory / (name + ".jsonl")

    def records(self, name: str) -> Iterator[dict[str, Any]]:
        with self.path(name).open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("object required")
                    yield value
                except (ValueError, TypeError) as exc:
                    raise AppError(f"{name}.jsonl {number}행 손상. 원본을 보존하고 백업에서 복원하세요.") from exc

    def write(self, name: str, records: Iterable[dict[str, Any]]) -> None:
        with atomic_output(self.path(name)) as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def transactions(self) -> Iterator[Transaction]:
        for number, record in enumerate(self.records("transactions"), 1):
            try:
                if "id" not in record:
                    raise ValueError("missing id")
                yield Transaction.create(**record)
            except (TypeError, ValueError, AppError) as exc:
                raise AppError(f"transactions.jsonl {number}행 거래 오류. 백업이나 원본을 확인하세요: {exc}") from exc
