"""Strict v1 request contracts (Pydantic 2)."""
from pydantic import BaseModel, ConfigDict, StringConstraints, Field, model_validator
from typing import Annotated, Literal

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ProjectCreate(StrictModel):
    name: Name
    client: Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)] = ""

Code = Annotated[str, StringConstraints(pattern=r"^[0-9]{2}$")]

class Category(StrictModel):
    code: Code
    label: Name

class CodebookCreate(StrictModel):
    name: Name
    categories: list[Category] = Field(min_length=1, max_length=100)
    max_labels: int = Field(default=1, ge=1, le=6, strict=True)

    @model_validator(mode="after")
    def unique_codes(self):
        if len({item.code for item in self.categories}) != len(self.categories):
            raise ValueError("Códigos duplicados")
        return self

class QuestionCreate(StrictModel):
    column_name: Name
    question_text: Name
    codebook_id: str

class JobCreate(StrictModel):
    survey_id: str
    name: Name
    questions: list[QuestionCreate] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_columns(self):
        if len({item.column_name for item in self.questions}) != len(self.questions):
            raise ValueError("Columnas duplicadas")
        return self

class ResumeRequest(StrictModel):
    retry_uncertain: bool = Field(default=False, strict=True)

class ReviewUpdate(StrictModel):
    codes: list[Code] = Field(min_length=1, max_length=6)
    review_status: Annotated[str, StringConstraints(pattern=r"^APPROVED$")] = "APPROVED"

class BatchReview(StrictModel):
    record_ids: list[str] = Field(min_length=1, max_length=200)
    code: Code
    label: Name

class LoginRequest(StrictModel):
    email: Annotated[str, StringConstraints(max_length=254)]
    password: Annotated[str, StringConstraints(max_length=128)] = Field(repr=False)

Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]

class PasswordChange(StrictModel):
    current_password: Annotated[str, StringConstraints(max_length=128)] = Field(repr=False)
    password: Password = Field(repr=False)

class UserCreate(StrictModel):
    email: Annotated[str, StringConstraints(max_length=254)]
    name: Name
    password: Password = Field(repr=False)
    role: Literal['ADMIN', 'STANDARD']
    must_change_password: bool = Field(strict=True)


class User(StrictModel):
    id: str
    email: str
    name: str
    role: Literal['ADMIN', 'STANDARD']
    active: bool
    must_change_password: bool
    created_at: str


class SessionResponse(StrictModel):
    user: User
    csrf_token: str


class UsersResponse(StrictModel):
    users: list[User]


class AuditEvent(StrictModel):
    id: str
    actor_id: str | None
    actor_name: str | None
    actor_email: str | None
    action: str
    resource_type: str
    resource_id: str | None
    project_id: str | None
    job_id: str | None
    created_at: str


class AuditResponse(StrictModel):
    events: list[AuditEvent]
    total: int


class AdminOverview(StrictModel):
    projects: int
    jobs: int
    users: int
    active_jobs: int
    completed_jobs: int


class OkResponse(StrictModel):
    ok: Literal[True]
