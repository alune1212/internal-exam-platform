from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringResult:
    is_correct: bool
    score_awarded: float


def normalize_answer_set(answer: str | None) -> set[str]:
    if not answer:
        return set()
    return {item.strip().upper() for item in answer.split(",") if item.strip()}


def normalize_single_answer(answer: str | None) -> str:
    return (answer or "").strip().upper()


def score_answer(
    question_type: str,
    correct_answer: str,
    selected_answer: str | None,
    score: float,
) -> ScoringResult:
    normalized_type = question_type.strip().lower()
    if normalized_type == "multiple":
        is_correct = normalize_answer_set(correct_answer) == normalize_answer_set(selected_answer)
    else:
        is_correct = normalize_single_answer(correct_answer) == normalize_single_answer(selected_answer)
    return ScoringResult(is_correct=is_correct, score_awarded=score if is_correct else 0)
