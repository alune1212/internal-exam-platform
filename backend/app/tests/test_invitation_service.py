from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import AdminAuditEvent, Candidate, Exam, ExamCandidateScope
from app.services import invitation_service


def _published_scope(db):
    exam = Exam(title="安全考试", duration_minutes=60, status="active")
    candidate = Candidate(name="用户", email="user@example.com", status="active")
    db.add_all([exam, candidate])
    db.flush()
    scope = ExamCandidateScope(
        exam_id=exam.id,
        candidate_id=candidate.id,
        roster_email="user@example.com",
        roster_name="名单名",
    )
    db.add(scope)
    db.commit()
    return exam, scope


def test_failed_invitation_persists_sanitized_class_and_resend_targets_failed(
    db, monkeypatch
) -> None:
    exam, scope = _published_scope(db)
    invitation_service.clear_invitation_rate_limiter()
    invitation_service.clear_invitation_email_outbox()
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)

    def fail(**_kwargs):
        raise invitation_service.PermanentEmailDeliveryError()

    monkeypatch.setattr(invitation_service, "send_invitation_email", fail)
    first = invitation_service.claim_invitations(
        db, exam.id, mode="initial", operator_subject="admin"
    )
    invitation_service.deliver_claimed_invitations(
        first.scope_ids, first.claim_owner, session_factory=factory
    )
    db.expire_all()
    assert db.get(ExamCandidateScope, scope.id).invitation_status == "failed"
    assert db.get(ExamCandidateScope, scope.id).invitation_error_class == "permanent"

    monkeypatch.setattr(
        invitation_service, "send_invitation_email", lambda **_kwargs: None
    )
    retry = invitation_service.claim_invitations(
        db, exam.id, mode="resend", operator_subject="admin"
    )
    assert retry.accepted_count == 1
    invitation_service.deliver_claimed_invitations(
        retry.scope_ids, retry.claim_owner, session_factory=factory
    )
    db.expire_all()
    assert db.get(ExamCandidateScope, scope.id).invitation_status == "sent"


def test_invitation_link_contains_only_same_origin_exam_path(monkeypatch) -> None:
    monkeypatch.setattr(
        settings, "candidate_public_base_url", "http://lan.example:8080"
    )
    url = invitation_service.build_invitation_url(7)
    assert url == "http://lan.example:8080/exams/7/start"
    assert all(marker not in url for marker in ("token", "otp", "email", "scope"))


def test_invitation_audit_keeps_scheduling_and_delivery_counts(db, monkeypatch) -> None:
    exam, scope = _published_scope(db)
    invitation_service.clear_invitation_rate_limiter()
    invitation_service.clear_invitation_email_outbox()
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)

    scheduled = invitation_service.claim_invitations(
        db, exam.id, mode="initial", operator_subject="audit-admin"
    )
    scheduled_event = (
        db.query(AdminAuditEvent)
        .filter(AdminAuditEvent.action == "exam_invitation_scheduled")
        .one()
    )
    assert scheduled.selected_count == 1
    assert scheduled_event.metadata_json == {
        "exam_id": exam.id,
        "selected_count": 1,
        "accepted_count": 1,
        "rejected_count": 0,
        "mode": "initial",
    }

    monkeypatch.setattr(invitation_service, "send_invitation_email", lambda **_: None)
    invitation_service.deliver_claimed_invitations(
        scheduled.scope_ids,
        scheduled.claim_owner,
        session_factory=factory,
        operator_subject="audit-admin",
    )
    final_event = (
        db.query(AdminAuditEvent)
        .filter(AdminAuditEvent.action == "exam_invitation_sent")
        .one()
    )
    assert final_event.metadata_json["sent_count"] == 1
    assert final_event.metadata_json["failed_count"] == 0
    assert final_event.metadata_json["outcome_classes"] == ["sent"]
    assert scope.roster_email not in str(final_event.metadata_json)
