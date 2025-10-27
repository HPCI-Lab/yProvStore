import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from application.settings import DEBUG

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses in the application.
    If DEBUG is enabled, it logs the request method, URL, query parameters,
    response status code, headers, and body.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if DEBUG:
            logger.debug(f"Processing request: {request.method} {request.url} with parameters: {request.query_params}")

        # === Add other logs before executing the request if needed ===

        response = await call_next(request)

        if DEBUG:
            logger.debug(
                f"Response status code: {response.status_code}, "
                f"headers: {response.headers}, "
                "body: " + (response.body.decode('utf-8') if hasattr(response, "body") and response.body else 'None')
            )

        # === Add other logs after executing the request if needed ===

        return response
