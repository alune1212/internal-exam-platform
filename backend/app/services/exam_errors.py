from app.core.exceptions import DomainError


class AdminAuthError(DomainError):
    """管理员鉴权失败。"""

    status_code = 401

    def __init__(self) -> None:
        super().__init__("管理员凭据无效，请重新登录。")


class ExamNotFoundError(DomainError):
    status_code = 404

    def __init__(self, exam_id: int) -> None:
        self.exam_id = exam_id
        super().__init__(f"考试 #{exam_id} 不存在")


class ExamNotActiveError(DomainError):
    status_code = 409

    def __init__(self, exam_id: int) -> None:
        self.exam_id = exam_id
        super().__init__(f"考试 #{exam_id} 未处于 active 状态")


class ExamNotAvailableError(DomainError):
    status_code = 409

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class CandidateNotFoundError(DomainError):
    status_code = 404

    def __init__(self, candidate_id: int) -> None:
        self.candidate_id = candidate_id
        super().__init__(f"考试人 #{candidate_id} 不存在")


class CandidateNotEligibleError(DomainError):
    status_code = 403

    def __init__(self, candidate_id: int) -> None:
        super().__init__(f"考试人 #{candidate_id} 当前不可参加考试")


class AttemptResultNotReadyError(DomainError):
    status_code = 409

    def __init__(self, attempt_id: int) -> None:
        super().__init__(f"答题记录 #{attempt_id} 尚未交卷，不能查看成绩结果")


class AttemptAlreadyExistsError(DomainError):
    status_code = 409

    def __init__(self, attempt_id: int) -> None:
        self.attempt_id = attempt_id
        super().__init__(f"考试人已有进行中的考试记录 #{attempt_id}")


class AttemptNotFoundError(DomainError):
    status_code = 404

    def __init__(self, attempt_id: int) -> None:
        self.attempt_id = attempt_id
        super().__init__(f"考试记录 #{attempt_id} 不存在")


class AttemptQuestionNotFoundError(DomainError):
    status_code = 404

    def __init__(self, attempt_question_id: int) -> None:
        self.attempt_question_id = attempt_question_id
        super().__init__(f"考试题目 #{attempt_question_id} 不存在")


class AttemptAlreadySubmittedError(DomainError):
    status_code = 409

    def __init__(self, attempt_id: int) -> None:
        self.attempt_id = attempt_id
        super().__init__(f"考试记录 #{attempt_id} 已交卷")


class AttemptSessionConflictError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("本设备的考试会话已失效，请重新验证码登录后接管考试。")


class AttemptRevisionConflictError(DomainError):
    status_code = 409

    def __init__(self, current_revision: int) -> None:
        self.current_revision = current_revision
        super().__init__(
            f"答案版本已更新，当前服务端版本为 {current_revision}，请先重新载入。"
        )


class ResultDetailsNotReadyError(DomainError):
    status_code = 409

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class ResultDetailsAlreadyReleasedError(DomainError):
    status_code = 409

    def __init__(self, exam_id: int) -> None:
        super().__init__(f"考试 #{exam_id} 的答案解析已经发布，不能重复操作。")


class AttemptVoidError(DomainError):
    status_code = 409

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class BulkRetakeConflictError(DomainError):
    status_code = 409

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class InsufficientQuestionsError(DomainError):
    status_code = 422

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ExamFrozenError(DomainError):
    status_code = 409

    def __init__(self, reason: str = "考试发布后结构配置已冻结") -> None:
        super().__init__(reason)


class ExamConfigError(DomainError):
    status_code = 422

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class ExamQuestionPoolMissingError(ExamConfigError):
    def __init__(self, exam_id: int) -> None:
        super().__init__(f"考试 #{exam_id} 已发布但缺少冻结题池，请先执行题池修复")
