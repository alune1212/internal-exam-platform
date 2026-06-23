# Security Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Codex Security deep-scan findings without adding complex RBAC, queues, or services.

**Architecture:** Keep route files thin and put security decisions in `backend/app/services/` or `backend/app/core/`. Candidate authentication becomes name plus per-candidate login code, practice APIs become candidate-authenticated and avoid active formal exam pools, and deployment/config/Excel hardening remains local to the existing first-phase scaffold.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, openpyxl, React, TypeScript, Vite, Tailwind, Docker Compose, pytest.

---

## Scope Check

This scan touches several independent subsystems: candidate auth, exam attempt state, practice mode, login throttling, production config, Docker Compose exposure, Excel export escaping, and XLSX import parsing. This plan keeps them in one umbrella remediation plan because they came from one security review and can be executed as independent commits. If execution needs parallel branches, split on the task boundaries below.

Verification commands below use raw `uv`, `npm`, and `docker-compose` commands because this workspace currently does not have `rtk` installed. If `rtk` is available in the execution environment, prefix each command segment with `rtk`.

## File Structure

- `backend/app/models/candidate.py`: add `login_code` as the candidate-held login secret.
- `backend/alembic/versions/202606220001_add_candidate_login_code.py`: add and drop the `candidate.login_code` column.
- `backend/app/schemas/candidate.py`: accept `login_code` for login/import input while keeping it out of `CandidateRead`.
- `backend/app/services/candidate_service.py`: require login code and bind employee number to name when supplied.
- `backend/app/services/import_service.py`: import and validate candidate `login_code`; add XLSX archive pre-parse limits.
- `backend/app/services/template_service.py`: add login code to candidate template headers and example row.
- `frontend/src/api/auth.ts`: send `login_code` from candidate login form.
- `frontend/src/pages/LoginPage.tsx`: render a login code field and update validation/copy.
- `backend/app/services/exam_service.py`: block result reads before submit.
- `backend/app/api/practice.py`: require candidate token for practice question listing.
- `backend/app/services/practice_service.py`: list practice-safe questions and reject answer disclosure for active formal exam pool questions.
- `backend/app/core/rate_limit.py`: small in-memory login rate limiter.
- `backend/app/api/auth.py` and `backend/app/api/candidates.py`: call the limiter for public token issuance endpoints.
- `backend/app/core/config.py`: reject repository-published sample secrets in production and add XLSX archive budget settings.
- `docker-compose.yml`: remove host-published DB/backend/frontend ports from the default stack.
- `README.md`, `docs/handoff.md`, `docs/official-exam-uat-checklist.md`, `CLAUDE.md`: update security and startup notes.
- `backend/app/services/excel_security.py`: normalize leading controls before formula-prefix checks.
- Tests under `backend/app/tests/` and `frontend/src/pages/`.

## Task 1: Add Candidate Login Code Data Model And Import Support

**Files:**
- Create: `backend/alembic/versions/202606220001_add_candidate_login_code.py`
- Modify: `backend/app/models/candidate.py`
- Modify: `backend/app/schemas/candidate.py`
- Modify: `backend/app/services/import_service.py`
- Modify: `backend/app/services/template_service.py`
- Test: `backend/app/tests/test_candidate_import_service.py`
- Test: `backend/app/tests/test_template_service.py`

- [ ] **Step 1: Write failing candidate import tests**

Append these tests to `backend/app/tests/test_candidate_import_service.py`:

```python
def test_candidate_import_requires_login_code(db: Session) -> None:
    workbook = build_workbook(
        CANDIDATE_HEADERS,
        [
            {
                "name": "缺少登录码",
                "employee_no": "LC0001",
                "status": "active",
            }
        ],
    )

    result = import_candidates_from_workbook(
        db, workbook, file_name="missing-login-code.xlsx"
    )

    assert result.success_count == 0
    assert result.failed_count == 1
    assert result.failures[0].row_number == 2
    assert result.failures[0].reason == "登录码不能为空"


def test_candidate_import_persists_login_code(db: Session) -> None:
    workbook = build_workbook(
        CANDIDATE_HEADERS,
        [
            {
                "name": "带登录码",
                "employee_no": "LC0002",
                "login_code": "invite-0002",
                "status": "active",
            }
        ],
    )

    result = import_candidates_from_workbook(
        db, workbook, file_name="with-login-code.xlsx"
    )
    candidate = db.query(Candidate).filter_by(employee_no="LC0002").one()

    assert result.success_count == 1
    assert result.failed_count == 0
    assert candidate.login_code == "invite-0002"
```

Update the local `CANDIDATE_HEADERS` test constant if this file defines one:

```python
CANDIDATE_HEADERS = [
    "name",
    "employee_no",
    "login_code",
    "department",
    "position",
    "phone_suffix",
    "email",
    "exam_group",
    "should_attend",
    "status",
    "remark",
]
```

- [ ] **Step 2: Write failing template test**

Add this assertion to `backend/app/tests/test_template_service.py` in the candidate template test:

```python
def test_candidate_template_contains_login_code_column() -> None:
    wb = load_workbook(generate_candidate_template())
    sheet = wb.active
    headers = [cell.value for cell in sheet[1]]

    assert headers == [
        "name",
        "employee_no",
        "login_code",
        "department",
        "position",
        "phone_suffix",
        "email",
        "exam_group",
        "should_attend",
        "status",
        "remark",
    ]
    assert sheet.cell(2, 3).value == "invite-1001"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd backend
uv run pytest app/tests/test_candidate_import_service.py::test_candidate_import_requires_login_code app/tests/test_candidate_import_service.py::test_candidate_import_persists_login_code app/tests/test_template_service.py::test_candidate_template_contains_login_code_column -v
```

Expected: fails because `Candidate` has no `login_code` column and the template does not include the column.

- [ ] **Step 4: Add Alembic migration**

Create `backend/alembic/versions/202606220001_add_candidate_login_code.py`:

```python
"""add_candidate_login_code

Revision ID: 202606220001
Revises: 202606170001
Create Date: 2026-06-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606220001"
down_revision: str | None = "202606170001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate",
        sa.Column("login_code", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate", "login_code")
```

If the local Alembic head is not `202606170001`, run `cd backend && uv run alembic heads` and set `down_revision` to the single current head shown by Alembic.

- [ ] **Step 5: Add model and schema fields without exposing the code**

Modify `backend/app/models/candidate.py`:

