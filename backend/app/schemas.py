import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Status = Literal["TODO", "IN_PROGRESS", "DONE"]
Priority = Literal["LOW", "NORMAL", "HIGH"]

# 아이디는 4~20자 영문·숫자, 비밀번호는 8~100자 (Q-014)
USERNAME_PATTERN = r"^[A-Za-z0-9]{4,20}$"
PASSWORD_MIN = 8
PASSWORD_MAX = 100


class SignupRequest(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    """사용자에 대해 응답으로 돌려주는 값은 구분 값과 아이디뿐이다. 해시값은 담지 않는다."""

    id: int
    username: str

TITLE_MAX = 100
DESCRIPTION_MAX = 1000


DUE_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    # 우선순위는 지울 수 없다. null이나 허용 밖의 값은 422이다 (R-011).
    priority: Priority = "NORMAL"
    # 마감일은 YYYY-MM-DD 날짜만 받고, null이면 없음이다 (R-012).
    due_date: str | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # fromisoformat은 20261027 같은 다른 형식도 받으므로 형식을 먼저 확인한다.
        if not DUE_DATE_PATTERN.match(v):
            raise ValueError("마감일은 YYYY-MM-DD 형식이어야 한다")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("존재하지 않는 날짜이다") from None
        return v

    @field_validator("title")
    @classmethod
    def title_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("제목은 비워 둘 수 없다")
        if len(v) > TITLE_MAX:
            raise ValueError(f"제목은 {TITLE_MAX}자 이하여야 한다")
        return v

    @field_validator("description")
    @classmethod
    def description_length(cls, v: str) -> str:
        if len(v) > DESCRIPTION_MAX:
            raise ValueError(f"설명은 {DESCRIPTION_MAX}자 이하여야 한다")
        return v


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    due_date: str | None
    # 저장하지 않는다. 목록을 줄 때 서버가 계산한다 (R-013).
    overdue: bool
    created_at: str
    updated_at: str


class StatusUpdate(BaseModel):
    status: Status


class TaskUpdate(TaskCreate):
    """수정은 상태를 받지 않는다. priority·due_date는 보내지 않으면 그대로이다 (model_fields_set)."""
