class DomainError(Exception):
    """业务领域异常基类，status_code 用于 API 层统一映射。"""

    status_code: int = 400
