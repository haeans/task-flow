from typing import Literal

from pydantic import BaseModel, field_validator

Status = Literal["TODO", "IN_PROGRESS", "DONE"]

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