```python
class Candidate(TimestampMixin, Base):
    __tablename__ = "candidate"
    __table_args__ = (
        Index("ix_candidate_name", "name"),
        Index("ix_candidate_exam_group", "exam_group"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    employee_no: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True
    )
    login_code: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    position: Mapped[str | None] = mapped_column(String(100))
    phone_suffix: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    exam_group: Mapped[str | None] = mapped_column(String(100))
    should_attend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CandidateStatus.active.value, index=True
    )
    remark: Mapped[str | None] = mapped_column(Text)

    attempts = relationship("ExamAttempt", back_populates="candidate")
    practice_answers = relationship("PracticeAnswer", back_populates="candidate")
```

Modify `backend/app/schemas/candidate.py`:

```python
class CandidateLoginRequest(BaseModel):
    name: str
    login_code: str
    employee_no: str | None = None


class CandidateBase(BaseModel):
    name: str
    employee_no: str | None = None
    department: str | None = None
    position: str | None = None
    phone_suffix: str | None = None
    email: EmailStr | None = None
    exam_group: str | None = None
    should_attend: bool = True
    status: str = "active"
    remark: str | None = None


class CandidateRead(CandidateBase, ORMModel):
    id: int


class CandidateLoginResponse(CandidateRead):
    token: str


class CandidateImportRow(CandidateBase):
    login_code: str
```

- [ ] **Step 6: Import and template login codes**

Modify `backend/app/services/template_service.py`:

```python
CANDIDATE_HEADERS = [
    "name",
    "employee_no",
    "login_code",
    "department",
    "position",
    "phone_suffix",
    "email",
    "exam_group",
    "should_attend",
    "status",
    "remark",
]

CANDIDATE_EXAMPLES = [
    [
        "张三",
        "E1001",
        "invite-1001",
        "综合管理部",
        "工程师",
        "1234",
        "zhangsan@example.com",
        "A组",
        "true",
        "active",
        None,
    ],
]
```

Modify `backend/app/services/import_service.py` in `_validate_candidate_import_row` and `_build_candidate`:

```python
def _validate_candidate_import_row(
    row: dict[str, Any],
    existing_employee_numbers: set[str],
    existing_names_without_no: set[str],
) -> str | None:
    name = _optional_text(row.get("name"))
    employee_no = _optional_text(row.get("employee_no"))
    login_code = _optional_text(row.get("login_code"))
    status = _text(row.get("status") or DEFAULT_STATUS).lower()

    if not name:
        return "姓名不能为空"
    if not login_code:
        return "登录码不能为空"
    if status not in VALID_STATUSES:
        return "status 只能是 active 或 inactive"
    if employee_no:
        if employee_no in existing_employee_numbers:
            return "员工号已存在"
        return None

    if name in existing_names_without_no:
        return "姓名已存在"
    return None


def _build_candidate(row: dict[str, Any]) -> Candidate:
    return Candidate(
        name=_text(row.get("name")),
        employee_no=_optional_text(row.get("employee_no")),
        login_code=_text(row.get("login_code")),
        department=_optional_text(row.get("department")),
        position=_optional_text(row.get("position")),
        phone_suffix=_optional_text(row.get("phone_suffix")),
        email=_optional_text(row.get("email")),
        exam_group=_optional_text(row.get("exam_group")),
        should_attend=_parse_bool(row.get("should_attend"), default=True),
        status=_text(row.get("status") or DEFAULT_STATUS).lower(),
        remark=_optional_text(row.get("remark")),
    )
```

