import json
import logging
import math
import time
from collections import defaultdict, deque
from collections.abc import Mapping
from hmac import compare_digest

from aiohttp import web

logger = logging.getLogger(__name__)


def _error(message: str, status: int) -> web.Response:
    response = web.json_response({"error": message}, status=status)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _header_secret(request: web.Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    scheme, separator, credential = authorization.partition(" ")
    if separator and scheme.casefold() == "bearer" and credential:
        return credential
    return None


def _authorized(supplied: object, expected: bytes) -> bool:
    return isinstance(supplied, str) and compare_digest(supplied.encode(), expected)


def create_sensor_app(logic, shared_secret: str, config: Mapping | None = None) -> web.Application:
    if not isinstance(shared_secret, str) or not shared_secret:
        raise ValueError("iot.shared_secret must be a non-empty string")

    config = config or {}
    max_body = int(config.get("max_request_size_bytes", 16 * 1024))
    rate_limit = int(config.get("rate_limit_requests", 60))
    rate_period = float(config.get("rate_limit_period_seconds", 60))
    min_level = float(config.get("min_water_level", 0))
    max_level = float(config.get("max_water_level", 50))
    if (
        max_body <= 0
        or rate_limit <= 0
        or rate_period <= 0
        or not all(math.isfinite(value) for value in (rate_period, min_level, max_level))
        or min_level >= max_level
    ):
        raise ValueError("Invalid API security configuration")

    expected_secret = shared_secret.encode()
    requests_by_client = defaultdict(deque)

    @web.middleware
    async def security_middleware(request: web.Request, handler):
        if request.path == "/sensor":
            now = time.monotonic()
            requests = requests_by_client[request.remote or "unknown"]
            while requests and requests[0] <= now - rate_period:
                requests.popleft()
            if len(requests) >= rate_limit:
                response = _error("rate limit exceeded", 429)
                response.headers["Retry-After"] = str(math.ceil(rate_period))
                return response
            requests.append(now)

        try:
            response = await handler(request)
        except web.HTTPRequestEntityTooLarge:
            response = _error("request body too large", 413)
        except web.HTTPException as error:
            response = _error(error.reason.lower(), error.status)
        except Exception:
            logger.exception("Unhandled sensor API error")
            response = _error("internal server error", 500)

        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    async def post_sensor(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError, web.HTTPBadRequest):
            return _error("invalid JSON payload", 400)

        if not isinstance(data, Mapping):
            return _error("JSON payload must be an object", 400)

        supplied_secret = _header_secret(request) or data.get("secret")
        if not _authorized(supplied_secret, expected_secret):
            logger.warning("Rejected unauthorized sensor write from %s", request.remote or "unknown")
            return _error("unauthorized", 401)

        water_level = data.get("water_level")
        if isinstance(water_level, bool) or not isinstance(water_level, (int, float)):
            return _error("water_level must be a number", 400)
        try:
            numeric_level = float(water_level)
        except OverflowError:
            return _error("water_level must be finite", 400)
        if not math.isfinite(numeric_level):
            return _error("water_level must be finite", 400)
        if not min_level <= numeric_level <= max_level:
            return _error(f"water_level must be between {min_level:g} and {max_level:g}", 400)

        logger.info("Received water level: %s", water_level)
        await logic.on_sensor_data(water_level)
        return web.json_response({"status": "OK"})

    async def get_sensor(request: web.Request) -> web.Response:
        if not _authorized(_header_secret(request), expected_secret):
            logger.warning("Rejected unauthorized sensor read from %s", request.remote or "unknown")
            return _error("unauthorized", 401)
        return web.json_response(logic.sensor_data)

    app = web.Application(client_max_size=max_body, middlewares=[security_middleware])
    app.router.add_post("/sensor", post_sensor)
    app.router.add_get("/sensor", get_sensor)
    return app
