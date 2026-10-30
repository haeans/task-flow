"""한 문장으로 시키기의 규칙 (#33).

입력 문장의 길이 규칙과, 모델이 돌려준 actions를 거르는 규칙을 한 곳에 둔다.
문장이 규칙에 맞지 않으면 ValueError(이유)를 올리고, 모델의 글은 항목 단위로 버린다.
이 모듈은 DB를 읽거나 쓰지 않는다.
"""

from app.schemas import CommandAction, Priority, validate_due_date
from app.suggest import FAILED, SuggestError

TEXT_MAX = 200
ASK_MAX = 100
DEFAULT_ASK = "무슨 일을 할지 잘 모르겠어요. 다시 말씀해 주세요."

_PRIORITIES = ("LOW", "NORMAL", "HIGH")
_DEFAULT_PRIORITY: Priority = "NORMAL"


def validate_text(text: str) -> str:
    """앞뒤 공백을 지우고 1~200자인지 본다. 아니면 이유를 담은 ValueError이다."""
    text = text.strip()
    if not text:
        raise ValueError("문장을 입력해 주세요")
    if len(text) > TEXT_MAX:
        raise ValueError(f"문장은 {TEXT_MAX}자 이하여야 합니다")
    return text


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _due_date(v) -> str | None:
    """YYYY-MM-DD 날짜 문자열이면 그대로, 아니면 None. 과거 날짜도 허용한다 (형식만 검사)."""
    if not isinstance(v, str):
        return None
    try:
        return validate_due_date(v)
    except ValueError:
        return None


def _add(item: dict) -> CommandAction | None:
    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    due_date = None
    if item.get("due_date") is not None:
        due_date = _due_date(item["due_date"])
        if due_date is None:
            return None  # 규칙 밖 날짜는 그 action을 버린다. 날짜를 없애고 등록하지 않는다.
    priority = item.get("priority")
    if priority not in _PRIORITIES:
        priority = _DEFAULT_PRIORITY  # 규칙 밖 우선순위는 값만 버린다.
    return CommandAction(kind="add", title=title.strip(), priority=priority, due_date=due_date)


def clean_actions(raw_actions: list, titles: dict[int, str]) -> list[CommandAction]:
    """모델의 actions를 거른다. titles는 보낸 Task의 {id: 제목}이다.

    모양이 틀린 항목(객체 아님)은 502, 값이 규칙 밖인 항목은 그 항목만 버린다.
    보낸 적 없는 id, 알 수 없는 kind, 규칙 밖 날짜, 같은 (kind, id) 중복을 버린다.
    """
    result: list[CommandAction] = []
    seen: set[tuple[str, int]] = set()
    for item in raw_actions:
        if not isinstance(item, dict):
            raise SuggestError(502, FAILED)
        kind = item.get("kind")
        if kind == "add":
            action = _add(item)
        elif kind in ("due", "done"):
            task_id = item.get("id")
            if not _is_int(task_id) or task_id not in titles or (kind, task_id) in seen:
                continue
            due_date = None
            if kind == "due":
                due_date = _due_date(item.get("due_date"))
                if due_date is None:
                    continue
            seen.add((kind, task_id))
            action = CommandAction(kind=kind, id=task_id, title=titles[task_id], due_date=due_date)
        else:
            continue
        if action is not None:
            result.append(action)
    return result


def clean_ask(raw) -> str | None:
    """ask는 없거나 문자열이다. 비어 있으면 없는 것이고, 100자를 넘으면 502이다."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise SuggestError(502, FAILED)
    raw = raw.strip()
    if len(raw) > ASK_MAX:
        raise SuggestError(502, FAILED)
    return raw or None
