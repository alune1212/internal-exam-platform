from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.time import to_utc
from app.models import (
    AdminAuditEvent,
    Exam,
    ExamAttempt,
    ExamAttemptAnswer,
    ExamAttemptQuestion,
    ExamCandidateScope,
    ExamQuestionPool,
    ExamRetakeGrant,
)
from app.ops.internal_backup import BackupValidationError, validate_backup
from app.schemas.operations import (
    RetentionArchiveRead,
    RetentionDeleteRead,
    RetentionExamPreview,
    RetentionPreviewRead,
)
from app.services.audit_service import record_admin_event
from app.services.excel_security import escape_excel_cell
from app.services.operational_lock_service import assert_admin_mutation_allowed
from app.services.practice_retention_service import BACKUP_ID_PATTERN

RETENTION_MONTHS = 12
RETENTION_DAYS = 365
ARTIFACT_ID_PATTERN = re.compile(r"^retention-[0-9]{8}t[0-9]{6}z-[0-9a-f]{12}$")
RETENTION_ARCHIVE_SCHEMA_VERSION = 2
RETENTION_ARCHIVE_MEMBERS = frozenset({"archive.json", "archive.xlsx", "manifest.json"})
RETENTION_ARCHIVE_FILE_DIGESTS = frozenset({"archive.json", "archive.xlsx"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ARCHIVE_CHECKSUM_PATTERN = re.compile(
    r"^(?P<digest>[0-9a-f]{64})  (?P<filename>retention-[0-9]{8}t[0-9]{6}z-[0-9a-f]{12}\.zip)\n?$"
)
ROSTER_WORKBOOK_HEADERS = [
    "考试ID",
    "范围ID",
    "考生ID",
    "名单邮箱",
    "名单姓名",
    "部门",
    "职位",
    "考试分组",
    "备注",
]


class RetentionSafeguardError(DomainError):
    status_code = 409


def _validated_backup_path(backup_id: str) -> Path:
    """Resolve a backup ID without allowing it to leave the configured root."""

    if (
        not isinstance(backup_id, str)
        or BACKUP_ID_PATTERN.fullmatch(backup_id) is None
        or "/" in backup_id
        or "\\" in backup_id
        or ".." in backup_id
    ):
        raise RetentionSafeguardError("配对备份标识无效。")

    backup_root = Path(settings.backup_storage_dir)
    backup_path = backup_root / backup_id
    try:
        resolved_root = backup_root.resolve()
        resolved_backup = backup_path.resolve()
        if backup_path.is_symlink():
            raise RetentionSafeguardError("配对备份标识无效。")
        resolved_backup.relative_to(resolved_root)
    except RetentionSafeguardError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise RetentionSafeguardError("配对备份标识无效。") from exc
    return resolved_backup


def _fingerprint(cutoff_at: datetime, exams: list[RetentionExamPreview]) -> str:
    payload = {
        "cutoff_at": cutoff_at.isoformat(),
        "exams": [row.model_dump(mode="json") for row in exams],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def preview_retention(
    db: Session, *, now: datetime | None = None
) -> RetentionPreviewRead:
    generated_at = to_utc(now or datetime.now(UTC))
    cutoff_at = datetime.combine(
        (generated_at - timedelta(days=RETENTION_DAYS)).date(), time.min, UTC
    )
    rows: list[RetentionExamPreview] = []
    exams = db.query(Exam).order_by(Exam.id).all()
    for exam in exams:
        attempts = db.query(ExamAttempt).filter(ExamAttempt.exam_id == exam.id).all()
        attempt_ids = [attempt.id for attempt in attempts]
        attempt_question_count = (
            db.query(func.count(ExamAttemptQuestion.id))
            .join(ExamAttempt, ExamAttemptQuestion.attempt_id == ExamAttempt.id)
            .filter(ExamAttempt.exam_id == exam.id)
            .scalar()
            or 0
        )
        answer_count = (
            db.query(func.count(ExamAttemptAnswer.id))
            .join(
                ExamAttemptQuestion,
                ExamAttemptAnswer.attempt_question_id == ExamAttemptQuestion.id,
            )
            .join(ExamAttempt, ExamAttemptQuestion.attempt_id == ExamAttempt.id)
            .filter(ExamAttempt.exam_id == exam.id)
            .scalar()
            or 0
        )
        final_activity_candidates: list[datetime] = [
            to_utc(source)
            for source in (exam.created_at, exam.updated_at)
            if source is not None
        ]
        for attempt in attempts:
            final_activity_candidates.extend(
                to_utc(source)
                for source in (
                    attempt.created_at,
                    attempt.updated_at,
                    attempt.submitted_at,
                    attempt.voided_at,
                )
                if source is not None
            )
        final_activity_at = (
            max(final_activity_candidates)
            if final_activity_candidates
            else datetime.min.replace(tzinfo=UTC)
        )
        reasons: list[str] = []
        if exam.status != "archived":
            reasons.append("考试尚未归档")
        if any(attempt.status == "in_progress" for attempt in attempts):
            reasons.append("仍有进行中的正式考试记录")
        if final_activity_at > cutoff_at:
            reasons.append("最终活动距今未满 12 个月")
        candidate_ids = {
            row[0]
            for row in db.query(ExamCandidateScope.candidate_id)
            .filter(ExamCandidateScope.exam_id == exam.id)
            .all()
        } | {attempt.candidate_id for attempt in attempts}
        audit_evidence_count = sum(
            1
            for event in db.query(AdminAuditEvent).all()
            if (event.target_type == "exam" and event.target_id == str(exam.id))
            or event.metadata_json.get("exam_id") == exam.id
        )
        rows.append(
            RetentionExamPreview(
                exam_id=exam.id,
                title=exam.title,
                final_activity_at=final_activity_at,
                eligible=not reasons,
                reasons=reasons or ["符合 12 个月归档删除条件"],
                attempt_count=len(attempt_ids),
                attempt_question_count=int(attempt_question_count),
                answer_count=int(answer_count),
                roster_count=db.query(ExamCandidateScope)
                .filter(ExamCandidateScope.exam_id == exam.id)
                .count(),
                retake_grant_count=db.query(ExamRetakeGrant)
                .filter(ExamRetakeGrant.exam_id == exam.id)
                .count(),
                frozen_pool_count=db.query(ExamQuestionPool)
                .filter(ExamQuestionPool.exam_id == exam.id)
                .count(),
                protected_candidate_count=len(candidate_ids),
                audit_evidence_count=audit_evidence_count,
            )
        )
    return RetentionPreviewRead(
        generated_at=generated_at,
        cutoff_at=cutoff_at,
        retention_months=RETENTION_MONTHS,
        fingerprint=_fingerprint(cutoff_at, rows),
        exams=rows,
    )


def _eligible_rows(
    preview: RetentionPreviewRead, exam_ids: list[int], fingerprint: str
) -> list[RetentionExamPreview]:
    normalized_ids = sorted(set(exam_ids))
    if not normalized_ids or normalized_ids != sorted(exam_ids):
        raise RetentionSafeguardError("必须提供非空、唯一且有序的考试 ID。")
    if preview.fingerprint != fingerprint:
        raise RetentionSafeguardError("保留预览已过期，请重新预览。")
    rows_by_id = {row.exam_id: row for row in preview.exams}
    if any(
        exam_id not in rows_by_id or not rows_by_id[exam_id].eligible
        for exam_id in normalized_ids
    ):
        raise RetentionSafeguardError("所选考试包含不符合保留删除条件的记录。")
    return [rows_by_id[exam_id] for exam_id in normalized_ids]


def _scope_payload(scope: ExamCandidateScope) -> dict[str, object]:
    return {
        "scope_id": scope.id,
        "candidate_id": scope.candidate_id,
        "roster_email": scope.roster_email,
        "roster_name": scope.roster_name,
        "department": scope.department,
        "position": scope.position,
        "exam_group": scope.exam_group,
        "remark": scope.roster_remark,
    }


def _archive_payload(db: Session, exam_ids: list[int]) -> dict[str, Any]:
    exams = (
        db.query(Exam)
        .options(
            selectinload(Exam.candidate_scopes),
            selectinload(Exam.attempts)
            .selectinload(ExamAttempt.questions)
            .selectinload(ExamAttemptQuestion.answer),
        )
        .filter(Exam.id.in_(exam_ids))
        .order_by(Exam.id)
        .all()
    )
    return {
        "schema_version": RETENTION_ARCHIVE_SCHEMA_VERSION,
        "exams": [
            {
                "id": exam.id,
                "title": exam.title,
                "status": exam.status,
                "available_from": exam.available_from,
                "available_until": exam.available_until,
                "scopes": [
                    _scope_payload(scope)
                    for scope in sorted(exam.candidate_scopes, key=lambda row: row.id)
                ],
                "attempts": [
                    {
                        "id": attempt.id,
                        "candidate_id": attempt.candidate_id,
                        "status": attempt.status,
                        "started_at": attempt.started_at,
                        "submitted_at": attempt.submitted_at,
                        "score": str(attempt.score),
                        "total_score": str(attempt.total_score),
                        "questions": [
                            {
                                "id": question.id,
                                "stem_snapshot": question.stem_snapshot,
                                "options_snapshot": question.options_snapshot,
                                "correct_answer_snapshot": question.correct_answer_snapshot,
                                "analysis_snapshot": question.analysis_snapshot,
                                "selected_answer": question.answer.selected_answer
                                if question.answer
                                else None,
                                "is_correct": question.answer.is_correct
                                if question.answer
                                else None,
                            }
                            for question in attempt.questions
                        ],
                    }
                    for attempt in sorted(exam.attempts, key=lambda attempt: attempt.id)
                ],
            }
            for exam in exams
        ],
    }


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n"
    ).encode("utf-8")


def _excel_row(values: list[object]) -> list[object]:
    return [escape_excel_cell(value) for value in values]


def _workbook_bytes(payload: dict[str, Any]) -> bytes:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "考试归档"
    summary.append(["考试ID", "考试标题", "状态", "考试记录数"])
    roster = workbook.create_sheet("冻结名单")
    roster.append(ROSTER_WORKBOOK_HEADERS)
    attempts = workbook.create_sheet("考试记录")
    attempts.append(["考试ID", "记录ID", "考试人ID", "状态", "得分", "总分"])
    answers = workbook.create_sheet("作答快照")
    answers.append(["记录ID", "题目快照ID", "题干", "所选答案", "正确答案", "是否正确"])
    for exam in payload["exams"]:
        summary.append(
            _excel_row(
                [exam["id"], exam["title"], exam["status"], len(exam["attempts"])]
            )
        )
        for scope in exam["scopes"]:
            roster.append(
                _excel_row(
                    [
                        exam["id"],
                        scope["scope_id"],
                        scope["candidate_id"],
                        scope["roster_email"],
                        scope["roster_name"],
                        scope["department"],
                        scope["position"],
                        scope["exam_group"],
                        scope["remark"],
                    ]
                )
            )
        for attempt in exam["attempts"]:
            attempts.append(
                _excel_row(
                    [
                        exam["id"],
                        attempt["id"],
                        attempt["candidate_id"],
                        attempt["status"],
                        attempt["score"],
                        attempt["total_score"],
                    ]
                )
            )
            for question in attempt["questions"]:
                answers.append(
                    _excel_row(
                        [
                            attempt["id"],
                            question["id"],
                            question["stem_snapshot"],
                            question["selected_answer"],
                            question["correct_answer_snapshot"],
                            question["is_correct"],
                        ]
                    )
                )
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def create_retention_archive(
    db: Session,
    *,
    exam_ids: list[int],
    preview_fingerprint: str,
    operator_subject: str,
    now: datetime | None = None,
) -> RetentionArchiveRead:
    assert_admin_mutation_allowed(db)
    created_at = to_utc(now or datetime.now(UTC))
    preview = preview_retention(db, now=created_at)
    rows = _eligible_rows(preview, exam_ids, preview_fingerprint)
    payload = _archive_payload(db, [row.exam_id for row in rows])
    json_content = _json_bytes(payload)
    workbook_content = _workbook_bytes(payload)
    artifact_id = (
        f"retention-{created_at.strftime('%Y%m%dt%H%M%Sz').lower()}-"
        f"{preview.fingerprint[:12]}"
    )
    manifest = {
        "schema_version": RETENTION_ARCHIVE_SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "created_at": created_at.isoformat(),
        "operator_subject": operator_subject,
        "exam_ids": [row.exam_id for row in rows],
        "preview_fingerprint": preview.fingerprint,
        "roster_counts": {
            str(exam["id"]): len(exam["scopes"]) for exam in payload["exams"]
        },
        "roster_count": sum(len(exam["scopes"]) for exam in payload["exams"]),
        "files": {
            "archive.json": hashlib.sha256(json_content).hexdigest(),
            "archive.xlsx": hashlib.sha256(workbook_content).hexdigest(),
        },
    }
    manifest_content = _json_bytes(manifest)
    archive_dir = Path(settings.lifecycle_archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{artifact_id}.zip"
    temporary_path = archive_dir / f".{artifact_id}.tmp"
    with zipfile.ZipFile(
        temporary_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as bundle:
        bundle.writestr("archive.json", json_content)
        bundle.writestr("archive.xlsx", workbook_content)
        bundle.writestr("manifest.json", manifest_content)
    temporary_path.replace(archive_path)
    archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (archive_dir / f"{artifact_id}.manifest.json").write_bytes(manifest_content)
    (archive_dir / f"{artifact_id}.sha256").write_text(
        f"{archive_sha256}  {archive_path.name}\n", encoding="ascii"
    )
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="retention_archive_created",
        target_type="exam_set",
        target_id=",".join(str(row.exam_id) for row in rows),
        metadata={"archive_ref": artifact_id, "count": len(rows)},
    )
    db.commit()
    return RetentionArchiveRead(
        artifact_id=artifact_id,
        created_at=created_at,
        exam_ids=[row.exam_id for row in rows],
        preview_fingerprint=preview.fingerprint,
        archive_sha256=archive_sha256,
    )


def _archive_scope_identity(scope: ExamCandidateScope) -> dict[str, object]:
    return _scope_payload(scope)


def _validate_scope_payload(scope: object) -> dict[str, object]:
    required = {
        "scope_id",
        "candidate_id",
        "roster_email",
        "roster_name",
        "department",
        "position",
        "exam_group",
        "remark",
    }
    if not isinstance(scope, dict) or set(scope) != required:
        raise RetentionSafeguardError("归档冻结名单字段不完整。")
    scope_data = cast("dict[str, object]", scope)
    for field in ("scope_id", "candidate_id"):
        value = scope_data[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise RetentionSafeguardError("归档冻结名单标识无效。")
    for field in ("roster_email", "roster_name"):
        value = scope_data[field]
        if not isinstance(value, str) or not value.strip():
            raise RetentionSafeguardError("归档冻结名单身份字段无效。")
    for field in ("department", "position", "exam_group", "remark"):
        value = scope_data[field]
        if value is not None and not isinstance(value, str):
            raise RetentionSafeguardError("归档冻结名单组织字段无效。")
    return scope_data


def _validate_archive_payload(
    payload: object, manifest: dict[str, object], *, schema_version: int
) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("exams"), list):
        raise RetentionSafeguardError("归档 JSON 内容无效。")
    payload_data = cast("dict[str, Any]", payload)
    exam_ids = manifest.get("exam_ids")
    if not isinstance(exam_ids, list):
        raise RetentionSafeguardError("归档考试标识不完整。")
    payload_exams = payload_data["exams"]
    payload_ids: list[int] = []
    for exam in payload_exams:
        if not isinstance(exam, dict):
            raise RetentionSafeguardError("归档考试内容无效。")
        exam_id = exam.get("id")
        if isinstance(exam_id, bool) or not isinstance(exam_id, int) or exam_id <= 0:
            raise RetentionSafeguardError("归档考试标识无效。")
        payload_ids.append(exam_id)
    if payload_ids != exam_ids:
        raise RetentionSafeguardError("归档 JSON 与 manifest 考试标识不匹配。")

    if schema_version != RETENTION_ARCHIVE_SCHEMA_VERSION:
        return payload_data
    if payload_data.get("schema_version") != RETENTION_ARCHIVE_SCHEMA_VERSION:
        raise RetentionSafeguardError("归档 JSON schema 版本不匹配。")
    roster_counts = manifest.get("roster_counts")
    total_roster_count = manifest.get("roster_count")
    if not isinstance(roster_counts, dict) or isinstance(total_roster_count, bool):
        raise RetentionSafeguardError("归档冻结名单计数不完整。")
    if not isinstance(total_roster_count, int) or total_roster_count < 0:
        raise RetentionSafeguardError("归档冻结名单计数无效。")
    if set(roster_counts) != {str(exam_id) for exam_id in exam_ids}:
        raise RetentionSafeguardError("归档冻结名单计数与考试标识不匹配。")
    calculated_total = 0
    for exam in payload_exams:
        scopes = exam.get("scopes")
        if not isinstance(scopes, list):
            raise RetentionSafeguardError("归档冻结名单缺失。")
        scope_ids: list[int] = []
        for scope in scopes:
            validated = _validate_scope_payload(scope)
            scope_id = validated["scope_id"]
            assert isinstance(scope_id, int)
            scope_ids.append(scope_id)
        if scope_ids != sorted(set(scope_ids)):
            raise RetentionSafeguardError("归档冻结名单顺序或标识重复。")
        exam_id = exam["id"]
        expected_count = roster_counts.get(str(exam_id))
        if (
            isinstance(expected_count, bool)
            or not isinstance(expected_count, int)
            or expected_count != len(scopes)
        ):
            raise RetentionSafeguardError("归档冻结名单计数校验失败。")
        calculated_total += len(scopes)
    if calculated_total != total_roster_count:
        raise RetentionSafeguardError("归档冻结名单总数校验失败。")
    return payload_data


def _load_archive_contents(
    artifact_id: str,
) -> tuple[dict[str, object], dict[str, Any], dict[str, bytes]]:
    if ARTIFACT_ID_PATTERN.fullmatch(artifact_id) is None:
        raise RetentionSafeguardError("归档产物标识无效。")
    archive_dir = Path(settings.lifecycle_archive_dir)
    archive_path = archive_dir / f"{artifact_id}.zip"
    manifest_path = archive_dir / f"{artifact_id}.manifest.json"
    checksum_path = archive_dir / f"{artifact_id}.sha256"
    if (
        not archive_path.is_file()
        or not manifest_path.is_file()
        or not checksum_path.is_file()
        or archive_path.is_symlink()
        or manifest_path.is_symlink()
        or checksum_path.is_symlink()
    ):
        raise RetentionSafeguardError("归档产物不完整。")
    try:
        checksum_content = checksum_path.read_text(encoding="ascii")
        checksum_match = ARCHIVE_CHECKSUM_PATTERN.fullmatch(checksum_content)
        archive_bytes = archive_path.read_bytes()
        external_manifest_bytes = manifest_path.read_bytes()
    except (OSError, UnicodeError) as exc:
        raise RetentionSafeguardError("归档产物无法读取。") from exc
    if checksum_match is None or checksum_match.group("filename") != archive_path.name:
        raise RetentionSafeguardError("归档 checksum 文件格式无效。")
    if hashlib.sha256(archive_bytes).hexdigest() != checksum_match.group("digest"):
        raise RetentionSafeguardError("归档产物 checksum 校验失败。")

    try:
        with zipfile.ZipFile(BytesIO(archive_bytes)) as bundle:
            infos = bundle.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or set(names) != RETENTION_ARCHIVE_MEMBERS:
                raise RetentionSafeguardError("归档 ZIP 成员不完整或包含额外文件。")
            members = {name: bundle.read(name) for name in RETENTION_ARCHIVE_MEMBERS}
    except RetentionSafeguardError:
        raise
    except (KeyError, OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
        raise RetentionSafeguardError("归档 ZIP 结构校验失败。") from exc

    inner_manifest_bytes = members["manifest.json"]
    if inner_manifest_bytes != external_manifest_bytes:
        raise RetentionSafeguardError("归档内外 manifest 不一致。")
    try:
        manifest = json.loads(external_manifest_bytes)
        payload = json.loads(members["archive.json"])
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RetentionSafeguardError("归档 JSON 内容无效。") from exc
    if not isinstance(manifest, dict):
        raise RetentionSafeguardError("归档 manifest 内容无效。")
    schema_version = manifest.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version not in {1, RETENTION_ARCHIVE_SCHEMA_VERSION}
    ):
        raise RetentionSafeguardError("归档 schema 版本不受支持。")
    if manifest.get("artifact_id") != artifact_id:
        raise RetentionSafeguardError("归档 manifest 标识不匹配。")
    exam_ids = manifest.get("exam_ids")
    if (
        not isinstance(exam_ids, list)
        or any(
            isinstance(exam_id, bool) or not isinstance(exam_id, int) or exam_id <= 0
            for exam_id in exam_ids
        )
        or exam_ids != sorted(set(exam_ids))
    ):
        raise RetentionSafeguardError("归档 manifest 考试标识无效。")
    preview_fingerprint = manifest.get("preview_fingerprint")
    if (
        not isinstance(preview_fingerprint, str)
        or SHA256_PATTERN.fullmatch(preview_fingerprint) is None
    ):
        raise RetentionSafeguardError("归档预览指纹无效。")
    try:
        datetime.fromisoformat(str(manifest["created_at"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise RetentionSafeguardError("归档创建时间无效。") from exc
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != RETENTION_ARCHIVE_FILE_DIGESTS:
        raise RetentionSafeguardError("归档文件 manifest 不完整。")
    for filename in RETENTION_ARCHIVE_FILE_DIGESTS:
        expected_digest = files.get(filename)
        if (
            not isinstance(expected_digest, str)
            or SHA256_PATTERN.fullmatch(expected_digest) is None
            or hashlib.sha256(members[filename]).hexdigest() != expected_digest
        ):
            raise RetentionSafeguardError(f"归档文件 checksum 校验失败：{filename}")
    _validate_archive_payload(payload, manifest, schema_version=schema_version)
    return manifest, payload, members


def _load_archive_manifest(artifact_id: str) -> dict[str, object]:
    manifest, _payload, _members = _load_archive_contents(artifact_id)
    return manifest


def _validate_current_roster(
    db: Session,
    payload: dict[str, Any],
    preview: RetentionPreviewRead,
    exam_ids: list[int],
) -> None:
    current_payload = json.loads(_json_bytes(_archive_payload(db, exam_ids)))
    if current_payload != payload:
        raise RetentionSafeguardError("归档内容与当前来源不匹配。")
    payload_by_id = {exam["id"]: exam for exam in payload["exams"]}
    preview_by_id = {row.exam_id: row for row in preview.exams}
    for exam_id in exam_ids:
        exam = payload_by_id.get(exam_id)
        preview_row = preview_by_id.get(exam_id)
        if exam is None or preview_row is None:
            raise RetentionSafeguardError("归档考试与当前预览不匹配。")
        current_scopes = (
            db.query(ExamCandidateScope)
            .filter(ExamCandidateScope.exam_id == exam_id)
            .order_by(ExamCandidateScope.id)
            .with_for_update()
            .all()
        )
        archived_scopes = exam.get("scopes")
        if not isinstance(archived_scopes, list):
            raise RetentionSafeguardError("归档冻结名单缺失。")
        current_identity = [_archive_scope_identity(scope) for scope in current_scopes]
        if current_identity != archived_scopes:
            raise RetentionSafeguardError("归档冻结名单与当前来源不匹配。")
        if preview_row.roster_count != len(current_scopes):
            raise RetentionSafeguardError("归档冻结名单计数与当前来源不匹配。")


def _validate_roster_workbook(payload: dict[str, Any], workbook_content: bytes) -> None:
    try:
        workbook = load_workbook(
            BytesIO(workbook_content), read_only=True, data_only=False
        )
    except (
        AttributeError,
        BadZipFile,
        EOFError,
        IndexError,
        InvalidFileException,
        KeyError,
        OSError,
        ParseError,
        TypeError,
        ValueError,
    ) as exc:
        raise RetentionSafeguardError("归档 workbook 无法读取。") from exc
    try:
        if "冻结名单" not in workbook.sheetnames:
            raise RetentionSafeguardError("归档 workbook 缺少冻结名单。")
        rows = workbook["冻结名单"].iter_rows(values_only=True)
        if list(next(rows, ())) != ROSTER_WORKBOOK_HEADERS:
            raise RetentionSafeguardError("归档 workbook 冻结名单表头无效。")
        actual_rows = [
            list(row) for row in rows if any(value is not None for value in row)
        ]
        expected_rows = [
            _excel_row(
                [
                    exam["id"],
                    scope["scope_id"],
                    scope["candidate_id"],
                    scope["roster_email"],
                    scope["roster_name"],
                    scope["department"],
                    scope["position"],
                    scope["exam_group"],
                    scope["remark"],
                ]
            )
            for exam in payload["exams"]
            for scope in exam["scopes"]
        ]
        if actual_rows != expected_rows:
            raise RetentionSafeguardError("归档 workbook 冻结名单与 JSON 不匹配。")
    finally:
        workbook.close()


def delete_retained_exams(
    db: Session,
    *,
    exam_ids: list[int],
    preview_fingerprint: str,
    archive_id: str,
    backup_id: str,
    confirmation: str,
    operator_subject: str,
    now: datetime | None = None,
) -> RetentionDeleteRead:
    assert_admin_mutation_allowed(db)
    deleted_at = to_utc(now or datetime.now(UTC))
    preview = preview_retention(db, now=deleted_at)
    rows = _eligible_rows(preview, exam_ids, preview_fingerprint)
    normalized_ids = [row.exam_id for row in rows]
    expected_confirmation = f"DELETE EXAMS {','.join(map(str, normalized_ids))}"
    if confirmation != expected_confirmation:
        raise RetentionSafeguardError("删除确认文本不匹配。")
    manifest, archive_payload, archive_members = _load_archive_contents(archive_id)
    if manifest.get("schema_version") != RETENTION_ARCHIVE_SCHEMA_VERSION:
        raise RetentionSafeguardError("schema v1 归档仅可读取，不能授权删除。")
    if (
        manifest.get("exam_ids") != normalized_ids
        or manifest.get("preview_fingerprint") != preview.fingerprint
    ):
        raise RetentionSafeguardError("归档产物与当前预览或所选考试不匹配。")
    _validate_current_roster(db, archive_payload, preview, normalized_ids)
    _validate_roster_workbook(archive_payload, archive_members["archive.xlsx"])
    backup_path = _validated_backup_path(backup_id)
    try:
        backup_manifest = validate_backup(backup_path)
    except BackupValidationError as exc:
        raise RetentionSafeguardError("配对备份未通过校验。") from exc
    try:
        archive_created_at = datetime.fromisoformat(str(manifest["created_at"]))
        backup_created_at = datetime.fromisoformat(str(backup_manifest["created_at"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise RetentionSafeguardError("归档或配对备份创建时间无效。") from exc
    if to_utc(backup_created_at) < to_utc(archive_created_at):
        raise RetentionSafeguardError("配对备份早于归档产物，请重新创建并验证备份。")

    attempt_ids = [
        row[0]
        for row in db.query(ExamAttempt.id)
        .filter(ExamAttempt.exam_id.in_(normalized_ids))
        .all()
    ]
    if attempt_ids:
        question_ids = [
            row[0]
            for row in db.query(ExamAttemptQuestion.id)
            .filter(ExamAttemptQuestion.attempt_id.in_(attempt_ids))
            .all()
        ]
        if question_ids:
            db.query(ExamAttemptAnswer).filter(
                ExamAttemptAnswer.attempt_question_id.in_(question_ids)
            ).delete(synchronize_session=False)
        db.query(ExamAttemptQuestion).filter(
            ExamAttemptQuestion.attempt_id.in_(attempt_ids)
        ).delete(synchronize_session=False)
    db.query(ExamRetakeGrant).filter(
        ExamRetakeGrant.exam_id.in_(normalized_ids)
    ).delete(synchronize_session=False)
    db.query(ExamCandidateScope).filter(
        ExamCandidateScope.exam_id.in_(normalized_ids)
    ).delete(synchronize_session=False)
    db.query(ExamQuestionPool).filter(
        ExamQuestionPool.exam_id.in_(normalized_ids)
    ).delete(synchronize_session=False)
    db.query(ExamAttempt).filter(ExamAttempt.exam_id.in_(normalized_ids)).delete(
        synchronize_session=False
    )
    db.query(Exam).filter(Exam.id.in_(normalized_ids)).delete(synchronize_session=False)
    protected_candidate_count = sum(row.protected_candidate_count for row in rows)
    record_admin_event(
        db,
        operator_subject=operator_subject,
        action="retention_deleted",
        target_type="exam_set",
        target_id=",".join(map(str, normalized_ids)),
        metadata={
            "archive_ref": archive_id,
            "backup_ref": backup_id,
            "deleted_count": len(normalized_ids),
        },
    )
    db.commit()
    db.expire_all()
    return RetentionDeleteRead(
        deleted_exam_ids=normalized_ids,
        deleted_attempt_count=len(attempt_ids),
        protected_candidate_count=protected_candidate_count,
        archive_id=archive_id,
        backup_id=backup_id,
    )
