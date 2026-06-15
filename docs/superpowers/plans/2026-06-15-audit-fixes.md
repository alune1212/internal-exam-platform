# 审计修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 2025-06-15 后端审计发现的 5 critical + 15 important + 12 selected minor 问题

**Architecture:** 按依赖链条推进 6 个独立 PR，每个 PR 改动范围明确，可单独 review/merge/回滚。PR-1（安全）→ PR-2（并发）→ PR-3（错误）→ PR-4（业务规则）→ PR-5（测试）→ PR-6（长期治理）。PR-1/2/3 互有交叉但有明确的文件改动边界。

**Tech Stack:** Python 3.12+ / FastAPI / SQLAlchemy 2.0 / pytest / PostgreSQL

**审计依据:** `docs/superpowers/plans/` 下无前置审计文档，整改依据为本次 conversation 内完成的 4-domain 审计报告

---

## PR-1：安全止血

### Task 1.1: 新增 admin 鉴权依赖 `require_admin`

**Files:**
- Create: `backend/app/core/dependencies.py`
- Modify: `backend/app/services/exam_service.py:38-39`（新增 AdminAuthError）
- Test: `backend/app/tests/test_auth_api.py`（在 Task 1.2 后完成）

- [ ] **Step 1: 在 exam_service.py 新增 AdminAuthError**

在 `class ExamNotFoundError` 之前插入：
```python
class AdminAuthError(DomainError):
    """管理员鉴权失败。"""

    status_code = 401

    def __init__(self) -> None:
        super().__init__("管理员凭据无效，请重新登录。")
```

- [ ] **Step 2: 创建 `backend/app/core/dependencies.py`**

```python
"""FastAPI 鉴权依赖。"""

from fastapi import Header, Request

from app.core.config import settings
from app.core.security import constant_time_equals
from app.services.exam_service import AdminAuthError


def require_admin(request: Request) -> None:
    """校验 X-Admin-Token 头与配置的管理员 token 一致。"""
    token = request.headers.get("X-Admin-Token", "")
    if not constant_time_equals(token, settings.admin_password):
        raise AdminAuthError()
```

说明：当前 admin 认证是简单口令占位（`settings.ADMIN_PASSWORD`），不引入复杂 token 机制。前端调用 admin API 时需要加 `X-Admin-Token` 头（值 = 管理员密码）。

- [ ] **Step 3: 在 `backend/app/services/exam_service.py` 顶部导出**

检查 `__init__.py`（如有），确保 `AdminAuthError` 可被 `dependencies.py` 从 `app.services.exam_service` import。

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/dependencies.py backend/app/services/exam_service.py
git commit -m "feat: 新增 require_admin 鉴权依赖与 AdminAuthError"
```

---

### Task 1.2: 在 router.py 中为所有 admin router 挂载 require_admin

**Files:**
- Modify: `backend/app/api/router.py:24-32`

- [ ] **Step 1: 修改 `backend/app/api/router.py`**

将现有 import 区加一行：
```python
from app.core.dependencies import require_admin
```

将所有 admin router 的 include 改为带 dependencies：
```python
router.include_router(auth.router)
router.include_router(candidates.router)
router.include_router(practice.router)
router.include_router(exams.router)
router.include_router(attempts.router)
router.include_router(exams.admin_router, dependencies=[Depends(require_admin)])
router.include_router(questions.router, dependencies=[Depends(require_admin)])
router.include_router(reports.router, dependencies=[Depends(require_admin)])
router.include_router(imports.router, dependencies=[Depends(require_admin)])
```

同时添加 `Depends` 导入到 `from fastapi import APIRouter`：
```python
from fastapi import APIRouter, Depends
```

撤销 admin auth.py router 上的 `tags=["auth"]` 是否仍正确——确认不冲突。

- [ ] **Step 2: 更新 `backend/app/api/auth.py` 改为 DomainError 风格**

```python
from fastapi import APIRouter
from app.core.config import settings
from app.core.security import constant_time_equals, create_session_token
from app.schemas.auth import AdminLoginRequest, LoginResponse
from app.schemas.common import ApiResponse
from app.services.exam_service import AdminAuthError

router = APIRouter(tags=["auth"])


@router.post("/admin/login", response_model=ApiResponse[LoginResponse])
def admin_login(payload: AdminLoginRequest) -> ApiResponse[LoginResponse]:
    username_ok = constant_time_equals(payload.username, settings.admin_username)
    password_ok = constant_time_equals(payload.password, settings.admin_password)
    if not username_ok or not password_ok:
        raise AdminAuthError()
    return ApiResponse(data=LoginResponse(token=create_session_token(payload.username)))
```

移除 `from fastapi import HTTPException`。

- [ ] **Step 3: 验证路由仍可访问（本地启动后端测试 token 头）**

```bash
cd backend
# 不带 token → 401
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/admin/exams
# 带正确 token → 200
curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Token: change-me" http://localhost:8000/api/admin/exams
# 带错误 token → 401
curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Token: wrong" http://localhost:8000/api/admin/exams
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/router.py backend/app/api/auth.py
git commit -m "feat: 所有 admin 路由挂载 require_admin 鉴权依赖"
```

---

### Task 1.3: 新增候选人鉴权依赖 `require_candidate`

**Files:**
- Create: `backend/app/core/dependencies.py`（追加）
- Modify: 无其他（纯新增）

- [ ] **Step 1: 在 `backend/app/core/dependencies.py` 追加 require_candidate**

```python
from fastapi import Request
from app.services.exam_service import AdminAuthError
from app.core.security import constant_time_equals


