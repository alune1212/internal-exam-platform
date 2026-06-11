from sqlalchemy.orm import Session

from app.schemas.report import AbsentCandidateRow, QuestionAccuracyRow, ScoreReportRow, WrongQuestionRow


def get_score_report(db: Session) -> list[ScoreReportRow]:
    return []


def get_question_accuracy(db: Session) -> list[QuestionAccuracyRow]:
    return []


def get_wrong_questions(db: Session) -> list[WrongQuestionRow]:
    return []


def get_absent_candidates(db: Session) -> list[AbsentCandidateRow]:
    return []
