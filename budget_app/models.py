"""거래 모델과 공통 입력 검증."""
from dataclasses import asdict, dataclass
from datetime import date
import re
from typing import Any
from uuid import uuid4


class AppError(Exception):
    """사용자에게 원인과 해결 방법을 전달하는 오류."""


# 날짜는 모양(YYYY-MM-DD)과 실제 달력에 존재하는 날짜인지 둘 다 검사합니다.
def valid_date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise AppError("날짜 형식 오류. YYYY-MM-DD로 입력하세요 (예: 2024-01-15).")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise AppError("존재하지 않는 날짜입니다. 달력의 날짜를 확인하세요.") from exc
    return value


# 월 뒤에 01일을 붙여 기존 날짜 검사 함수를 재사용합니다.
def valid_month(value: str) -> str:
    if not isinstance(value, str):
        raise AppError("월 형식 오류. YYYY-MM로 입력하세요.")
    valid_date(value + "-01")
    return value


# input()과 CSV에서 받은 문자열을 검사한 뒤 양수 정수로 바꿉니다.
def positive(value: Any) -> int:
    if not re.fullmatch(r"[0-9]+", str(value)) or int(value) <= 0:
        raise AppError("금액/개수는 양수 정수여야 합니다. 1 이상의 정수를 입력하세요.")
    return int(value)


# dataclass는 거래 항목을 묶고 생성자 등을 만들어 줍니다. frozen=True는 필드 재할당을 막습니다.
# str/int 등의 타입 힌트는 값의 종류를 알려 줍니다. 실제 입력 검사는 아래 create에서 합니다.
@dataclass(frozen=True)
class Transaction:
    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: tuple[str, ...] = ()

    # 클래스 메서드는 거래를 만들기 전에 값을 검사하는 공통 입구입니다.
    # 카테고리의 등록 여부는 파일을 아는 service에서 별도로 확인합니다.
    @classmethod
    def create(cls, *, type: str, date: str, amount: Any, category: str,
               memo: str = "", tags: Any = (), id: str | None = None) -> "Transaction":
        if type not in ("income", "expense"):
            raise AppError("type 오류. income 또는 expense를 입력하세요.")
        if not isinstance(category, str) or not category.strip():
            raise AppError("카테고리가 비어 있습니다. category list로 확인하세요.")
        if not isinstance(memo, str):
            raise AppError("메모는 문자열이어야 합니다. 입력 파일을 확인하세요.")
        # 예: "meal, lunch"를 태그 목록으로 나누고, 마지막에 공백·빈 항목·중복을 정리합니다.
        if isinstance(tags, str):
            tags = tags.split(",")
        if not isinstance(tags, (list, tuple)) or any(not isinstance(t, str) for t in tags):
            raise AppError("태그 형식 오류. 쉼표로 구분한 문자열을 사용하세요.")
        if id is not None and (not isinstance(id, str) or not id.strip()):
            raise AppError("거래 id 오류. 저장 파일을 확인하세요.")
        # 새 거래는 UUID로 id를 만들고, 수정하거나 파일에서 읽을 때는 기존 id를 유지합니다.
        return cls(id or "TX-" + uuid4().hex, type, valid_date(date), positive(amount),
                   category.strip(), memo, tuple(dict.fromkeys(t.strip() for t in tags if t.strip())))

    # 거래 객체를 JSON/CSV에 저장하기 쉬운 딕셔너리로 바꿉니다.
    def record(self) -> dict[str, Any]:
        return asdict(self)
