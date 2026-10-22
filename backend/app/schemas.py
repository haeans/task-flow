from typing import Literal

from pydantic import BaseModel, Field, field_validator

Status = Literal["TODO", "IN_PROGRESS", "DONE"]

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


class TaskCreate(BaseModel):
    title: str
    description: str = ""

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
    created_at: str
    updated_at: str


class StatusUpdate(BaseModel):
    status: Status


class TaskUpdate(TaskCreate):
    """수정은 제목과 설명만 받는다. 상태는 받지 않는다."""
