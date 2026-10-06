# python -m budget_app을 실행하면 여기서 CLI의 main으로 들어갑니다.
from .cli import main

# 반환값을 프로그램 종료 코드로 전달합니다(성공 0, 오류는 0 이외).
raise SystemExit(main())
