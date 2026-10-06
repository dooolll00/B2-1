"""JSONL 스트리밍, 원자적 파일 교체, 프로세스 간 쓰기 보호."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator, Iterable
from .models import AppError, Transaction


# contextmanager는 with 문에서 쓰게 합니다. yield 앞은 준비, 뒤는 정상 마무리입니다.
@contextmanager
def atomic_output(path: Path) -> Iterator[Any]:
    """동일 파일 시스템에 완전히 기록한 뒤 교체한다. 실패 시 원본 유지."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # 원본과 같은 폴더에 임시 파일을 만들고, 완성될 때까지 원본을 유지합니다.
    fd, name = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            # with 블록에 임시 파일을 전달합니다. 쓰기 오류가 나면 교체 단계로 가지 않습니다.
            yield stream
            # Python 버퍼를 비우고 운영체제에 디스크 기록을 요청합니다.
            stream.flush()
            os.fsync(stream.fileno())
        # 모든 기록이 성공했을 때만 원본을 완성된 임시 파일로 교체합니다.
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


# 저장소는 파일 읽기·쓰기를 맡습니다. 검색·예산 계산 규칙은 service가 담당합니다.
class Repository:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def session(self) -> Iterator[None]:
        # 작업 중에는 잠금 파일을 두어 다른 실행이 동시에 데이터를 바꾸지 못하게 합니다.
        lock = self.directory / ".lock"
        try:
            # O_EXCL은 잠금 파일이 이미 있으면 생성을 실패시킵니다.
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise AppError("다른 작업이 진행 중입니다. 잠시 후 재시도하세요. 강제 종료 후라면 실행 중인 프로그램이 없는지 확인하고 data 폴더의 .lock을 삭제하세요.") from exc
        try:
            os.close(fd)
            self.initialize()
            yield
        finally:
            lock.unlink()

    # 처음 실행할 때 세 저장 파일을 만들고, 빈 카테고리 파일에는 기본 분류를 넣습니다.
    def initialize(self) -> None:
        for name in ("transactions", "categories", "budgets"):
            path = self.path(name)
            if not path.exists():
                self.write(name, [])
        if self.path("categories").stat().st_size == 0:
            self.write("categories", ({"name": n} for n in ("food", "transport", "rent", "etc", "salary")))

    def path(self, name: str) -> Path:
        return self.directory / (name + ".jsonl")

    # JSONL은 한 줄에 JSON 객체 하나입니다. 전체를 리스트로 읽지 않고 줄마다 읽습니다.
    def records(self, name: str) -> Iterator[dict[str, Any]]:
        with self.path(name).open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("object required")
                    # 한 건을 전달하고 멈춥니다. 다음 건을 요청받으면 이어서 읽습니다.
                    yield value
                except (ValueError, TypeError) as exc:
                    raise AppError(f"{name}.jsonl {number}행 손상. 원본을 보존하고 백업에서 복원하세요.") from exc

    # 제너레이터도 받아 한 건씩 임시 파일에 쓰므로 거래 전체를 메모리에 모으지 않습니다.
    def write(self, name: str, records: Iterable[dict[str, Any]]) -> None:
        with atomic_output(self.path(name)) as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 저장된 딕셔너리를 검증된 거래 객체로 바꿉니다. 손상되면 행 번호와 함께 알립니다.
    def transactions(self) -> Iterator[Transaction]:
        for number, record in enumerate(self.records("transactions"), 1):
            try:
                if not isinstance(record.get("id"), str) or not record["id"].strip():
                    raise ValueError("id는 비어 있지 않은 문자열이어야 합니다")
                yield Transaction.create(**record)
            except (TypeError, ValueError, AppError) as exc:
                raise AppError(f"transactions.jsonl {number}행 거래 오류. 백업이나 원본을 확인하세요: {exc}") from exc
