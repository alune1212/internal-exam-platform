from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringResult:
    is_correct: bool
    score_awarded: float


def normalize_answer_set(answer: str | None) -> set[str]:
    if not answer:
        return set()
    return {item.strip().upper() for item in answer.split(",") if item.strip()}


def score_answer(
    question_type: str,
    correct_answer: str,
    selected_answer: str | None,
    score: float,
) -> ScoringResult:
    # CLAUDE.md mandates set-based comparison; apply it uniformly so single
    # and judge answers follow the same encoding contract as multiple choice.
    del question_type  # the shape contract no longer varies by question type.
    is_correct = normalize_answer_set(correct_answer) == normalize_answer_set(
        selected_answer
    )
    return ScoringResult(
        is_correct=is_correct, score_awarded=score if is_correct else 0
    )
