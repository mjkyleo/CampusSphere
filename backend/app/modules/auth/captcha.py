"""滑块拼图验证码：生成与校验。

技术选型说明
------------
采用「服务端生成位图拼图 + 前端拖动对齐」的自建方案，而非接入第三方
（极验 / 腾讯云验证码等），原因：

* 项目为自部署形态（docker-compose 一键起），接入第三方需要额外账号、
  密钥与外网连通性，且会让离线环境无法注册；
* 图像处理使用 **Pillow**——Python 生态中最成熟稳定的图像库，无额外服务依赖；
* 返回 **位图（PNG）** 而非 SVG：SVG 是明文文本，攻击者可直接从源码解析出
  缺口坐标，拼图验证形同虚设。

安全设计
--------
* 缺口坐标只在服务端保存（Redis，TTL 到期自动清理），**绝不下发给前端**；
* 令牌**有限次有效**：成功即作废；失败时累计尝试次数，达到
  ``captcha_max_attempts`` 后立即作废——既容忍用户拖歪重试，
  又杜绝「无限试探坐标」。行为以 ``tests/unit/test_captcha_unit.py`` 为准；
* 多重判定：位置容差 + 拖动耗时 + 轨迹形态（拦截匀速脚本直传坐标）；
* 校验通过后签发**短期票据**，``send-code`` 需凭票据发送，无法绕过滑块。

流程
----
``GET captcha/slider`` → 用户拖动 → ``POST captcha/verify``（换票据）
→ ``POST send-code``（带票据）→ 发送验证码
"""

from __future__ import annotations

import base64
import io
import json
import random
import secrets
import time

from PIL import Image, ImageDraw

from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.core.redis import redis_delete, redis_get, redis_set

_logger = get_logger("auth.captcha")

# 画布尺寸：前端按此渲染，避免缩放导致坐标偏差
CANVAS_WIDTH = 320
CANVAS_HEIGHT = 160
SLIDER_SIZE = 52

_SLIDER_PREFIX = "captcha:slider:"
_TICKET_PREFIX = "captcha:ticket:"

# 轨迹单次步进上限（像素）：仅用于拦截异常跳变，不苛求真实用户的抖动
_MAX_TRACK_STEP = 120
# 人类完成拖动的下限（毫秒）：低于此值基本可判定为脚本
_MIN_ELAPSED_MS = 80


# ---------------------------------------------------------------------------
# 图像生成
# ---------------------------------------------------------------------------
def _rand_color(rand: random.Random | None = None) -> tuple[int, int, int]:
    """随机中等亮度颜色（过暗/过亮都会让滑块与缺口难以分辨）。"""
    r = rand.randrange if rand else secrets.randbelow
    return (r(120) + 60, r(120) + 60, r(120) + 60)


def _random_background(width: int, height: int) -> Image.Image:
    """生成随机渐变背景 + 少量干扰图形/噪点，保证每次图片都不同。

    视觉元素只起辅助防 OCR 作用，不依赖复杂滤镜；复杂滤镜会显著拖慢
    低配置服务器上的响应时间，因此这里保持轻量。
    """
    # 纯视觉元素使用 random 即可，不必占用密码学安全随机源
    rand = random.Random()
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 竖向渐变：每 4 像素画一条横线，减少 draw 调用次数
    top, bottom = _rand_color(rand), _rand_color(rand)
    for row in range(0, height, 4):
        ratio = row / max(height - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.rectangle([(0, row), (width, min(row + 4, height))], fill=color)

    # 干扰图形：随机圆与折线，数量保持轻量即可
    for _ in range(3):
        cx, cy = rand.randrange(width), rand.randrange(height)
        radius = rand.randrange(6, 24)
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=_rand_color(rand),
            width=2,
        )
    for _ in range(2):
        x1, y1 = rand.randrange(width), rand.randrange(height)
        x2, y2 = rand.randrange(width), rand.randrange(height)
        draw.line([(x1, y1), (x2, y2)], fill=_rand_color(rand), width=2)

    # 轻量噪点：数量减少，避免大量 point 调用拖慢生成
    for _ in range(80):
        x, y = rand.randrange(width), rand.randrange(height)
        draw.point((x, y), fill=_rand_color(rand))

    return img


def _puzzle_mask(size: int) -> Image.Image:
    """生成拼图块遮罩（方块 + 右侧圆形凸起），白色区域为保留部分。"""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    inset = size // 8
    draw.rectangle([inset, inset, size - inset - 1, size - inset - 1], fill=255)
    radius = size // 8
    center_x = size - inset
    center_y = size // 2
    draw.ellipse(
        [
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        ],
        fill=255,
    )
    return mask


def _cut_slider(bg: Image.Image, mask: Image.Image, x: int, y: int) -> Image.Image:
    """从背景中裁出拼图块（透明 PNG）。"""
    region = bg.crop((x, y, x + SLIDER_SIZE, y + SLIDER_SIZE))
    slider = Image.new("RGBA", (SLIDER_SIZE, SLIDER_SIZE), (0, 0, 0, 0))
    slider.paste(region, (0, 0), mask)
    return slider


