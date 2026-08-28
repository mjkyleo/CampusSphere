"""网关中间件：鉴权 / 限流 / 请求 ID / 请求日志。

- 解析 Authorization: Bearer <access>，校验签名+黑名单，写入 request.state.user_id
- 注入 X-Request-ID，贯穿 structlog
- 基于 Redis 的简单令牌桶限流（超阈返回 429）
- 登录/公开接口（白名单）放行
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions import ErrorCode
from app.core.logging import bind_request, clear_request, get_logger
from app.core.redis import redis_incr
from app.core.response import ApiResponse
from app.core.security import decode_token, is_token_revoked

_logger = get_logger("gateway")

PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/email-register",
    "/api/auth/phone-login",
    "/api/auth/refresh",
    "/api/auth/send-code",
    "/api/auth/verify-email",
    "/api/auth/email-config",
    "/api/auth/wechat/callback",
    "/api/auth/qq/callback",
    "/api/admin/login",
    "/api/admin/discover",
    "/api/ai/status",
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# 公开读取接口：未登录用户可浏览校园信息广场、课程、二手、组队、食堂、分享、兼职
PUBLIC_GET_PREFIXES = {
    "/api/items",
    "/api/courses",
    "/api/teams",
    "/api/canteens",
    "/api/shares",
    "/api/jobs",
}


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


class GatewayMiddleware(BaseHTTPMiddleware):
    """统一网关中间件。"""

    def __init__(self, app, rate_limit_per_minute: int = 120) -> None:
        super().__init__(app)
        self.rate_limit_per_minute = rate_limit_per_minute

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        bind_request(request_id)

        # 请求日志
        _logger.info("request_start", method=request.method, path=request.url.path)

        # 限流
        client = request.client.host if request.client else "unknown"
        limit_key = f"ratelimit:{client}:{int(time.time() // 60)}"
        try:
            count = await redis_incr(limit_key, ttl=60)
            if count and count > self.rate_limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content=ApiResponse(
                        code=ErrorCode.TOO_MANY_REQUESTS,
                        message="请求过于频繁，请稍后再试",
                    ).model_dump(),
                )
        except Exception:  # noqa: BLE001
            pass  # 限流失败不阻断业务

        # 认证/验证码接口独立严格限流（防爆破与刷接口），每 IP 每分钟 10 次。
        _auth_strict_paths = {
            "/api/auth/login",
            "/api/auth/phone-login",
            "/api/auth/email-register",
            "/api/auth/send-code",
            "/api/auth/verify-email",
        }
        if request.url.path in _auth_strict_paths:
            auth_limit_key = f"ratelimit:auth:{client}:{int(time.time() // 60)}"
            try:
                acount = await redis_incr(auth_limit_key, ttl=60)
                if acount and acount > 10:
                    return JSONResponse(
                        status_code=429,
                        content=ApiResponse(
                            code=ErrorCode.TOO_MANY_REQUESTS,
                            message="操作过于频繁，请稍后再试",
                        ).model_dump(),
                    )
            except Exception:  # noqa: BLE001
                pass

        # 管理端网关隐藏：/api/admin/*（discover 除外）未携带有效网关令牌时一律 404，
        # 让未授权探测者看起来像接口不存在（先于鉴权执行，避免泄露 401）。
        _path = request.url.path
        if _path.startswith("/api/admin/") and _path != "/api/admin/discover":
            from app.modules.admin.gateway import gateway_enforced, verify_gateway_token

            if gateway_enforced() and not verify_gateway_token(request.headers.get("X-Admin-Gateway")):
                return JSONResponse(
                    status_code=404,
                    content=ApiResponse(
                        code=ErrorCode.NOT_FOUND, message="资源不存在", data=None
                    ).model_dump(),
                )

        # 鉴权
        path = request.url.path
        is_public = (
            path in PUBLIC_PATHS
            or path.startswith("/ws")
            or (request.method == "GET" and any(path.startswith(prefix) for prefix in PUBLIC_GET_PREFIXES))
        )
        if not is_public:
            token = _extract_token(request)
            if not token:
                clear_request()
                return JSONResponse(
                    status_code=401,
                    content=ApiResponse(
                        code=ErrorCode.UNAUTHORIZED, message="缺少访问令牌"
                    ).model_dump(),
                )
            try:
                payload = decode_token(token)
                if payload.get("type") != "access":
                    raise ValueError("not access token")
                if await is_token_revoked(token):
                    raise ValueError("revoked")
                request.state.user_id = payload["sub"]
                bind_request(request_id, user_id=payload["sub"])
            except Exception as exc:  # noqa: BLE001
                _logger.warning("auth_failed", error=str(exc))
                clear_request()
                return JSONResponse(
                    status_code=401,
                    content=ApiResponse(
                        code=ErrorCode.UNAUTHORIZED, message="令牌无效或已失效"
                    ).model_dump(),
                )

        start = time.time()
        response = await call_next(request)
        cost = round((time.time() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        _logger.info("request_end", status=response.status_code, cost_ms=cost)
        clear_request()
        return response
