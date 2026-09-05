"""极验行为验证 4.0（Geetest）服务端二次校验。

为什么需要二次校验
------------------
极验的前端验证（滑块/点选）只是**第一道门**：它产出的
``lot_number`` / ``captcha_output`` / ``pass_token`` / ``gen_time``
都是客户端可见的数据，脚本完全可以伪造一组字段声称"我已通过验证"。
因此必须由服务端拿着这批参数再去极验服务端问一次"这是否是一次真实的通过"，
即**二次校验**。只有二次校验通过才签发内部票据。

签名规则（极验官方）
--------------------
``sign_token = HMAC-SHA256(key=captcha_key, message=lot_number).hexdigest()``
—— 用验证私钥对**流水号**做 HMAC，证明这次校验请求确实来自持有私钥的一方。

容灾策略
--------
第三方服务不可达是**必然会发生的**事情（机房故障、网络抖动、额度耗尽）。
这里的处理由 ``GEETEST_FAIL_OPEN`` 决定：

* ``True``（默认）：校验接口不可达时**放行**，保证用户仍可注册，
  代价是这段时间内防刷能力下降。适合"可用性优先"的校园站点。
* ``False``：校验接口不可达时**拒绝**，宁可暂时无法注册也不放机器人进来。

两种选择都是合理的，关键是**显式配置**而不是意外行为，
且无论哪种都要打日志，便于事后发现"极验挂了多久"。
"""

from __future__ import annotations

import hashlib
import hmac
import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("auth.geetest")

_VALIDATE_URL = "https://gcaptcha4.geetest.com/validate"

# gen_time 允许的最大偏移（秒）。极验服务端本身也会校验 gen_time，
# 这里是额外一层：拦掉明显过期或被篡改的时间戳，避免为绕过而重放。
_GEN_TIME_SKEW = 600


def geetest_enabled() -> bool:
    """是否启用极验：captcha_id 与 captcha_key 都配置了才生效。

    任一为空都回退到自建拼图滑块 —— 保证"还没申请到极验账号"时站点依然可用。
    """
    return bool(settings.geetest_captcha_id and settings.geetest_captcha_key)


def captcha_provider() -> str:
    """当前实际生效的验证码提供方，供 /captcha/config 下发给前端。"""
    if settings.captcha_enabled and geetest_enabled():
        return "geetest"
    return "builtin"


def _sign_token(lot_number: str) -> str:
    """生成二次校验签名：HMAC-SHA256(key=验证私钥, msg=流水号)。"""
    return hmac.new(
        settings.geetest_captcha_key.encode("utf-8"),
        lot_number.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _gen_time_plausible(gen_time: str) -> bool:
    """校验 gen_time 是否为合理范围内的时间戳。

    解析失败时**放行**而非拒绝：时间戳格式由极验控制，
    若极验哪天换了格式，这里拒绝会导致全站注册不可用 ——
    让真正的判定权留在极验服务端，这里只挡明显的重放。
    """
    try:
        stamp = int(gen_time)
    except (TypeError, ValueError):
        return True
    return abs(time.time() - stamp) <= _GEN_TIME_SKEW


async def verify_geetest(
    lot_number: str,
    captcha_output: str,
    pass_token: str,
    gen_time: str,
) -> tuple[bool, str]:
    """向极验发起二次校验，返回 ``(是否通过, 说明)``。

    说明字段只用于日志，不回传给前端 —— 避免给攻击者提供
    "差在哪儿"的调试信息。
    """
    if not (lot_number and captcha_output and pass_token and gen_time):
        return False, "missing geetest params"
    if not _gen_time_plausible(gen_time):
        return False, "gen_time out of range"

    payload = {
        "lot_number": lot_number,
        "captcha_output": captcha_output,
        "pass_token": pass_token,
        "gen_time": gen_time,
        "sign_token": _sign_token(lot_number),
    }
    # captcha_id 放在 query 上：极验官方文档建议如此，
    # 便于其侧按 id 快速定位异常请求。
    url = f"{_VALIDATE_URL}?captcha_id={settings.geetest_captcha_id}"

    try:
        async with httpx.AsyncClient(timeout=settings.geetest_timeout) as client:
            resp = await client.post(url, data=payload)
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:  # 第三方可达性不可控，一律降级处理
        _logger.error(
            "geetest_unreachable",
            error=type(exc).__name__,
            detail=str(exc)[:200],
            fail_open=settings.geetest_fail_open,
        )
        # 容灾：不可达时按配置决定放行或拒绝
        return (settings.geetest_fail_open, "geetest unreachable")

    status = body.get("status")
    result = body.get("result")
    if status == "error":
        _logger.warning("geetest_error", code=body.get("code"), msg=body.get("msg"))
        return False, f"geetest error: {body.get('msg', 'unknown')}"

    ok = result == "success"
    _logger.info(
        "geetest_validated",
        ok=ok,
        reason=body.get("reason", ""),
        lot_number=lot_number[:12],
    )
    return ok, str(body.get("reason") or "")
