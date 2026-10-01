"""Single error shape for the API: {error: {code, message}}.

Starlette 1.x no longer routes arbitrary exception classes through `exception_handler`, so the
KeyError/ValueError mapping is a middleware; AppError keeps the explicit handler.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.models_ai.gateway import GatewayError
from app.models_ai.routing import NoModelReady

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _json(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return _json(exc.http_status, exc.code, exc.message)

    @app.middleware("http")
    async def _map_domain_errors(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except AppError as exc:
            return _json(exc.http_status, exc.code, exc.message)
        except KeyError as exc:
            return _json(404, "not_found", str(exc).strip("'"))
        except ValueError as exc:
            return _json(400, "bad_request", str(exc))
        except NoModelReady as exc:
            return _json(503, "no_model_ready", str(exc))
        except GatewayError:
            logger.exception("model gateway failed")
            return _json(
                502,
                "tutor_failed",
                "The tutor model did not answer. Nothing was changed. Try again, or check "
                "Models › Routing.",
            )