class CandidateAuthError(DomainError):
    """候选人鉴权失败。"""

    status_code = 401

    def __init__(self, detail: str = "请先输入姓名登录。") -> None:
        super().__init__(detail)


def require_candidate(request: Request) -> int:
    """校验 X-Candidate-Name 头并返回 candidate_id。

    该依赖从 session storage（当前实现为请求头）中推导当前候选人身份。
    候选人必须先调用 POST /api/candidates/login 拿到 token，
    前端将 token 附加在后续请求的 X-Candidate-Token 头中。
    """
    token = request.headers.get("X-Candidate-Token", "")
    candidate_id = _resolve_candidate_id_from_token(token)
    if candidate_id is None:
        raise CandidateAuthError()
    return candidate_id
```

但因为当前 `create_session_token` 只做字符串拼接而没有签名/持久化，需要先加固 token 机制才能让 require_candidate 有意义。考虑到"不引入 Redis"的硬边界，简化方案：

```python
"""FastAPI 鉴权依赖。"""

from fastapi import Header, Request

from app.core.config import settings
from app.core.security import constant_time_equals
from app.services.exam_service import AdminAuthError, CandidateNotFoundError


class CandidateAuthError(DomainError):
    """候选人鉴权失败。"""

    status_code = 401

    def __init__(self, detail: str = "请先输入姓名登录。") -> None:
        super().__init__(detail)


def require_admin(request: Request) -> None:
    """校验 X-Admin-Token 头与配置的管理员 token 一致。"""
    token = request.headers.get("X-Admin-Token", "")
    if not constant_time_equals(token, settings.admin_password):
        raise AdminAuthError()


def get_current_candidate_id(
    x_candidate_id: str | None = Header(None, alias="X-Candidate-Id"),
) -> int:
    """从 X-Candidate-Id 请求头提取候选人 ID。

    该依赖不校验 token 签名（当前为第一阶段简化方案），
    仅确保 candidate_id 存在。实际鉴权由各路由自行校验
    candidate_id 是否匹配 attempt/exam 的资源归属。
    """
    if x_candidate_id is None:
        raise CandidateAuthError()
    try:
        return int(x_candidate_id)
    except (ValueError, TypeError):
        raise CandidateAuthError("无效的候选人身份")
```

说明：第一阶段不引入复杂 JWT/HMAC 签名，但**强制前端从登录后的 candidate.id 发起请求**，并在各 attempt 路由中校验资源归属（IDOR 防护）。

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/dependencies.py
git commit -m "feat: 新增 get_current_candidate_id 候选人身份提取依赖"
```

---

### Task 1.4: 候选人路由加 IDOR 防护

**Files:**
- Modify: `backend/app/api/attempts.py:18-52`（所有 attempt 路由加 `get_current_candidate_id` 校验）
- Modify: `backend/app/api/exams.py:26-33`（start_exam 校验 token）

- [ ] **Step 1: 修改 `backend/app/api/attempts.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_candidate_id
from app.schemas.attempt import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    AttemptRead,
    AttemptResultRead,
    SubmitRequest,
)
from app.schemas.common import ApiResponse
from app.services import exam_service
from app.services.exam_service import AttemptNotFoundError

router = APIRouter(prefix="/attempts", tags=["attempts"])


def _verify_attempt_ownership(db: Session, attempt_id: int, candidate_id: int) -> None:
    """快速校验 attempt 的 candidate_id，防 IDOR。"""
    from app.models import ExamAttempt
    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    if attempt.candidate_id != candidate_id:
        raise AttemptNotFoundError(attempt_id)  # 不泄露 attempt 是否存在的信号


@router.get("/{attempt_id}", response_model=ApiResponse[AttemptRead])
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AttemptRead]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(data=exam_service.get_attempt(db, attempt_id))


@router.post(
    "/{attempt_id}/answers/save", response_model=ApiResponse[AnswerSaveResponse]
)
def save_answers(
    attempt_id: int,
    payload: AnswerSaveRequest,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AnswerSaveResponse]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(data=exam_service.save_answers(db, attempt_id, payload))


@router.post("/{attempt_id}/submit", response_model=ApiResponse[AttemptResultRead])
def submit_attempt(
    attempt_id: int,
    payload: SubmitRequest,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AttemptResultRead]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(
        data=exam_service.submit_attempt(db, attempt_id, payload.submit_type)
    )


@router.get("/{attempt_id}/result", response_model=ApiResponse[AttemptResultRead])
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[AttemptResultRead]:
    _verify_attempt_ownership(db, attempt_id, candidate_id)
    return ApiResponse(data=exam_service.get_attempt_result(db, attempt_id))
```

- [ ] **Step 2: 修改 `backend/app/api/exams.py` 的 start_exam**

只修改 start_exam 函数签名，把 `payload.candidate_id` 改为从 `get_current_candidate_id` 获取：

