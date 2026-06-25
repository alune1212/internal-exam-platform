import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import router
from app.core.config import settings
from app.core.exceptions import DomainError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Internal Exam Platform API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        _request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.error("数据库异常", exc_info=exc)
        return JSONResponse(
            status_code=500, content={"detail": "服务器内部错误，请稍后重试。"}
        )

    @app.exception_handler(Exception)
    async def fallback_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("未捕获异常", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误。"})

    app.include_router(router)
    return app


app = create_app()
