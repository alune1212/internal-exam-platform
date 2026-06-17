from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class QuestionOptionBase(BaseModel):
    label: str
    content: str
    is_correct: bool = False
    sort_order: int = 0


class QuestionOptionRead(QuestionOptionBase, ORMModel):
    id: int


class PracticeQuestionOptionRead(ORMModel):
    id: int
    label: str
    content: str
    sort_order: int = 0


class QuestionBase(BaseModel):
    question_type: str
    stem: str
    analysis: str | None = None
    category_1: str | None = None
    category_2: str | None = None
    difficulty: str | None = None
    score: float = 1
    status: str = "active"
    source: str | None = None
    source_no: str | None = None
    remark: str | None = None


class QuestionCreate(QuestionBase):
    options: list[QuestionOptionBase] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    question_type: str | None = None
    stem: str | None = None
    analysis: str | None = None
    category_1: str | None = None
    category_2: str | None = None
    difficulty: str | None = None
    score: float | None = None
    status: str | None = None
    source: str | None = None
    source_no: str | None = None
    remark: str | None = None
    options: list[QuestionOptionBase] | None = None


class QuestionRead(QuestionBase, ORMModel):
    id: int
    options: list[QuestionOptionRead] = Field(default_factory=list)


class PracticeQuestionRead(ORMModel):
    id: int
    question_type: str
    stem: str
    category_1: str | None = None
    category_2: str | None = None
    difficulty: str | None = None
    score: float = 1
    status: str = "active"
    source: str | None = None
    source_no: str | None = None
    remark: str | None = None
    options: list[PracticeQuestionOptionRead] = Field(default_factory=list)


class ImportFailure(BaseModel):
    row_number: int
    reason: str


class QuestionImportResult(BaseModel):
    batch_id: int
    success_count: int
    failed_count: int
    failures: list[ImportFailure] = Field(default_factory=list)