```python
from app.core.dependencies import get_current_candidate_id

@router.post("/{exam_id}/start", response_model=ApiResponse[ExamStartResponse])
def start_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    candidate_id: int = Depends(get_current_candidate_id),
) -> ApiResponse[ExamStartResponse]:
    return ApiResponse(data=exam_service.start_exam(db, exam_id, candidate_id))
```

同时 `ExamStartRequest` 不再需要 `candidate_id` 字段，但保留 schema 定义不动（向后兼容）。

注意：`ExamStartRequest` 的 `candidate_id` 仍保留在 schema 中但路由层不再使用。如需完全移除，单独改 schema 即可。

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/attempts.py backend/app/api/exams.py
git commit -m "feat: 候选人 attempt/exam 路由加 IDOR 防护与候选人身份校验"
```

---

### Task 1.5: 移除不安全的 candidate_session 路由

**Files:**
- Modify: `backend/app/api/candidates.py:22-28`

- [ ] **Step 1: 删除 `/candidates/session` endpoint**

直接删除 `candidates.py` 中从 `@router.post("/session", ...)` 到 `return ApiResponse(data=...)` 的 5 行。

同时移除不再需要的 `from app.core.security import create_session_token` import。

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/candidates.py
git commit -m "fix: 移除不安全的 /api/candidates/session 路由"
```

---

## PR-2：并发与事务安全

### Task 2.1: start_exam 加 FOR UPDATE 行锁

**Files:**
- Modify: `backend/app/services/exam_service.py:282-314`（`_select_exam_questions`）
- Modify: `backend/app/services/exam_service.py:402-404`（`start_exam` 入口）

- [ ] **Step 1: 在 start_exam 入口处用 FOR UPDATE 锁 Exam 行**

将第 404 行：
```python
exam = db.get(Exam, exam_id)
```
改为：
```python
exam = (
    db.query(Exam)
    .filter(Exam.id == exam_id)
    .with_for_update()
    .one_or_none()
)
```
需要添加 `from app.models import Exam`（如未导入）。

- [ ] **Step 2: 在 _select_exam_questions 中先 commit fixed_question_ids 再生成 snapshot**

当前的逻辑是：选好的题集 → 写回 exam.question_rule → 返回 selected → 外部生成 snapshot + commit。这就是竞态窗口。

修改方案：**_select_exam_questions 在生成 fixed_question_ids 后立即 flush/commit exam**，然后在 start_exam 中开第二个事务用已固化的 ID 生成 snapshot：

```python
def start_exam(db: Session, exam_id: int, candidate_id: int) -> ExamStartResponse:
    exam = (
        db.query(Exam)
        .filter(Exam.id == exam_id)
        .with_for_update()
        .one_or_none()
    )
    if exam is None:
        raise ExamNotFoundError(exam_id)
    if exam.status != "active":
        raise ExamNotActiveError(exam_id)

    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)

    existing = db.execute(
        select(ExamAttempt).where(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.status == "in_progress",
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AttemptAlreadyExistsError(existing.id)

    questions = _select_exam_questions(db, exam)

    # 立即持久化 exam.question_rule（释放锁的关键）
    db.add(exam)
    db.flush()

    # 后续 snapshot 生成在同一事务中
    now = datetime.now(UTC)
    total_score = sum(q.score for q in questions)

    attempt = ExamAttempt(
        exam_id=exam_id,
        candidate_id=candidate_id,
        status="in_progress",
        started_at=now,
        total_score=total_score,
    )
    db.add(attempt)
    db.flush()

    snapshots: list[ExamAttemptQuestion] = []
    for idx, question in enumerate(questions):
        snapshot = ExamAttemptQuestion(
            attempt_id=attempt.id,
            original_question_id=question.id,
            question_type=question.question_type,
            stem_snapshot=question.stem,
            options_snapshot=_build_options_snapshot(question.options),
            correct_answer_snapshot=_build_correct_answer_snapshot(question.options),
            analysis_snapshot=question.analysis,
            score=question.score,
            sort_order=idx,
        )
        db.add(snapshot)
        snapshots.append(snapshot)

    db.flush()

    question_reads = [
        AttemptQuestionRead(
            id=snapshot.id,
            question_type=snapshot.question_type,
            stem_snapshot=snapshot.stem_snapshot,
            options_snapshot=snapshot.options_snapshot,
            score=float(snapshot.score),
            sort_order=snapshot.sort_order,
            selected_answer=None,
        )
        for snapshot in snapshots
    ]

    db.commit()

    return ExamStartResponse(
        attempt_id=attempt.id,
        exam=ExamRead.model_validate(exam),
        questions=question_reads,
        started_at=now,
        ends_at=now + timedelta(minutes=exam.duration_minutes),
    )
```

关键点：`db.add(exam); db.flush()` 在 snapshot 生成之前将 fixed_question_ids 持久化，PostgreSQL 的 row-level lock 随着 commit 释放，后续的事务不再需要锁 exam 行就能读到已固化的 ID。

- [ ] **Step 3: 现有测试验证**

