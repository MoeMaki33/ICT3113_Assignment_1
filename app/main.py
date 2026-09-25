import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database.db import init_db
from app.routes import search, stats, tickets
from app.services.request_logger import RequestLoggingMiddleware, create_request_logger


def create_app(log_path: str = "logs/service.log") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        yield

    logging.basicConfig(level=settings.log_level.upper())
    application = FastAPI(title="Ticket Triage Service", lifespan=lifespan)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Exclude submitted values (including sensitive narratives) from errors.
        return JSONResponse(status_code=400, content={"detail": [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]})

    @application.exception_handler(SQLAlchemyError)
    async def database_failure(request, exc):
        request.state.error = "DatabaseError"
        return JSONResponse(status_code=500, content={"detail": "Database operation failed"})

    application.include_router(tickets.router)
    application.include_router(search.router)
    application.include_router(stats.router)
    application.add_middleware(RequestLoggingMiddleware, logger=create_request_logger(log_path))
    return application


app = create_app()
