from pydantic import BaseModel


class PracticeAnswerSubmitRequest(BaseModel):
    question_id: int
    selected_answer: str


class PracticeAnswerResult(BaseModel):
    question_id: int
    selected_answer: str
    score: float
