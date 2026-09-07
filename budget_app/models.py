"""거래 모델과 공통 입력 검증."""
from dataclasses import asdict, dataclass
from datetime import date
import re
from typing import Any
from uuid import uuid4


class AppError(Exception):
    """사용자에게 원인과 해결 방법을 전달하는 오류."""


def valid_date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise AppError("날짜 형식 오류. YYYY-MM-DD로 입력하세요 (예: 2024-01-15).")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise AppError("존재하지 않는 날짜입니다. 달력의 날짜를 확인하세요.") from exc
    return value


def valid_month(value: str) -> str:
    if not isinstance(value, str):
        raise AppError("월 형식 오류. YYYY-MM로 입력하세요.")
    valid_date(value + "-01")
    return value


def positive(value: Any) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)) or int(value) <= 0:
        raise AppError("금액/개수는 양수 정수여야 합니다. 1 이상의 정수를 입력하세요.")
    return int(value)


@dataclass(frozen=True)
class Transaction:
    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: tuple[str, ...] = ()

    @classmethod
    def create(cls, *, type: str, date: str, amount: Any, category: str,
               memo: str = "", tags: Any = (), id: str | None = None) -> "Transaction":
        if type not in ("income", "expense"):
            raise AppError("type 오류. income 또는 expense를 입력하세요.")
        if not isinstance(category, str) or not category.strip():
            raise AppError("카테고리가 비어 있습니다. category list로 확인하세요.")
        if not isinstance(memo, str):
            raise AppError("메모는 문자열이어야 합니다. 입력 파일을 확인하세요.")
        if isinstance(tags, str):
            tags = tags.split(",")
        if not isinstance(tags, (list, tuple)) or any(not isinstance(t, str) for t in tags):
            raise AppError("태그 형식 오류. 쉼표로 구분한 문자열을 사용하세요.")
        if id is not None and (not isinstance(id, str) or not id.strip()):
            raise AppError("거래 id 오류. 저장 파일을 확인하세요.")
        return cls(id or "TX-" + uuid4().hex, type, valid_date(date), positive(amount),
                   category.strip(), memo, tuple(dict.fromkeys(t.strip() for t in tags if t.strip())))

    def record(self) -> dict[str, Any]:
        return asdict(self)