- [ ] **Step 7: Run import/template tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_candidate_import_service.py app/tests/test_template_service.py -v
```

Expected: all tests pass after updating older candidate import fixtures to include `"login_code": "invite-..."`.

- [ ] **Step 8: Commit**

```bash
git add backend/alembic/versions/202606220001_add_candidate_login_code.py backend/app/models/candidate.py backend/app/schemas/candidate.py backend/app/services/import_service.py backend/app/services/template_service.py backend/app/tests/test_candidate_import_service.py backend/app/tests/test_template_service.py
git commit -m "fix: 为考生导入增加登录码"
```

## Task 2: Require Login Code For Candidate Session Issuance

**Files:**
- Modify: `backend/app/services/candidate_service.py`
- Modify: `backend/app/tests/test_candidate_flow_api.py`

- [ ] **Step 1: Update successful login tests to include login code**

In `backend/app/tests/test_candidate_flow_api.py`, update existing candidate rows and login payloads:

```python
Candidate(
    name="张三",
    employee_no="YG0001",
    login_code="code-0001",
    department="综合管理部",
    status="active",
)
```

```python
response = client.post(
    "/api/candidates/login",
    json={"name": "张三", "employee_no": "YG0001", "login_code": "code-0001"},
)
```

For name-only login:

```python
Candidate(
    name="王五",
    employee_no=None,
    login_code="name-code-0001",
    department="安全管理部",
    status="active",
)
```

```python
response = client.post(
    "/api/candidates/login",
    json={"name": "王五", "login_code": "name-code-0001"},
)
```

- [ ] **Step 2: Add failing negative tests**

Append:

```python
def test_candidate_login_rejects_missing_login_code() -> None:
    client, db = _build_client()
    db.add(
        Candidate(
            name="赵六",
            employee_no="YG0006",
            login_code="secret-0006",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={"name": "赵六", "employee_no": "YG0006"},
    )

    assert response.status_code == 422


def test_candidate_login_rejects_wrong_login_code() -> None:
    client, db = _build_client()
    db.add(
        Candidate(
            name="赵六",
            employee_no="YG0006",
            login_code="secret-0006",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={
            "name": "赵六",
            "employee_no": "YG0006",
            "login_code": "wrong-code",
        },
    )

    assert response.status_code == 404


def test_candidate_login_binds_name_when_employee_no_is_present() -> None:
    client, db = _build_client()
    db.add(
        Candidate(
            name="真实姓名",
            employee_no="YG0007",
            login_code="secret-0007",
            status="active",
        )
    )
    db.commit()

    response = client.post(
        "/api/candidates/login",
        json={
            "name": "错误姓名",
            "employee_no": "YG0007",
            "login_code": "secret-0007",
        },
    )

    assert response.status_code == 404
```

- [ ] **Step 3: Run tests to verify failures**

Run:

```bash
cd backend
uv run pytest app/tests/test_candidate_flow_api.py::test_candidate_login_returns_persisted_candidate_by_employee_no app/tests/test_candidate_flow_api.py::test_candidate_login_returns_persisted_candidate_by_name_without_employee_no app/tests/test_candidate_flow_api.py::test_candidate_login_rejects_missing_login_code app/tests/test_candidate_flow_api.py::test_candidate_login_rejects_wrong_login_code app/tests/test_candidate_flow_api.py::test_candidate_login_binds_name_when_employee_no_is_present -v
```

Expected: negative tests fail until `candidate_service.login_candidate` checks the code and name binding.

- [ ] **Step 4: Implement login-code verification**

Replace `backend/app/services/candidate_service.py` login logic with:

```python
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.security import constant_time_equals, create_candidate_token
from app.models import Candidate
from app.schemas.candidate import (
    CandidateLoginRequest,
    CandidateLoginResponse,
    CandidateRead,
)


class CandidateLoginError(DomainError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("未找到匹配的考试人员")


class CandidateLoginAmbiguousError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("姓名匹配到多名考试人员，请填写员工号")


def _with_token(candidate: Candidate) -> CandidateLoginResponse:
    candidate_read = CandidateRead.model_validate(candidate)
    return CandidateLoginResponse(
        **candidate_read.model_dump(),
        token=create_candidate_token(candidate.id),
    )


def _login_code_matches(candidate: Candidate, login_code: str) -> bool:
    if not candidate.login_code:
        return False
    return constant_time_equals(candidate.login_code, login_code)


def login_candidate(
    db: Session, payload: CandidateLoginRequest
) -> CandidateLoginResponse:
    if payload.employee_no:
        candidate = (
            db.query(Candidate)
            .filter(
                Candidate.employee_no == payload.employee_no,
                Candidate.name == payload.name,
                Candidate.status == "active",
            )
            .one_or_none()
        )
        if candidate is None or not _login_code_matches(candidate, payload.login_code):
            raise CandidateLoginError()
        return _with_token(candidate)

    candidates = (
        db.query(Candidate)
        .filter(Candidate.name == payload.name, Candidate.status == "active")
        .order_by(Candidate.id)
        .all()
    )
    matches = [
        candidate
        for candidate in candidates
        if _login_code_matches(candidate, payload.login_code)
    ]
    if not matches:
        raise CandidateLoginError()
    if len(matches) > 1:
        raise CandidateLoginAmbiguousError()
    return _with_token(matches[0])
```

- [ ] **Step 5: Run candidate flow tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_candidate_flow_api.py -v
```

Expected: all candidate flow tests pass after adding `login_code` to all candidate fixtures that call login.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/candidate_service.py backend/app/tests/test_candidate_flow_api.py
git commit -m "fix: 使用登录码签发考生令牌"
```

## Task 3: Add Candidate Login Code Field To Frontend

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/pages/LoginPage.tsx`
- Test: `frontend/src/pages/P0Pages.test.tsx`

- [ ] **Step 1: Update frontend API type**

Modify `frontend/src/api/auth.ts`:

```ts
export function loginCandidate(payload: {
  name: string;
  login_code: string;
  employee_no?: string;
}) {
  return apiRequest<Candidate>("/api/candidates/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 2: Update LoginPage form schema and field**

Modify the schema in `frontend/src/pages/LoginPage.tsx`:

```ts
const schema = z.object({
  name: z.string().min(1, "请输入姓名"),
  login_code: z.string().min(1, "请输入登录码"),
  employee_no: z.string().optional(),
});
```

Update defaults:

```ts
defaultValues: { name: "", login_code: "", employee_no: "" },
```

Update the help copy:

```tsx
<p className="max-w-xl text-body-lg text-muted">
  填写姓名和登录码即可进入练习或考试。如有员工号会优先用于识别，登录码由管理员随应考名单发放。
</p>
```

Insert this `Field` between name and employee number:

```tsx
<Field data-invalid={form.formState.errors.login_code ? "" : undefined}>
  <FieldLabel htmlFor="login_code">
    登录码 · <span className="text-muted">Login Code</span>
  </FieldLabel>
  <Input
    id="login_code"
    type="password"
    autoComplete="one-time-code"
    aria-invalid={Boolean(form.formState.errors.login_code)}
    {...form.register("login_code")}
  />
  {form.formState.errors.login_code ? (
    <FieldError>{form.formState.errors.login_code.message}</FieldError>
  ) : null}
</Field>
```

- [ ] **Step 3: Add frontend test for login payload**

In `frontend/src/pages/P0Pages.test.tsx`, add or update the login-page test so it fills login code and asserts the API call:

```tsx
it("submits candidate login with login code", async () => {
  const user = userEvent.setup();
  vi.mocked(loginCandidate).mockResolvedValue({
    id: 1,
    name: "张三",
    employee_no: "YG0001",
    token: "candidate-token",
    should_attend: true,
    status: "active",
  });

  renderPage("login", <LoginPage />, { initialEntries: ["/login"] });

  await user.type(screen.getByLabelText(/姓名/), "张三");
  await user.type(screen.getByLabelText(/登录码/), "invite-0001");
  await user.type(screen.getByLabelText(/员工号/), "YG0001");
  await user.click(screen.getByRole("button", { name: /进入系统/ }));

  await waitFor(() => {
    expect(loginCandidate).toHaveBeenCalledWith({
      name: "张三",
      login_code: "invite-0001",
      employee_no: "YG0001",
    });
  });
});
```

- [ ] **Step 4: Run frontend test**

Run:

```bash
cd frontend
npm run test -- P0Pages.test.tsx --runInBand
```

Expected: login payload test passes. If the project uses Vitest without `--runInBand`, run `npm run test -- P0Pages.test.tsx` and keep the passing output in the implementation notes.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/auth.ts frontend/src/pages/LoginPage.tsx frontend/src/pages/P0Pages.test.tsx
git commit -m "fix: 前端登录提交考生登录码"
```

## Task 4: Block Attempt Result Reads Before Submission

**Files:**
- Modify: `backend/app/services/exam_service.py`
- Test: `backend/app/tests/test_exam_service.py`
- Test: `backend/app/tests/test_candidate_attempt_api.py`

- [ ] **Step 1: Add failing service test**

Append to `backend/app/tests/test_exam_service.py`:

```python
def test_get_attempt_result_rejects_in_progress_attempt(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    add_exam_candidate_scope(db, exam.id, candidate.id)
    create_question_with_options(db)

    start = exam_service.start_exam(db, exam.id, candidate.id)

    with pytest.raises(exam_service.AttemptResultNotReadyError):
        exam_service.get_attempt_result(db, start.attempt_id)
```

- [ ] **Step 2: Add failing API test**

Append to `backend/app/tests/test_candidate_attempt_api.py`:

```python
def test_result_rejects_in_progress_attempt() -> None:
    client, db = _build_client()
    exam = Exam(title="安全考试", duration_minutes=60, status="active")
    candidate = Candidate(name="张三", employee_no="YG0001", login_code="code-1")
    question = Question(question_type="single", stem="题目", score=2, status="active")
    db.add_all([exam, candidate, question])
    db.flush()
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.add_all(
        [
            QuestionOption(
                question_id=question.id,
                label="A",
                content="正确",
                is_correct=True,
                sort_order=0,
            ),
            QuestionOption(
                question_id=question.id,
                label="B",
                content="错误",
                is_correct=False,
                sort_order=1,
            ),
        ]
    )
    db.commit()
    start = exam_service.start_exam(db, exam.id, candidate.id)

    resp = client.get(
        f"/api/attempts/{start.attempt_id}/result",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert resp.status_code == 409
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd backend
uv run pytest app/tests/test_exam_service.py::test_get_attempt_result_rejects_in_progress_attempt app/tests/test_candidate_attempt_api.py::test_result_rejects_in_progress_attempt -v
```

Expected: service test fails because `AttemptResultNotReadyError` does not exist or result is returned.

- [ ] **Step 4: Implement submitted-state gate**

Add this exception near existing attempt exceptions in `backend/app/services/exam_service.py`:

```python
class AttemptResultNotReadyError(DomainError):
    status_code = 409

    def __init__(self, attempt_id: int) -> None:
        super().__init__(f"考试记录 #{attempt_id} 尚未提交，不能查看结果")
```

Replace `get_attempt_result`:

```python
def get_attempt_result(db: Session, attempt_id: int) -> AttemptResultRead:
    attempt = _load_attempt_with_snapshots(db, attempt_id)
    if attempt.status not in SUBMITTED_STATUSES:
        raise AttemptResultNotReadyError(attempt_id)
    return _build_attempt_result(attempt)
```

- [ ] **Step 5: Run attempt/result tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_exam_service.py::test_get_attempt_result_rejects_in_progress_attempt app/tests/test_exam_service.py::test_get_attempt_result_reads_submitted_result_without_mutating_submit_type app/tests/test_candidate_attempt_api.py::test_result_requires_candidate_header app/tests/test_candidate_attempt_api.py::test_result_rejects_in_progress_attempt -v
```

Expected: all listed tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/exam_service.py backend/app/tests/test_exam_service.py backend/app/tests/test_candidate_attempt_api.py
git commit -m "fix: 禁止未提交考试查看结果"
```

## Task 5: Authenticate Practice Listing And Remove Formal Exam Questions From Practice Answers

**Files:**
- Modify: `backend/app/api/practice.py`
- Modify: `backend/app/services/practice_service.py`
- Modify: `backend/app/tests/test_candidate_flow_api.py`

- [ ] **Step 1: Add failing API tests**

Update `test_practice_questions_hide_answers_and_analysis` to include a token:

```python
candidate = Candidate(name="张三", employee_no="YG0001", login_code="code-1")
db.add(candidate)
db.commit()

response = client.get(
    "/api/practice/questions",
    headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
)
```

Append:

```python
def test_practice_questions_requires_candidate_token() -> None:
    client, _db = _build_client()

    response = client.get("/api/practice/questions")

    assert response.status_code == 401


def test_practice_questions_excludes_active_exam_pool_questions() -> None:
    client, db = _build_client()
    candidate = Candidate(name="张三", employee_no="YG0001", login_code="code-1")
    exam = Exam(title="正式考试", duration_minutes=60, status="active")
    formal_question = Question(
        question_type="single", stem="正式题", score=2, status="active"
    )
    practice_question = Question(
        question_type="single", stem="练习题", score=2, status="active"
    )
    db.add_all([candidate, exam, formal_question, practice_question])
    db.flush()
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.add(ExamQuestionPool(exam_id=exam.id, question_id=formal_question.id, sort_order=0))
    db.commit()

    response = client.get(
        "/api/practice/questions",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
    )

    assert response.status_code == 200
    stems = [row["stem"] for row in response.json()["data"]]
    assert stems == ["练习题"]


def test_practice_answer_rejects_active_exam_pool_question() -> None:
    client, db = _build_client()
    candidate = Candidate(name="张三", employee_no="YG0001", login_code="code-1")
    exam = Exam(title="正式考试", duration_minutes=60, status="active")
    question = Question(
        question_type="single", stem="正式题", analysis="解析", score=2, status="active"
    )
    db.add_all([candidate, exam, question])
    db.flush()
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.add(ExamQuestionPool(exam_id=exam.id, question_id=question.id, sort_order=0))
    db.add_all(
        [
            QuestionOption(
                question_id=question.id,
                label="A",
                content="正确",
                is_correct=True,
                sort_order=0,
            ),
            QuestionOption(
                question_id=question.id,
                label="B",
                content="错误",
                is_correct=False,
                sort_order=1,
            ),
        ]
    )
    db.commit()

    response = client.post(
        "/api/practice/answers",
        headers={"X-Candidate-Token": create_candidate_token(candidate.id)},
        json={"question_id": question.id, "selected_answer": "A"},
    )

    assert response.status_code == 409
```

Add imports at the top of `test_candidate_flow_api.py`:

```python
from app.models import Candidate, Exam, ExamCandidateScope, ExamQuestionPool, Question, QuestionOption
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```bash
cd backend
uv run pytest app/tests/test_candidate_flow_api.py::test_practice_questions_requires_candidate_token app/tests/test_candidate_flow_api.py::test_practice_questions_excludes_active_exam_pool_questions app/tests/test_candidate_flow_api.py::test_practice_answer_rejects_active_exam_pool_question -v
```

Expected: tests fail because the list endpoint is anonymous and formal-pool questions are returned/answered.

- [ ] **Step 3: Implement practice-safe listing and answer rejection**

Modify `backend/app/services/practice_service.py`:

```python
from datetime import UTC, datetime

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.models import Candidate, Exam, ExamQuestionPool, PracticeAnswer, Question
from app.schemas.practice import PracticeAnswerResult, PracticeAnswerSubmitRequest
from app.schemas.question import PracticeQuestionRead
from app.services.scoring_service import score_answer


class PracticeCandidateNotFoundError(DomainError):
    status_code = 404

    def __init__(self, candidate_id: int) -> None:
        super().__init__(f"考生 #{candidate_id} 不存在")


class PracticeQuestionNotFoundError(DomainError):
    status_code = 404

    def __init__(self, question_id: int) -> None:
        super().__init__(f"练习题目 #{question_id} 不存在")


class PracticeQuestionLockedError(DomainError):
    status_code = 409

    def __init__(self, question_id: int) -> None:
        super().__init__(f"题目 #{question_id} 正在用于正式考试，不能作为练习题")


def _active_exam_question_ids(db: Session) -> set[int]:
    rows = (
        db.query(ExamQuestionPool.question_id)
        .join(Exam, Exam.id == ExamQuestionPool.exam_id)
        .filter(Exam.status == "active")
        .all()
    )
    return {row[0] for row in rows}


def list_practice_questions(db: Session) -> list[PracticeQuestionRead]:
    locked_question_ids = _active_exam_question_ids(db)
    questions = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.status == "active")
        .order_by(Question.id)
        .all()
    )
    return [
        PracticeQuestionRead.model_validate(question)
        for question in questions
        if question.id not in locked_question_ids
    ]


def submit_practice_answer(
    db: Session, candidate_id: int, payload: PracticeAnswerSubmitRequest
) -> PracticeAnswerResult:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None or candidate.status != "active":
        raise PracticeCandidateNotFoundError(candidate_id)

    if payload.question_id in _active_exam_question_ids(db):
        raise PracticeQuestionLockedError(payload.question_id)

    question = (
        db.query(Question)
        .options(selectinload(Question.options))
        .filter(Question.id == payload.question_id, Question.status == "active")
        .one_or_none()
    )
    if question is None:
        raise PracticeQuestionNotFoundError(payload.question_id)

    correct_answer = _build_correct_answer(question)
    scoring = score_answer(
        question.question_type,
        correct_answer,
        payload.selected_answer,
        float(question.score),
    )
    db.add(
        PracticeAnswer(
            candidate_id=candidate.id,
            question_id=question.id,
            selected_answer=payload.selected_answer,
            is_correct=scoring.is_correct,
            practiced_at=datetime.now(UTC),
        )
    )
    db.commit()

    return PracticeAnswerResult(
        question_id=question.id,
        selected_answer=payload.selected_answer,
        correct_answer=correct_answer,
        is_correct=scoring.is_correct,
        score_awarded=scoring.score_awarded,
        score=float(question.score),
        analysis=question.analysis,
    )


def _build_correct_answer(question: Question) -> str:
    labels = sorted(option.label for option in question.options if option.is_correct)
    return ",".join(labels)
```

Modify `backend/app/api/practice.py`:

```python
@router.get("/questions", response_model=ApiResponse[list[PracticeQuestionRead]])
def list_practice_questions(
    db: Session = Depends(get_db),
    _candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[list[PracticeQuestionRead]]:
    return ApiResponse(data=practice_service.list_practice_questions(db))
```

- [ ] **Step 4: Run practice tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_candidate_flow_api.py -v
```

Expected: all candidate practice tests pass after adding `login_code` to test candidates.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/practice.py backend/app/services/practice_service.py backend/app/tests/test_candidate_flow_api.py
git commit -m "fix: 收紧练习题库与答案披露"
```

## Task 6: Add In-Memory Rate Limiting To Public Token Issuance

**Files:**
- Create: `backend/app/core/rate_limit.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/api/candidates.py`
- Test: `backend/app/tests/test_rate_limit.py`

- [ ] **Step 1: Write failing rate-limit tests**

Create `backend/app/tests/test_rate_limit.py`:

```python
import pytest

from app.core.rate_limit import LoginRateLimiter, RateLimitExceededError


def test_login_rate_limiter_blocks_after_limit() -> None:
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60)

    limiter.check("admin:127.0.0.1")
    limiter.check("admin:127.0.0.1")

    with pytest.raises(RateLimitExceededError):
        limiter.check("admin:127.0.0.1")


def test_login_rate_limiter_can_reset_identifier() -> None:
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    limiter.check("candidate:YG0001")

    limiter.reset("candidate:YG0001")
    limiter.check("candidate:YG0001")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
uv run pytest app/tests/test_rate_limit.py -v
```

Expected: import fails because `app.core.rate_limit` does not exist.

- [ ] **Step 3: Implement limiter**

Create `backend/app/core/rate_limit.py`:

```python
from collections import defaultdict, deque
from time import monotonic

from app.core.exceptions import DomainError


class RateLimitExceededError(DomainError):
    status_code = 429

    def __init__(self) -> None:
        super().__init__("尝试次数过多，请稍后再试")


class LoginRateLimiter:
    def __init__(self, *, max_attempts: int = 10, window_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = monotonic()
        attempts = self._attempts[key]
        while attempts and now - attempts[0] >= self.window_seconds:
            attempts.popleft()
        if len(attempts) >= self.max_attempts:
            raise RateLimitExceededError()
        attempts.append(now)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


login_rate_limiter = LoginRateLimiter()
```

- [ ] **Step 4: Apply limiter to public login routes**

Modify `backend/app/api/auth.py`:

```python
from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.rate_limit import login_rate_limiter
from app.core.security import constant_time_equals, create_session_token
from app.schemas.auth import AdminLoginRequest, LoginResponse
from app.schemas.common import ApiResponse
from app.services.exam_service import AdminAuthError

router = APIRouter(tags=["auth"])


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/admin/login", response_model=ApiResponse[LoginResponse])
def admin_login(
    payload: AdminLoginRequest, request: Request
) -> ApiResponse[LoginResponse]:
    key = f"admin:{_client_host(request)}:{payload.username}"
    login_rate_limiter.check(key)
    username_ok = constant_time_equals(payload.username, settings.admin_username)
    password_ok = constant_time_equals(payload.password, settings.admin_password)
    if not username_ok or not password_ok:
        raise AdminAuthError()
    login_rate_limiter.reset(key)
    return ApiResponse(data=LoginResponse(token=create_session_token(payload.username)))
```

Modify `backend/app/api/candidates.py`:

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import login_rate_limiter
from app.schemas.candidate import CandidateLoginRequest, CandidateLoginResponse
from app.schemas.common import ApiResponse
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=ApiResponse[CandidateLoginResponse])
def candidate_login(
    payload: CandidateLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[CandidateLoginResponse]:
    identifier = payload.employee_no or payload.name
    key = f"candidate:{_client_host(request)}:{identifier}"
    login_rate_limiter.check(key)
    result = candidate_service.login_candidate(db, payload)
    login_rate_limiter.reset(key)
    return ApiResponse(data=result)
```

- [ ] **Step 5: Run limiter tests and targeted auth tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_rate_limit.py app/tests/test_admin_auth_api.py::test_admin_login_rejects_wrong_password app/tests/test_candidate_flow_api.py::test_candidate_login_rejects_wrong_login_code -v
```

Expected: all listed tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/rate_limit.py backend/app/api/auth.py backend/app/api/candidates.py backend/app/tests/test_rate_limit.py
git commit -m "fix: 为登录接口增加限流"
```

## Task 7: Reject Published Sample Secrets In Production

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/tests/test_admin_auth_api.py`
- Modify: `docs/official-exam-uat-checklist.md`

- [ ] **Step 1: Write failing config test**

Append to `backend/app/tests/test_admin_auth_api.py`:

```python
def test_production_rejects_documented_local_dev_secrets() -> None:
    with pytest.raises(ValidationError, match="ADMIN_PASSWORD"):
        Settings(
            environment="production",
            admin_password="local-dev-admin-password",  # noqa: S106
            token_secret="prod-token-secret",  # noqa: S106
            cors_origins="https://exam.example.com",
        )

    with pytest.raises(ValidationError, match="TOKEN_SECRET"):
        Settings(
            environment="production",
            admin_password="strong-password",  # noqa: S106
            token_secret="local-dev-token-secret-change-before-production",  # noqa: S106
            cors_origins="https://exam.example.com",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
uv run pytest app/tests/test_admin_auth_api.py::test_production_rejects_documented_local_dev_secrets -v
```

Expected: fails because the documented local-dev values are accepted.

- [ ] **Step 3: Implement production denylist**

Modify `backend/app/core/config.py`:

```python
PRODUCTION_ADMIN_PASSWORD_DENYLIST = {
    "change-me",
    "local-dev-admin-password",
}
PRODUCTION_TOKEN_SECRET_DENYLIST = {
    "change-me-in-production",
    "local-dev-token-secret-change-before-production",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "internal-exam-platform"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://exam:exam@db:5432/internal_exam"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    admin_username: str = "admin"
    admin_password: str = "change-me"
    token_secret: str = Field(default="change-me-in-production", min_length=8)
    token_ttl_seconds: int = 12 * 60 * 60
    import_max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    import_max_rows: int = Field(default=5000, ge=1)
    import_max_sheets: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def reject_production_defaults(self) -> "Settings":
        if self.environment == "production":
            if self.admin_password in PRODUCTION_ADMIN_PASSWORD_DENYLIST:
                raise ValueError("production 环境必须配置 ADMIN_PASSWORD")
            if self.token_secret in PRODUCTION_TOKEN_SECRET_DENYLIST:
                raise ValueError("production 环境必须配置 TOKEN_SECRET")
            origins = self.cors_origin_list
            if not origins:
                raise ValueError("production 环境必须配置安全的 CORS_ORIGINS")
            for origin in origins:
                parsed = urlparse(origin)
                if (
                    origin == "*"
                    or parsed.scheme != "https"
                    or parsed.hostname in {"localhost", "127.0.0.1", "0.0.0.0"}  # noqa: S104
                ):
                    raise ValueError("production 环境必须配置安全的 CORS_ORIGINS")
        return self
```

- [ ] **Step 4: Update UAT checklist wording**

Modify `docs/official-exam-uat-checklist.md` production checklist:

```markdown
- `ADMIN_PASSWORD` 不是 `change-me` 或 `local-dev-admin-password`。
- `TOKEN_SECRET` 不是 `change-me-in-production` 或 `local-dev-token-secret-change-before-production`。
```

- [ ] **Step 5: Run config tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_admin_auth_api.py::test_production_rejects_default_admin_password_and_token_secret app/tests/test_admin_auth_api.py::test_production_rejects_documented_local_dev_secrets app/tests/test_admin_auth_api.py::test_production_rejects_dangerous_cors_origins app/tests/test_admin_auth_api.py::test_production_accepts_explicit_https_cors_origins -v
```

Expected: all listed tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/tests/test_admin_auth_api.py docs/official-exam-uat-checklist.md
git commit -m "fix: 生产环境拒绝示例密钥"
```

## Task 8: Remove Default Host Exposure From Docker Compose

**Files:**
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Modify: `docs/handoff.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Edit Compose port mappings**

Modify `docker-compose.yml` so only Nginx publishes a host port:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: internal_exam
      POSTGRES_USER: exam
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U exam -d internal_exam"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ./backend
    environment:
      ENVIRONMENT: ${ENVIRONMENT:-development}
      DATABASE_URL: ${DATABASE_URL:?Set DATABASE_URL in .env}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:8080}
      ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:?Set ADMIN_PASSWORD in .env}
      TOKEN_SECRET: ${TOKEN_SECRET:?Set TOKEN_SECRET in .env}
    depends_on:
      db:
        condition: service_healthy
    command: ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]

  frontend:
    build:
      context: ./frontend
    depends_on:
      - backend

  nginx:
    image: nginx:1.27-alpine
    depends_on:
      - frontend
      - backend
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro

volumes:
  postgres_data:
```

- [ ] **Step 2: Update README Docker health check**

Change Docker health check docs to:

```markdown
Docker 默认只暴露 Nginx 入口：

```bash
curl http://localhost:8080/api/health
```

如果需要直接调试后端，请使用 `cd backend && uv run uvicorn app.main:app --reload` 启动本地后端，或创建本地-only compose override，不要在生产 compose 中暴露 PostgreSQL 或 backend host port。
```
```

- [ ] **Step 3: Update handoff and CLAUDE notes**

In `docs/handoff.md`, add:

```markdown
- Docker Compose 默认只发布 Nginx `8080:80`。PostgreSQL、backend、frontend 只在 Compose 网络内互通；本地直连调试使用单独进程或本地 override。
```

In `CLAUDE.md`, update any Docker health check that uses `localhost:8000` for Compose to `localhost:8080/api/health`. Keep direct backend development commands under the backend section.

- [ ] **Step 4: Validate compose**

Run:

```bash
docker-compose config
```

Expected: command exits 0, and rendered config contains only one `published: "8080"` port under `nginx`.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml README.md docs/handoff.md CLAUDE.md
git commit -m "fix: 默认 compose 仅暴露 nginx"
```

## Task 9: Harden Excel Formula Escaping

**Files:**
- Modify: `backend/app/services/excel_security.py`
- Modify: `backend/app/tests/test_report_service.py`
- Modify: `backend/app/tests/test_question_import_service.py`

- [ ] **Step 1: Add failing escape tests**

Append to `backend/app/tests/test_report_service.py`:

```python
def test_report_workbook_escapes_control_prefixed_formula_text(db: Session) -> None:
    from openpyxl import load_workbook

    exam = create_exam(db, title="\t=cmd")
    candidate = create_candidate(db, name="\r=HYPERLINK(\"http://example.test\")")
    db.add(ExamCandidateScope(exam_id=exam.id, candidate_id=candidate.id))
    db.commit()
    create_question_with_options(db, stem="\n+SUM(1,1)")
    start = exam_service.start_exam(db, exam.id, candidate.id)
    submit_answers(db, start.attempt_id, start.questions, ["B"])

    workbook_stream = report_service.generate_report_workbook(db, exam_id=exam.id)
    workbook = load_workbook(workbook_stream, data_only=False)

    assert workbook["成绩报表"].cell(2, 1).value.startswith("'\r=")
    assert workbook["成绩报表"].cell(2, 4).value == "'\t=cmd"
    assert workbook["题目正确率"].cell(2, 2).value == "'\n+SUM(1,1)"
```

Append to `backend/app/tests/test_question_import_service.py`:

```python
def test_failure_report_escapes_control_prefixed_formula_file_name(db: Session) -> None:
    from openpyxl import load_workbook

    db.add(
        ImportBatch(
            import_type="questions",
            file_name="\t=HYPERLINK(\"http://example.test\")",
            total_count=1,
            success_count=0,
            failed_count=1,
            status="completed",
            error_report=[{"row_number": 2, "reason": "\r=cmd"}],
        )
    )
    db.commit()
    batch = db.scalars(select(ImportBatch)).one()

    workbook = load_workbook(generate_failure_report(db, batch.id), data_only=False)

    assert workbook["导入批次"].cell(3, 2).value.startswith("'\t=")
    assert workbook["失败明细"].cell(2, 2).value.startswith("'\r=")
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```bash
cd backend
uv run pytest app/tests/test_report_service.py::test_report_workbook_escapes_control_prefixed_formula_text app/tests/test_question_import_service.py::test_failure_report_escapes_control_prefixed_formula_file_name -v
```

Expected: fails because values beginning with tab, CR, or LF are not escaped.

- [ ] **Step 3: Implement normalized formula check**

Replace `backend/app/services/excel_security.py`:

```python
FORMULA_PREFIXES = ("=", "+", "-", "@")
IGNORED_FORMULA_PREFIX_CHARS = frozenset("\t\r\n ")


def _starts_with_formula_prefix(value: str) -> bool:
    stripped = value.lstrip("".join(IGNORED_FORMULA_PREFIX_CHARS))
    return stripped.startswith(FORMULA_PREFIXES)


def escape_excel_cell(value: object) -> object:
    if isinstance(value, str) and _starts_with_formula_prefix(value):
        return f"'{value}"
    return value
```

- [ ] **Step 4: Run Excel export tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_report_service.py::test_report_workbook_escapes_formula_like_text app/tests/test_report_service.py::test_report_workbook_escapes_control_prefixed_formula_text app/tests/test_question_import_service.py::test_failure_report_escapes_formula_like_file_name app/tests/test_question_import_service.py::test_failure_report_escapes_control_prefixed_formula_file_name -v
```

Expected: all listed tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/excel_security.py backend/app/tests/test_report_service.py backend/app/tests/test_question_import_service.py
git commit -m "fix: 加固 Excel 公式转义"
```

## Task 10: Add Pre-Parse XLSX Archive Limits

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/import_service.py`
- Modify: `backend/app/tests/test_question_import_service.py`
- Modify: `docs/official-exam-uat-checklist.md`

- [ ] **Step 1: Add failing archive-limit tests**

Append to `backend/app/tests/test_question_import_service.py`:

```python
from zipfile import ZIP_DEFLATED, ZipFile
```

Append:

```python
def test_parse_workbook_rejects_zip_with_too_many_entries() -> None:
    file_obj = BytesIO()
    with ZipFile(file_obj, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "")
        archive.writestr("xl/workbook.xml", "")
        archive.writestr("xl/worksheets/sheet1.xml", "")
    file_obj.seek(0)

    with pytest.raises(import_service.ImportLimitError, match="压缩包条目数量"):
        import_service.validate_xlsx_archive_limits(
            file_obj,
            max_entries=3,
            max_uncompressed_bytes=1024 * 1024,
        )

    assert file_obj.tell() == 0


def test_parse_workbook_rejects_zip_with_too_much_uncompressed_data() -> None:
    file_obj = BytesIO()
    with ZipFile(file_obj, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "A" * 2048)
    file_obj.seek(0)

    with pytest.raises(import_service.ImportLimitError, match="解压后大小"):
        import_service.validate_xlsx_archive_limits(
            file_obj,
            max_entries=10,
            max_uncompressed_bytes=1024,
        )

    assert file_obj.tell() == 0
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```bash
cd backend
uv run pytest app/tests/test_question_import_service.py::test_parse_workbook_rejects_zip_with_too_many_entries app/tests/test_question_import_service.py::test_parse_workbook_rejects_zip_with_too_much_uncompressed_data -v
```

Expected: fails because `validate_xlsx_archive_limits` does not exist.

- [ ] **Step 3: Add config settings**

Modify `backend/app/core/config.py`:

```python
import_max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
import_max_rows: int = Field(default=5000, ge=1)
import_max_sheets: int = Field(default=1, ge=1)
import_max_zip_entries: int = Field(default=1000, ge=1)
import_max_uncompressed_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
```

- [ ] **Step 4: Implement archive validation before openpyxl**

Modify `backend/app/services/import_service.py` imports:

```python
from zipfile import BadZipFile, ZipFile
```

Add function after `validate_upload_file_size`:

```python
def validate_xlsx_archive_limits(
    file_obj: Any,
    *,
    max_entries: int | None = None,
    max_uncompressed_bytes: int | None = None,
) -> None:
    entry_limit = max_entries or settings.import_max_zip_entries
    uncompressed_limit = (
        max_uncompressed_bytes or settings.import_max_uncompressed_bytes
    )
    try:
        file_obj.seek(0)
        with ZipFile(file_obj) as archive:
            entries = archive.infolist()
            if len(entries) > entry_limit:
                raise ImportLimitError(
                    f"导入文件压缩包条目数量不能超过 {entry_limit} 个"
                )
            total_size = sum(info.file_size for info in entries)
            if total_size > uncompressed_limit:
                raise ImportLimitError(
                    f"导入文件解压后大小不能超过 {uncompressed_limit} 字节"
                )
    except BadZipFile as exc:
        raise ImportLimitError("导入文件必须是有效的 xlsx 文件") from exc
    finally:
        with suppress(AttributeError, OSError):
            file_obj.seek(0)
```

Modify `parse_workbook`:

```python
def parse_workbook(
    file_obj: Any, *, max_rows: int | None = None, max_sheets: int | None = None
) -> ParsedWorkbook:
    row_limit = max_rows or settings.import_max_rows
    sheet_limit = max_sheets or settings.import_max_sheets
    validate_xlsx_archive_limits(file_obj)
    with suppress(AttributeError, OSError):
        file_obj.seek(0)
    workbook = load_workbook(file_obj, read_only=True, data_only=True)
    try:
        if len(workbook.worksheets) > sheet_limit:
            raise ImportLimitError(f"导入文件不能超过 {sheet_limit} 个工作表")
        sheet = workbook.active
        it = sheet.iter_rows(values_only=True)
        headers_row = next(it, None)
        if headers_row is None:
            return ParsedWorkbook(rows=[], total_count=0)
        headers = [
            str(cell).strip() if cell is not None else "" for cell in headers_row
        ]
        parsed_rows = []
        for row_number, row in enumerate(it, start=1):
            if row_number > row_limit:
                raise ImportLimitError(f"导入数据行数不能超过 {row_limit} 行")
            parsed_rows.append(
                {headers[i]: v for i, v in enumerate(row) if i < len(headers)}
            )
        return ParsedWorkbook(rows=parsed_rows, total_count=len(parsed_rows))
    finally:
        workbook.close()
```

- [ ] **Step 5: Update UAT checklist import budget**

Modify `docs/official-exam-uat-checklist.md`:

```markdown
- 如需调整导入预算，显式配置 `IMPORT_MAX_UPLOAD_BYTES`、`IMPORT_MAX_ROWS`、`IMPORT_MAX_SHEETS`、`IMPORT_MAX_ZIP_ENTRIES`、`IMPORT_MAX_UNCOMPRESSED_BYTES`；默认是 5 MiB、5000 行、1 个工作表、1000 个 ZIP 条目、20 MiB 解压后大小。
```

- [ ] **Step 6: Run import tests**

Run:

```bash
cd backend
uv run pytest app/tests/test_question_import_service.py app/tests/test_candidate_import_service.py -v
```

Expected: all import tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/config.py backend/app/services/import_service.py backend/app/tests/test_question_import_service.py docs/official-exam-uat-checklist.md
git commit -m "fix: 限制 xlsx 解压预算"
```

## Task 11: Final Verification And Documentation Pass

**Files:**
- Modify: `README.md`
- Modify: `docs/handoff.md`
- Modify: `docs/api-design.md`
- Modify: `docs/import-templates.md`

- [ ] **Step 1: Update API docs**

In `docs/api-design.md`, update candidate login and practice notes:

```markdown
- `/api/candidates/login` 需要 `name`、`login_code`，可选 `employee_no`；当传入员工号时必须同时匹配姓名和登录码。
- `/api/practice/questions` 需要 `X-Candidate-Token`，并排除正在用于 active 正式考试题池的题目。
- `/api/practice/answers` 需要 `X-Candidate-Token`；如果题目正在用于 active 正式考试题池，返回 409，不返回正确答案或解析。
- `/api/attempts/{attempt_id}/result` 仅允许 `submitted` 或 `auto_submitted` attempt 查看结果。
```

- [ ] **Step 2: Update import template docs**

In `docs/import-templates.md`, add `login_code` to candidate template fields:

```markdown
| login_code | 是 | 考生登录码，由管理员通过安全渠道发放；不在登录响应、报表或候选人读取接口中返回。 |
```

- [ ] **Step 3: Update README and handoff security notes**

Add to `README.md` hardening notes:

```markdown
- 考生登录需要姓名和登录码；员工号仅用于消歧，不能单独签发考生 token。
- Docker Compose 默认只暴露 Nginx `8080`，数据库和后端服务不发布宿主机端口。
- Excel 导入在 `openpyxl` 解析前检查压缩包条目数和解压后大小。
```

Add to `docs/handoff.md`:

```markdown
- Security remediation after the deep scan: candidate login code, submitted-only result reads, candidate-authenticated practice listing, active exam pool exclusion from practice answers, login throttling, production sample-secret rejection, default Compose internal service isolation, stronger Excel formula escaping, and XLSX archive budget checks.
```

- [ ] **Step 4: Run backend full tests**

Run:

```bash
cd backend
uv run pytest
```

Expected: all backend tests pass.

- [ ] **Step 5: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 6: Run compose config**

Run:

```bash
docker-compose config
```

Expected: config renders successfully and only Nginx publishes a host port by default.

- [ ] **Step 7: Run Alembic upgrade**

Run:

```bash
cd backend
uv run alembic upgrade head
```

Expected: migration applies successfully.

- [ ] **Step 8: Commit docs and verification fixes**

```bash
git add README.md docs/handoff.md docs/api-design.md docs/import-templates.md
git commit -m "docs: 更新安全加固说明"
```

## Self-Review

- Spec coverage: all 8 reportable findings are covered. Candidate token impersonation is covered by Tasks 1-3. Pre-submit result disclosure is covered by Task 4. Practice anonymous list and answer oracle are covered by Task 5. Rate limiting is covered by Task 6. Production sample secrets are covered by Task 7. Docker port exposure is covered by Task 8. Excel formula escaping is covered by Task 9. XLSX import resource exhaustion follow-up is covered by Task 10. Final docs and verification are covered by Task 11.
- Placeholder scan: the plan avoids placeholder terms and gives concrete code, commands, and expected results for each implementation step.
- Type consistency: `login_code` is used in backend request/import schemas and frontend request payload; it is not added to `CandidateRead` or frontend `Candidate` because login codes must not be returned to clients.
