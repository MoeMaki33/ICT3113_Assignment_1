import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse

from app.config import settings


def create_request_logger(path: str = "logs/service.log") -> logging.Logger:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"triage.requests.{Path(path).resolve()}")
    # Request audit records must be retained even when LOG_LEVEL is WARNING/ERROR.
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp, logger: logging.Logger):
        self.app = app
        self.logger = logger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        start = datetime.now(timezone.utc)
        timer = perf_counter()
        status = 500
        error = None
        response_started = False
        state = scope.setdefault("state", {})

        async def capture_send(message):
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                message.setdefault("headers", []).append(
                    (b"x-request-id", request_id.encode("ascii"))
                )
            await send(message)

        try:
            await self.app(scope, receive, capture_send)
        except Exception as exc:
            error = type(exc).__name__
            if response_started:
                raise
            # Keep unexpected failures generic and correlated just like handled errors.
            await JSONResponse(status_code=500, content={"detail": "Internal server error"})(
                scope, receive, capture_send
            )
        finally:
            route = scope.get("route")
            self.logger.info(json.dumps({
                "request_id": request_id,
                "timestamp": start.isoformat(),
                # Route template avoids logging arbitrary paths or query narratives.
                "endpoint": getattr(route, "path", "<unmatched>"),
                "method": scope["method"],
                "model": settings.ollama_model,
                "start_time": start.isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "duration_ms": (perf_counter() - timer) * 1000,
                "status_code": status,
                "ticket_id": state.get("ticket_id"),
                "predicted_category": state.get("predicted_category"),
                "error": error or state.get("error") or (
                    f"HTTP {status}" if status >= 400 else None
                ),
            }))