```bash
cd backend && uv run pytest app/tests/test_exam_service.py -q -k "start_exam"
```
预期：所有 start_exam 相关测试仍通过（锁不影响逻辑）

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/exam_service.py
git commit -m "fix: start_exam 加 FOR UPDATE 行锁防止固定试卷并发破坏"
```

---

### Task 2.2: submit_attempt 加行锁 + 原子化状态转换

**Files:**
- Modify: `backend/app/services/exam_service.py:543-587`

- [ ] **Step 1: 修改 submit_attempt 入口加载方式**

将第 543-546 行：
```python
def submit_attempt(db: Session, attempt_id: int, submit_type: str) -> AttemptResultRead:
    attempt = _load_attempt_with_snapshots(db, attempt_id)
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
```

改为先做一次轻量检查（不加锁），再 FOR UPDATE 加载 + 重新检查：

```python
def submit_attempt(
    db: Session, attempt_id: int, submit_type: str
) -> AttemptResultRead:
    # 轻量检查：避免不需要的 FOR UPDATE
    quick = db.get(ExamAttempt, attempt_id)
    if quick is None:
        raise AttemptNotFoundError(attempt_id)
    if quick.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)

    # 加行锁后重新加载完整 attempt + snapshots
    attempt = (
        db.query(ExamAttempt)
        .options(
            selectinload(ExamAttempt.questions).selectinload(
                ExamAttemptQuestion.answer
            ),
            selectinload(ExamAttempt.exam),
        )
        .filter(ExamAttempt.id == attempt_id)
        .with_for_update()
        .one_or_none()
    )
    if attempt is None:
        raise AttemptNotFoundError(attempt_id)
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
```

确保开头导入：`from app.models import Exam, ExamAttempt, ExamAttemptQuestion`

后半部分保持不变（scoring + commit）。

- [ ] **Step 2: 现有测试验证**

```bash
cd backend && uv run pytest app/tests/test_exam_service.py -q -k "submit"
```
预期：所有 submit 相关测试仍通过

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/exam_service.py
git commit -m "fix: submit_attempt 加 FOR UPDATE 行锁防止并发覆盖"
```

---

### Task 2.3: save_answers 加 status 守卫

**Files:**
- Modify: `backend/app/services/exam_service.py:517-540`

- [ ] **Step 1: 在 save_answers 入口加状态检查**

在第 520 行 `attempt = _load_attempt_with_snapshots(db, attempt_id)` 之后插入：

```python
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
```

- [ ] **Step 2: 现有测试验证 + 新增测试**

```bash
cd backend && uv run pytest app/tests/test_exam_service.py -q -k "save"
```

