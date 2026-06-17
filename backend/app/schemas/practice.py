from pydantic import BaseModel


class PracticeAnswerSubmitRequest(BaseModel):
    question_id: int
    selected_answer: str


class PracticeAnswerResult(BaseModel):
    question_id: int
    selected_answer: str
    correct_answer: str
    is_correct: bool
    score_awarded: float
    score: float
    analysis: str | None = None
