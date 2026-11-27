from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


# ---------- Todo models ----------

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False
    priority: Priority = Priority.medium


class TodoCreate(TodoBase):
    """Body for POST /todos."""


class TodoUpdate(BaseModel):
    """Body for PATCH /todos/{id}. Only the fields you send are changed."""
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None
    priority: Priority | None = None


class Todo(TodoBase):
    """Internal todo record, including the owner."""
    id: int
    owner_id: int


class TodoResponse(TodoBase):
    """What the API returns. owner_id is hidden."""
    id: int


# ---------- User and auth models ----------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt_limit(cls, value: str) -> str:
        # bcrypt only accepts 72 bytes, and non-English characters use more than one byte
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes")
        return value


class UserPublic(BaseModel):
    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