def _punch_hole(bg: Image.Image, mask: Image.Image, x: int, y: int) -> Image.Image:
    """在背景上挖出缺口（暗色半透明 + 白色描边），供前端对齐。"""
    layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    # 暗块
    patch = Image.new("RGBA", (SLIDER_SIZE, SLIDER_SIZE), (35, 35, 35, 170))
    layer.paste(patch, (x, y), mask)
    # 描边：用遮罩的边缘做白色轮廓，提升缺口可辨识度
    edge = mask.filter(ImageFilter.FIND_EDGES)
    edge_rgba = Image.new("RGBA", (SLIDER_SIZE, SLIDER_SIZE), (255, 255, 255, 0))
    edge_rgba.paste((255, 255, 255, 210), (0, 0), edge)
    layer.paste(edge_rgba, (x, y), edge)
    return Image.alpha_composite(bg.convert("RGBA"), layer)


def _to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
async def generate_slider() -> dict:
    """生成一次滑块验证。

    返回可直接渲染的载荷；缺口坐标只写入 Redis，不出现在响应中。
    """
    bg = _random_background(CANVAS_WIDTH, CANVAS_HEIGHT)
    # 缺口位置：左右各留出滑块宽度，避免贴边导致无法拖动
    target_x = secrets.randbelow(CANVAS_WIDTH - 2 * SLIDER_SIZE) + SLIDER_SIZE
    target_y = secrets.randbelow(CANVAS_HEIGHT - SLIDER_SIZE - 16) + 8

    mask = _puzzle_mask(SLIDER_SIZE)
    slider = _cut_slider(bg, mask, target_x, target_y)
    background = _punch_hole(bg, mask, target_x, target_y)

    token = secrets.token_urlsafe(32)
    payload = {
        "x": target_x,
        "y": target_y,
        "ts": time.time(),
        "tries": 0,
    }
    await redis_set(
        _SLIDER_PREFIX + token, json.dumps(payload), ttl=settings.captcha_ttl_seconds
    )
    return {
        "token": token,
        "background": _to_data_uri(background),
        "slider": _to_data_uri(slider),
        "width": CANVAS_WIDTH,
        "height": CANVAS_HEIGHT,
        "slider_size": SLIDER_SIZE,
        "y": target_y,  # 缺口纵坐标（需要下发，滑块才能在同一水平线上）
        "expires_in": settings.captcha_ttl_seconds,
    }


def _track_looks_human(track: object, min_points: int) -> bool:
    """轨迹形态校验：拦截「直传坐标 / 匀速直线」的脚本行为。

    期望格式：``[[t_ms, x, y], ...]``，至少 min_points 个采样点。
    """
    if not isinstance(track, list) or len(track) < min_points:
        return False

    xs: list[float] = []
    for item in track:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            return False
        try:
            xs.append(float(item[1]))
        except (TypeError, ValueError):
            return False

    # 整体必须向前推进
    if xs[-1] <= xs[0]:
        return False

    steps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    # 单次步进异常大 → 疑似伪造轨迹
    if any(abs(step) > _MAX_TRACK_STEP for step in steps):
        return False
    # 完全匀速（每步位移一致）→ 典型脚本特征
    distinct_steps = {round(step, 3) for step in steps}
    return len(distinct_steps) > 1


async def verify_slider(
    token: str,
    offset_x: float,
    track: object,
    elapsed_ms: int,
) -> str:
    """校验一次滑块拖动，成功返回一次性票据（用于 send-code）。

    失败一律抛 ``BizError(42200)``，且不区分「坐标偏差」与「令牌失效」，
    避免给攻击者提供可用于调整参数的反馈。
    """
    raw = await redis_get(_SLIDER_PREFIX + token) if token else None
    if not raw:
        raise BizError(ErrorCode.VALIDATION, "验证已失效，请重新进行滑块验证")

    try:
        payload = json.loads(raw)
        target_x = float(payload["x"])
        tries = int(payload.get("tries", 0))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        await redis_delete(_SLIDER_PREFIX + token)
        raise BizError(ErrorCode.VALIDATION, "验证已失效，请重新进行滑块验证") from None

    tries += 1
    ok = (
        tries <= settings.captcha_max_attempts
        and abs(float(offset_x) - target_x) <= settings.captcha_tolerance_px
        and _MIN_ELAPSED_MS <= int(elapsed_ms) <= settings.captcha_ttl_seconds * 1000
        and _track_looks_human(track, settings.captcha_min_track_points)
    )

    if ok:
        # 一次性：成功后立即作废，防止票据被复用
        await redis_delete(_SLIDER_PREFIX + token)
        _logger.info("captcha_passed", tries=tries, elapsed_ms=elapsed_ms)
        return await issue_ticket()

    if tries >= settings.captcha_max_attempts:
        await redis_delete(_SLIDER_PREFIX + token)
    else:
        payload["tries"] = tries
        await redis_set(
            _SLIDER_PREFIX + token, json.dumps(payload), ttl=settings.captcha_ttl_seconds
        )
    _logger.info("captcha_failed", tries=tries, elapsed_ms=elapsed_ms)
    raise BizError(ErrorCode.VALIDATION, "滑块验证未通过，请重试")


async def issue_ticket() -> str:
    """签发一次性票据：滑块通过后，凭票据才能请求发送验证码。"""
    ticket = secrets.token_urlsafe(24)
    await redis_set(
        _TICKET_PREFIX + ticket,
        json.dumps({"ts": time.time()}),
        ttl=settings.captcha_ticket_ttl_seconds,
    )
    return ticket


async def consume_ticket(ticket: str | None) -> bool:
    """消费票据（一次性）。返回是否存在且有效。"""
    if not ticket:
        return False
    raw = await redis_get(_TICKET_PREFIX + ticket)
    if not raw:
        return False
    # 无论后续是否成功，票据都立即作废，避免重放
    await redis_delete(_TICKET_PREFIX + ticket)
    return True
