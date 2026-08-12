import pytest
from sqlalchemy.orm import Session

from app.models import (
    ExamAttempt,
    ExamAttemptAnswer,
    ExamCandidateScope,
    ExamRetakeGrant,
)
from app.services import exam_service, report_service
from app.services.audit_service import record_admin_event
from app.services.exam_errors import (
    AttemptAlreadySubmittedError,
    AttemptResultNotReadyError,
    BulkRetakeConflictError,
    ExamConfigError,
    ResultDetailsAlreadyReleasedError,
    ResultDetailsNotReadyError,
)
from app.tests.conftest import (
    create_candidate,
    create_exam,
    create_question_with_options,
    submit_answers,
)


def _start_exam(db: Session, *, title: str = "结果发布考试"):
    exam = create_exam(db, title=title)
    candidate = create_candidate(db, name="结果考生")
    db.add(
        ExamCandidateScope(
            exam_id=exam.id,
            candidate_id=candidate.id,
            roster_email=candidate.email,
            roster_name=candidate.name or "待注册",
        )
    )
    db.commit()
    create_question_with_options(db, analysis="快照解析")
    start = exam_service.start_exam(db, exam.id, candidate.id)
    return exam, candidate, start


def test_new_result_is_score_only_until_irreversible_release(db: Session) -> None:
    exam, _candidate, start = _start_exam(db)
    submit_answers(db, start.attempt_id, start.questions, ["A"])
    hidden = exam_service.get_attempt_result(db, start.attempt_id)

    assert hidden.score > 0
    assert hidden.show_answer_after_submit is False
    assert hidden.questions == []

    released = exam_service.release_result_details(
        db,
        exam.id,
        operator_subject="primary-operator",
        confirmation_title=exam.title,
    )
    db.commit()
    visible = exam_service.get_attempt_result(db, start.attempt_id)

    assert released.released_by == "primary-operator"
    assert visible.show_answer_after_submit is True
    assert visible.questions[0].correct_answer_snapshot == "A"
    assert visible.questions[0].analysis_snapshot == "快照解析"
    with pytest.raises(ResultDetailsAlreadyReleasedError):
        exam_service.release_result_details(
            db,
            exam.id,
            operator_subject="primary-operator",
            confirmation_title=exam.title,
        )


def test_result_release_requires_exact_title_and_all_attempts_terminal(
    db: Session,
) -> None:
    exam, _candidate, start = _start_exam(db)

    with pytest.raises(ExamConfigError, match="确认名称"):
        exam_service.release_result_details(
            db,
            exam.id,
            operator_subject="primary-operator",
            confirmation_title="错误名称",
        )
    with pytest.raises(ResultDetailsNotReadyError, match="进行中"):
        exam_service.release_result_details(
            db,
            exam.id,
            operator_subject="primary-operator",
            confirmation_title=exam.title,
        )

    exam_service.submit_attempt(db, start.attempt_id, "manual")
    result = exam_service.release_result_details(
        db,
        exam.id,
        operator_subject="primary-operator",
        confirmation_title=exam.title,
    )
    assert result.exam_id == exam.id


def test_void_preserves_evidence_excludes_reports_and_requires_retake_grant(
    db: Session,
) -> None:
    exam, candidate, start = _start_exam(db)
    submit_answers(db, start.attempt_id, start.questions, ["A"])
    before = db.get(ExamAttempt, start.attempt_id)
    assert before is not None
    snapshot_ids = [question.id for question in before.questions]
    answer_id = db.query(ExamAttemptAnswer.id).scalar()

    incident = exam_service.void_attempt(
        db,
        start.attempt_id,
        operator_subject="backup-operator",
        reason="考试期间发生持续网络故障",
    )
    db.commit()

    after = db.get(ExamAttempt, start.attempt_id)
    assert after is not None
    assert incident.prior_status == "submitted"
    assert after.status == "voided"
    assert after.voided_by == "backup-operator"
    assert after.attempt_session_hash is None
    assert [question.id for question in after.questions] == snapshot_ids
    assert db.query(ExamAttemptAnswer.id).scalar() == answer_id
    assert report_service.get_score_report(db, exam_id=exam.id) == []
    assert report_service.get_question_accuracy(db, exam_id=exam.id) == []
    assert report_service.get_wrong_questions(db, exam_id=exam.id) == []
    assert [
        row.candidate_id for row in report_service.get_absent_candidates(db, exam.id)
    ] == [candidate.id]
    assert (
        exam_service.list_exam_incidents(db, exam.id)[0].attempt_id == start.attempt_id
    )
    with pytest.raises(AttemptResultNotReadyError):
        exam_service.get_attempt_result(db, start.attempt_id)
    with pytest.raises(AttemptAlreadySubmittedError):
        exam_service.start_exam(db, exam.id, candidate.id)

    exam_service.create_retake_grant(db, exam.id, candidate.id)
    retake = exam_service.start_exam(db, exam.id, candidate.id)
    assert retake.attempt_id != start.attempt_id