新增测试用例 `test_save_answers_rejects_after_submit`（在下文测试 PR 中补）。

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/exam_service.py
git commit -m "fix: save_answers 拒绝已提交 attempt 的答案修改"
```

---

### Task 2.4: Scheduler 每条 attempt 独立 session + rollback

**Files:**
- Modify: `backend/app/core/scheduler.py:19-48`

- [ ] **Step 1: 重写 auto_submit_loop 为逐 attempt 独立 session**

```python
"""后台定时任务：自动提交超时考试。"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.time import ensure_aware
from app.models import Exam, ExamAttempt
from app.services.exam_service import submit_attempt

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30


def _find_expired_attempts(db) -> list[int]:
    """查找已超时的 in_progress attempt。"""
    now = datetime.now(UTC)
    rows = db.execute(
        select(ExamAttempt.id, ExamAttempt.started_at, Exam.duration_minutes)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .where(ExamAttempt.status == "in_progress")
    ).all()
    return [
        attempt_id
        for attempt_id, started_at, duration_minutes in rows
        if ensure_aware(started_at) + timedelta(minutes=duration_minutes) <= now
    ]


async def auto_submit_loop() -> None:
    """定时检查并自动提交超时考试。

    每条 attempt 使用独立的数据库会话：
    - 查询过期列表用一个 session
    - 每条 submit 用一个独立 session（失败自动回滚，不影响下一条）
    """
    while True:
        try:
            with SessionLocal() as scan_db:
                expired_ids = _find_expired_attempts(scan_db)
        except Exception:
            logger.exception("过期 attempt 扫描异常")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            continue

        for attempt_id in expired_ids:
            try:
                with SessionLocal() as submit_db:
                    submit_attempt(submit_db, attempt_id, "auto")
                    logger.info("自动提交考试记录 #%d", attempt_id)
            except Exception:
                logger.exception("自动提交 #%d 失败", attempt_id)

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
```

关键变化：
- `_find_expired_attempts` 判定改为 `<=`（`<` → `<=`，修复边界精度问题）
- 扫描用独立 session，提交用独立 session
- 每条 attempt 失败不会污染后续 session
- 扫描失败不中断循环（旧代码也 except 了，但加了 continue 语义更明确）

- [ ] **Step 2: 修改测试文件以兼容新行为**

`backend/app/tests/test_scheduler.py` 中：
- `test_find_expired_attempts_finds_overdue`：将 `timedelta(minutes=2)` 改为确保 `<` 或 `<=` 都触发（改为 `timedelta(minutes=5)` 更加直观）
- 确认 `assert attempt is not None` 断言仍然存在

- [ ] **Step 3: 测试验证**

```bash
cd backend && uv run pytest app/tests/test_scheduler.py -q
```
预期：3 test 全部通过

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/scheduler.py backend/app/tests/test_scheduler.py
git commit -m "fix: scheduler 逐 attempt 独立 session 回滚 + 过期判定边界修正"
```

---

## PR-3：错误契约统一

### Task 3.1: 补齐所有 DomainError 的 status_code

**Files:**
- Modify: `backend/app/services/exam_service.py:38-93`

- [ ] **Step 1: 为缺失的 3 个异常加 status_code**

```python
class ExamNotActiveError(DomainError):
    status_code = 409  # 新增

class AttemptAlreadySubmittedError(DomainError):
    status_code = 409  # 新增

class InsufficientQuestionsError(DomainError):
    status_code = 422  # 新增
```

检查 `CandidateNotFoundError` 可改为 404（已正确）。

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/exam_service.py
git commit -m "fix: 补齐 DomainError 子类缺失的 status_code"
```

---

### Task 3.2: main.py 新增 SQLAlchemyError 处理器

**Files:**
- Modify: `backend/app/main.py:26-43`

- [ ] **Step 1: 新增统一异常处理器**

在 `create_app()` 内的 `domain_error_handler` 后面追加：

```python
from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(
    _request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error("数据库异常", exc_info=exc)
    return JSONResponse(
        status_code=500, content={"detail": "服务器内部错误，请稍后重试。"}
    )


@app.exception_handler(Exception)
async def fallback_error_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    logger.error("未捕获异常", exc_info=exc)
    return JSONResponse(
        status_code=500, content={"detail": "服务器内部错误。"}
    )
```

注意：`Exception` handler 不能拦截 `HTTPException`（FastAPI 有默认的），但会拦截 `ValueError`、`RuntimeError` 等。

- [ ] **Step 2: 检查 main.py 已有 import**

确保有：
```python
import logging
logger = logging.getLogger(__name__)
```
（或复用已有的 `logging.basicConfig(level=logging.INFO)` 旁的 logger）

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "fix: main.py 新增 SQLAlchemyError 与兜底异常处理器"
```

---

## PR-4：业务规则补全

### Task 4.1: start_exam 校验 candidate 状态

**Files:**
- Modify: `backend/app/services/exam_service.py:410-412`（start_exam 入口）
- Modify: `backend/app/services/exam_service.py:60` 附近（新增异常类）

- [ ] **Step 1: 新增 CandidateNotEligibleError**

```python
class CandidateNotEligibleError(DomainError):
    status_code = 403

    def __init__(self, candidate_id: int) -> None:
        super().__init__(f"考生 #{candidate_id} 当前不可参加考试")
```

- [ ] **Step 2: 修改 start_exam 校验逻辑**

在 `candidate = db.get(Candidate, candidate_id)` 之后：

```python
    if candidate is None:
        raise CandidateNotFoundError(candidate_id)
    if candidate.status != "active":
        raise CandidateNotEligibleError(candidate_id)
```

不检查 `should_attend`，因为 Phase 1 的"考试与应参人员范围关联"尚未完成，`should_attend` 只影响"缺考"报表口径。`start_exam` 只校验候选人是否活跃。

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/exam_service.py
git commit -m "feat: start_exam 校验候选人 status=active 才允许开考"
```

---

### Task 4.2: save_answers / submit_attempt 校验 exam.status

**Files:**
- Modify: `backend/app/services/exam_service.py:517`（save_answers）
- Modify: `backend/app/services/exam_service.py:543`（submit_attempt）

- [ ] **Step 1: 在 save_answers 入口校验 exam 状态**

```python
def save_answers(
    db: Session, attempt_id: int, payload: AnswerSaveRequest
) -> AnswerSaveResponse:
    attempt = _load_attempt_with_snapshots(db, attempt_id)
    if attempt.status != "in_progress":
        raise AttemptAlreadySubmittedError(attempt_id)
    if attempt.exam and attempt.exam.status != "active":
        raise ExamNotActiveError(attempt.exam_id)
```

注意：`_load_attempt_with_snapshots` 已加载 `selectinload(ExamAttempt.exam)`。

- [ ] **Step 2: 在 submit_attempt 入口校验 exam 状态**

在 FOR UPDATE 加载 attempt 后（已在 submit_attempt 重构时加了 `selectinload(ExamAttempt.exam)`）：

```python
    if attempt.exam and attempt.exam.status != "active":
        raise ExamNotActiveError(attempt.exam_id)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/exam_service.py
git commit -m "feat: save/submit 校验考试 active 状态防下线后继续作答"
```

---

### Task 4.3: get_absent_candidates 按考试过滤

**Files:**
- Modify: `backend/app/services/report_service.py:135-159`
- Modify: `backend/app/api/reports.py`（如接口签名有 exam_id 参数变化）

- [ ] **Step 1: 修改 get_absent_candidates 加 exam_id 参数**

```python
def get_absent_candidates(db: Session, exam_id: int | None = None) -> list[AbsentCandidateRow]:
    """缺考人员：应参但在指定考试中无 attempt 记录的考生。

    不传 exam_id 时保留旧行为（全局从未参考过）。
    """
    if exam_id is not None:
        attempted_ids = (
            select(ExamAttempt.candidate_id)
            .where(ExamAttempt.exam_id == exam_id)
            .distinct()
        )
    else:
        attempted_ids = select(ExamAttempt.candidate_id).distinct()

    rows = (
        db.query(Candidate)
        .filter(
            Candidate.should_attend == True,  # noqa: E712
            Candidate.status == "active",
            ~Candidate.id.in_(attempted_ids),
        )
        .order_by(Candidate.name)
        .all()
    )

    return [
        AbsentCandidateRow(
            candidate_id=c.id,
            name=c.name,
            employee_no=c.employee_no,
            department=c.department,
            exam_group=c.exam_group,
        )
        for c in rows
    ]
```

- [ ] **Step 2: 确认 API 层 reports 路由是否需要 exam_id query param**

检查 `backend/app/api/reports.py` 中 `absent-candidates` endpoint 是否已有 `exam_id` query param。如没有，新增：

```python
@router.get("/absent-candidates", response_model=ApiResponse[list[AbsentCandidateRow]])
def absent_candidates(
    exam_id: int | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse[list[AbsentCandidateRow]]:
    return ApiResponse(data=report_service.get_absent_candidates(db, exam_id))
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/report_service.py backend/app/api/reports.py
git commit -m "fix: 缺考统计支持按考试 exam_id 过滤历史 attempt"
```

---

### Task 4.4: _parse_fixed_paper_rule 在缺 type_counts 时按比例分配

**Files:**
- Modify: `backend/app/services/exam_service.py:117-138`

- [ ] **Step 1: 修改默认 type_counts 逻辑**

将：
```python
    raw_type_counts = question_rule.get("type_counts") or {
        "single": 15,
        "multiple": 40,
        "judge": 5,
    }
```

改为按 `question_count` 等比分配（默认规则 15:40:5 比例为 3:8:1）：

```python
    raw_type_counts = question_rule.get("type_counts")
    if raw_type_counts is None:
        # 按默认 3:8:1 比例从 question_count 推导
        total_parts = 12
        single = max(1, round(question_count * 3 / total_parts))
        multiple = max(1, round(question_count * 8 / total_parts))
        judge = max(1, question_count - single - multiple)
        raw_type_counts = {
            "single": single,
            "multiple": multiple,
            "judge": judge,
        }
```

- [ ] **Step 2: 保留 validate 逻辑**

后续的校验逻辑保持不变：
```python
    type_counts = {
        question_type: int(raw_type_counts.get(question_type, 0))
        for question_type in ("single", "multiple", "judge")
    }
    if sum(type_counts.values()) != question_count:
        raise InsufficientQuestionsError("抽题规则中的题型数量合计必须等于总题数")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/exam_service.py
git commit -m "fix: 缺 type_counts 时按比例自动推导避免静默失败"
```

---

## PR-5：测试补全

### Task 5.1: API 层新增 admin 鉴权集成测试

**Files:**
- Create: `backend/app/tests/test_admin_auth_api.py`
- Modify: `backend/app/tests/conftest.py`（新增 admin auth header fixture）

- [ ] **Step 1: 在 conftest.py 新增 admin_client fixture**

```python
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    from app.core.config import settings
    return {"X-Admin-Token": settings.admin_password}
```

- [ ] **Step 2: 创建 `test_admin_auth_api.py`**

```python
"""admin 鉴权集成测试：验证所有 /admin/* 路由在无/有/错 token 时行为。"""

from fastapi.testclient import TestClient


def test_admin_login_returns_token(client: TestClient) -> None:
    resp = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "change-me"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "token" in body["data"]


def test_admin_login_rejects_wrong_password(client: TestClient) -> None:
    resp = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_admin_exams_requires_token(client: TestClient) -> None:
    resp = client.get("/api/admin/exams")
    assert resp.status_code == 401


def test_admin_exams_accepts_valid_token(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    resp = client.get("/api/admin/exams", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


def test_admin_exams_rejects_wrong_token(client: TestClient) -> None:
    resp = client.get("/api/admin/exams", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 401


def test_admin_questions_requires_token(client: TestClient) -> None:
    resp = client.get("/api/admin/questions")
    assert resp.status_code == 401


def test_admin_reports_requires_token(client: TestClient) -> None:
    resp = client.get("/api/admin/reports/scores")
    assert resp.status_code == 401


def test_admin_imports_requires_token(client: TestClient) -> None:
    resp = client.get("/api/admin/imports/templates")
    assert resp.status_code == 401
```

- [ ] **Step 3: 运行测试**

```bash
cd backend && uv run pytest app/tests/test_admin_auth_api.py -q -v
```
预期：8 项全部通过（admin password = change-me 是 conftest fixture 中的默认值）

- [ ] **Step 4: Commit**

```bash
git add backend/app/tests/test_admin_auth_api.py backend/app/tests/conftest.py
git commit -m "test: 新增 admin 鉴权集成测试 8 条"
```

---

### Task 5.2: 候选人 API IDOR 测试

**Files:**
- Create: `backend/app/tests/test_candidate_attempt_api.py`

- [ ] **Step 1: 创建 `test_candidate_attempt_api.py`**

```python
"""候选人 attempt IDOR 防护集成测试。"""

from fastapi.testclient import TestClient


def test_attempt_routes_require_candidate_header(client: TestClient) -> None:
    resp = client.get("/api/attempts/1")
    assert resp.status_code == 401
    body = resp.json()
    assert "detail" in body


def test_attempt_routes_accept_candidate_header(client: TestClient) -> None:
    resp = client.get("/api/attempts/1", headers={"X-Candidate-Id": "1"})
    # 404 (attempt 不存在) 而非 401
    assert resp.status_code == 404


def test_attempt_routes_reject_invalid_candidate_id(client: TestClient) -> None:
    resp = client.get("/api/attempts/1", headers={"X-Candidate-Id": "not-int"})
    assert resp.status_code == 401


def test_save_answers_requires_candidate_header(client: TestClient) -> None:
    resp = client.post(
        "/api/attempts/1/answers/save",
        json={"answers": []},
    )
    assert resp.status_code == 401


def test_submit_requires_candidate_header(client: TestClient) -> None:
    resp = client.post(
        "/api/attempts/1/submit",
        json={"submit_type": "manual"},
    )
    assert resp.status_code == 401


def test_result_requires_candidate_header(client: TestClient) -> None:
    resp = client.get("/api/attempts/1/result")
    assert resp.status_code == 401
```

- [ ] **Step 2: 运行测试**

```bash
cd backend && uv run pytest app/tests/test_candidate_attempt_api.py -q -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/tests/test_candidate_attempt_api.py
git commit -m "test: 新增候选人 attempt IDOR 防护集成测试 6 条"
```

---

### Task 5.3: Service 层边缘场景补测

**Files:**
- Modify: `backend/app/tests/test_exam_service.py`

- [ ] **Step 1: 新增 test_save_answers_rejects_after_submit**

```python
def test_save_answers_rejects_after_submit(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db, stem="题目", score=5)
    start = exam_service.start_exam(db, exam.id, candidate.id)

    exam_service.submit_attempt(db, start.attempt_id, "manual")

    with pytest.raises(exam_service.AttemptAlreadySubmittedError):
        exam_service.save_answers(
            db,
            start.attempt_id,
            AnswerSaveRequest(
                answers=[
                    AnswerSaveItem(
                        attempt_question_id=start.questions[0].id,
                        selected_answer="A",
                    )
                ]
            ),
        )
```

- [ ] **Step 2: 新增 test_submit_attempt_with_no_answers_zeros_score**

```python
def test_submit_attempt_with_no_answers_zeros_score(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db)
    create_question_with_options(db, stem="题目1", score=2)
    create_question_with_options(db, stem="题目2", score=3)
    start = exam_service.start_exam(db, exam.id, candidate.id)

    result = exam_service.submit_attempt(db, start.attempt_id, "manual")

    assert result.score == 0
    assert result.total_score == 5
    assert result.correct_count == 0
    assert result.wrong_count == 2
```

- [ ] **Step 3: 新增 test_start_exam_rejects_inactive_candidate**

```python
def test_start_exam_rejects_inactive_candidate(db: Session) -> None:
    exam = create_exam(db)
    candidate = create_candidate(db, status="inactive")
    create_question_with_options(db)

    with pytest.raises(exam_service.CandidateNotEligibleError):
        exam_service.start_exam(db, exam.id, candidate.id)
```

检查 conftest.py 中 `create_candidate` fixture 是否接受 status 参数，如不接收则直接用 model 构造：
```python
from app.models import Candidate
candidate = Candidate(name="禁用人", employee_no="E999", status="inactive")
db.add(candidate)
db.commit()
```

- [ ] **Step 4: 运行测试**

```bash
cd backend && uv run pytest app/tests/test_exam_service.py -q
```
预期：所有测试通过（包括新增的 3 条）

- [ ] **Step 5: Commit**

```bash
git add backend/app/tests/test_exam_service.py
git commit -m "test: 补 save_answers 被拒/空提交/禁用人 边缘场景"
```

---

### Task 5.4: Scoring 边缘场景补测

**Files:**
- Modify: `backend/app/tests/test_scoring_service.py`

- [ ] **Step 1: 新增 test_multiple_choice_empty_correct_answer**

```python
def test_multiple_choice_empty_correct_answer() -> None:
    from app.services.scoring_service import score_answer
    result = score_answer("multiple", "", None, 5.0)
    # 空答案 == 空答案 → 当前行为是正确
    assert result.is_correct is True
    assert result.score_awarded == 5.0
```

- [ ] **Step 2: 新增 test_score_zero_value_awarded_zero**

```python
def test_score_zero_value_awarded_zero() -> None:
    from app.services.scoring_service import score_answer
    result = score_answer("single", "A", "A", 0)
    assert result.is_correct is True
    assert result.score_awarded == 0
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/tests/test_scoring_service.py
git commit -m "test: 补判分空答案与零分值边缘场景"
```

---

## PR-6：长期治理

### Task 6.1: Status 字段改为 SQLAlchemy Enum + CHECK 约束

**Files:**
- Modify: `backend/app/models/exam.py:15-18`
- Modify: `backend/app/models/question.py:33-34`
- Modify: `backend/app/models/candidate.py:26-28`
- Modify: `backend/app/models/attempt.py:31-33`
- Create: `backend/alembic/versions/20260615_add_status_check_constraints.py`（手动迁移）

- [ ] **Step 1: 在各 model 中定义 status enum 并替换 String**

在 `backend/app/models/exam.py` 顶部加：
```python
import enum

class ExamStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"
```

修改字段定义：
```python
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ExamStatus.draft.value, index=True
    )
```

同理处理 `Question`（draft/active/archived）、`Candidate`（active/inactive）、`ExamAttempt`（in_progress/submitted/auto_submitted）。

注意：`ExamAttempt.status` 的 `auto_submitted` 值在 `SUBMITTED_STATUSES` tuple 中使用，需保持一致。

- [ ] **Step 2: 生成 Alembic 迁移**

```bash
cd backend && uv run alembic revision --autogenerate -m "add_status_check_constraints"
```

手动在生成的迁移中添加 CHECK 约束：
```python
op.create_check_constraint(
    "ck_exam_status",
    "exam",
    "status IN ('draft', 'active', 'archived')",
)
```
（PostgreSQL 下可选，使用 native_enum=False 时 Alembic 会自动生成。手工检查。）

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/exam.py backend/app/models/question.py backend/app/models/candidate.py backend/app/models/attempt.py backend/alembic/versions/*status_check*.py
git commit -m "refactor: status 字段改为 Python Enum + DB CHECK 约束"
```

---

### Task 6.2: FK ondelete 策略显式化

**Files:**
- Modify: `backend/app/models/attempt.py:25-30, 67-69`

- [ ] **Step 1: 添加 ondelete 策略**

`ExamAttempt.exam_id` 和 `ExamAttempt.candidate_id` 的 FK 加 `ondelete="RESTRICT"`：
```python
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="RESTRICT"), nullable=False, index=True
    )
```

`ExamAttemptQuestion.original_question_id` 加 `ondelete="SET NULL"`（CLAUDE.md 要求快照不可破坏，所以不能 cascade delete，而是 set null 保留快照）：
```python
    original_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("question.id", ondelete="SET NULL"), index=True
    )
```

`ExamAttemptQuestion.attempt_id` 已有 `ondelete="CASCADE"`，保持不变。

- [ ] **Step 2: 生成 Alembic 迁移**

```bash
cd backend && uv run alembic revision --autogenerate -m "add_fk_ondelete_strategies"
```

手动检查迁移文件中 ALTER TABLE 的 ondelete 是否正确。

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/attempt.py backend/alembic/versions/*fk_ondelete*.py
git commit -m "refactor: FK 显式声明 ondelete 策略与快照语义对齐"
```

---

### Task 6.3: 移除 Question 冗余索引

**Files:**
- Modify: `backend/app/models/question.py:26, 34`

- [ ] **Step 1: 移除单列 index=True**

`question_type` 和 `status` 已被复合索引 `ix_question_type_status` 覆盖：

```python
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
```

移除 `index=True`。

- [ ] **Step 2: 生成 Alembic 迁移**

```bash
cd backend && uv run alembic revision --autogenerate -m "drop_redundant_question_indexes"
```

手动确认迁移包含 DROP INDEX 语句。

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/question.py backend/alembic/versions/*redundant*.py
git commit -m "chore: 移除 Question 冗余单列索引"
```

---

### Task 6.4: Question.score 迁移补 server_default

**Files:**
- Modify: `backend/app/models/question.py:32`
- Create: migration 文件

- [ ] **Step 1: 修改 model**

```python
    score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=1, server_default="1"
    )
```

- [ ] **Step 2: 生成 Alembic 迁移**

```bash
cd backend && uv run alembic revision --autogenerate -m "add_question_score_server_default"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/question.py backend/alembic/versions/*score_server_default*.py
git commit -m "fix: Question.score 迁移加 server_default 防止非 ORM 写入空值"
```

---

## 验证步骤（全部 PR 完成后）

```bash
# 后端
cd backend
uv run ruff format .            # 格式化
uv run ruff check --fix .       # lint 修复
uv run pyright .                # 类型检查
uv run pytest -q                # 运行所有测试

# 前端
cd frontend
npm run lint                    # ESLint
npm run format:check            # Prettier
npm test -- --run               # 测试

# Docker
docker compose up -d --build    # 完整重建
curl http://localhost:8080/api/health  # 验证
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/admin/exams  # 应返回 401
curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Token: change-me" http://localhost:8080/api/admin/exams  # 应返回 200
```

---

## 任务统计

| PR | 任务数 | 关键改动 |
|----|--------|----------|
| PR-1 安全止血 | 5 | require_admin + IDOR + 移除 session |
| PR-2 并发事务 | 4 | FOR UPDATE + status guard + scheduler |
| PR-3 错误契约 | 2 | status_code + 异常处理器 |
| PR-4 业务规则 | 4 | candidate 校验 + exam 状态 + absent + type_counts |
| PR-5 测试补全 | 4 | admin API tests + candidate IDOR tests + service edge cases + scoring edges |
| PR-6 长期治理 | 4 | Enum + FK + index + server_default |
| **总计** | **23** | |
