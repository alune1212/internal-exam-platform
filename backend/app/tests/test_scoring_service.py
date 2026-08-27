from app.services.scoring_service import score_answer


def test_multiple_choice_scores_by_set_not_string_order() -> None:
    result = score_answer(
        correct_answer="A,C",
        selected_answer="C,A",
        score=2.0,
    )

    assert result.is_correct is True
    assert result.score_awarded == 2.0


def test_multiple_choice_requires_exact_set_match() -> None:
    result = score_answer(
        correct_answer="A,C",
        selected_answer="A,B,C",
        score=2.0,
    )

    assert result.is_correct is False
    assert result.score_awarded == 0


def test_single_choice_requires_exact_answer() -> None:
    result = score_answer(
        correct_answer="A",
        selected_answer="B",
        score=1.0,
    )

    assert result.is_correct is False
    assert result.score_awarded == 0


def test_judge_answer_normalizes_case() -> None:
    result = score_answer(
        correct_answer="true",
        selected_answer="TRUE",
        score=1.0,
    )

    assert result.is_correct is True
    assert result.score_awarded == 1.0


def test_multiple_choice_empty_correct_answer() -> None:
    result = score_answer("", None, 5.0)
    assert result.is_correct is True
    assert result.score_awarded == 5.0


def test_score_zero_value_awarded_zero() -> None:
    result = score_answer("A", "A", 0)
    assert result.is_correct is True
    assert result.score_awarded == 0