def test_bulk_retake_preview_apply_is_row_level_and_idempotent(db: Session) -> None:
    exam, first, first_start = _start_exam(db, title="批量补考")
    submit_answers(db, first_start.attempt_id, first_start.questions, ["A"])
    second = create_candidate(db, name="进行中考生")
    third = create_candidate(db, name="未开始考生")
    outsider = create_candidate(db, name="非名单考生")
    db.add_all(
        [
            ExamCandidateScope(
                exam_id=exam.id,
                candidate_id=second.id,
                roster_email=second.email,
                roster_name=second.name or "待注册",
            ),
            ExamCandidateScope(
                exam_id=exam.id,
                candidate_id=third.id,
                roster_email=third.email,
                roster_name=third.name or "待注册",
            ),
        ]
    )
    db.commit()
    second_start = exam_service.start_exam(db, exam.id, second.id)

    preview = exam_service.preview_bulk_retake(
        db,
        exam.id,
        candidate_ids=[first.id, second.id, third.id, outsider.id],
        void_existing=True,
    )
    assert preview.eligible_count == 2
    assert {row.reason for row in preview.rows if row.outcome == "skipped"} == {
        "尚无答题记录",
        "不在本场应考名单",
    }

    applied = exam_service.apply_bulk_retake(
        db,
        exam.id,
        candidate_ids=[first.id, second.id, third.id, outsider.id],
        void_existing=True,
        confirmation_title=exam.title,
        preview_fingerprint=preview.fingerprint,
        reason="办公室网络中断，统一安排补考",
        operator_subject="primary-operator",
    )
    db.commit()

    assert applied.granted_count == 2
    assert applied.voided_count == 2
    first_attempt = db.get(ExamAttempt, first_start.attempt_id)
    second_attempt = db.get(ExamAttempt, second_start.attempt_id)
    assert first_attempt is not None
    assert first_attempt.status == "voided"
    assert second_attempt is not None
    assert second_attempt.status == "voided"
    assert db.query(ExamRetakeGrant).filter_by(used_at=None).count() == 2
    refreshed = exam_service.preview_bulk_retake(
        db,
        exam.id,
        candidate_ids=[first.id, second.id],
        void_existing=True,
    )
    assert refreshed.eligible_count == 0
    assert all(row.reason == "已有未使用补考授权" for row in refreshed.rows)
    with pytest.raises(BulkRetakeConflictError, match="预览已经变化"):
        exam_service.apply_bulk_retake(
            db,
            exam.id,
            candidate_ids=[first.id, second.id],
            void_existing=True,
            confirmation_title=exam.title,
            preview_fingerprint=preview.fingerprint,
            reason="办公室网络中断，统一安排补考",
            operator_subject="primary-operator",
        )


def test_formal_evidence_manifest_is_checksummed_and_redacts_sensitive_refs(
    db: Session,
) -> None:
    exam, _candidate, start = _start_exam(db, title="证据考试")
    submit_answers(db, start.attempt_id, start.questions, ["A"])
    record_admin_event(
        db,
        operator_subject="primary-operator",
        action="smtp_preflight_passed",
        target_type="exam",
        target_id=exam.id,
        metadata={"exam_id": exam.id},
    )
    db.commit()

    evidence = exam_service.build_formal_exam_evidence(
        db,
        exam.id,
        operator_subject="primary-operator",
        artifact_references={
            "release_manifest_ref": "release-abc123.json",
            "preflight_ref": "preflight-pass.json",
            "smtp_ref": "smtp-token-secret.txt",
            "backup_ref": "backup-final-001.json",
            "close_exam_ref": None,
        },
    )

    assert len(evidence.checksum_sha256) == 64
    assert evidence.manifest["attempt_status_counts"] == {"submitted": 1}
    assert evidence.manifest["artifact_references"] == {
        "release_manifest_ref": "release-abc123.json",
        "preflight_ref": "preflight-pass.json",
        "backup_ref": "backup-final-001.json",
    }
    serialized = str(evidence.manifest).lower()
    assert "smtp-token-secret" not in serialized
    assert "password" not in serialized
