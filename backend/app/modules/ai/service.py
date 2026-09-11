"""AI 智能助手业务逻辑：功能开关 + OpenAI 标准接入 + 三层降级。

架构（对应 docs/AI集成规划方案.md 第三章）：
- **L0 开关层**：``app_config`` 表（key=``ai.feature``）优先于 school.yaml，后台可热改；
  默认 ``enabled=False``，未配置 Key 时前端隐藏全部 AI 入口，主流程零阻塞。
- **L1 能力层**：按 capability 粒度开关与降级。失败时 ``degradable=True`` 的能力
  走模板/规则降级（当前仅首页问候、内容预审）；``degradable=False`` 的能力
  （文案润色、课程画像、校园灵感）失败即友好提示——**绝不返回假数据**。
- **L2 模型层**：主模型失败（超时/429/5xx）依次尝试 ``fallback_models``，
  全部失败再回落到 L1；连续失败达阈值触发熔断，冷却期内直接降级，避免雪崩。

Key 只存在后端（``AI_API_KEY`` 环境变量优先，其次 school.yaml ``ai.api_key``），绝不下发浏览器。
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.admin.models import AppConfig
from app.modules.ai.models import AiDailyGreeting, AiGenerationLog
from app.modules.ai.provider import DEFAULT_BASE_URL, LLMError, OpenAICompatibleClient
from app.modules.ai.templates import (
    FOCUS,
    MOODS,
    PERIODS,
    VARIATION_HINTS,
    pick_greeting_template,
    sanitize_text,
    stable_hash,
)

_logger = get_logger("ai.service")

# AppConfig 存储 key
_AI_FEATURE_KEY = "ai.feature"

# 输入规模限制（防止 prompt 过长导致 token 消耗失控）
_MAX_REVIEW_TEXT_LEN = 500
_MAX_INSIGHT_TOPIC_LEN = 200
_MAX_CONTENT_LEN = 3000
_MAX_GREETING_LEN = 60

# 首页问候：每日生成上限（含「换一句」）与「换一句」次数上限
_GREETING_DAILY_LIMIT = 10
_GREETING_MAX_ATTEMPT = 5

# 允许的帖子分类（与前端分类保持一致，超出范围归入「其他」）
_POST_CATEGORIES = [
    "学习交流", "竞赛组队", "运动搭子", "考研考公",
    "实习就业", "社团活动", "生活服务", "二手交易", "其他",
]

# 能力默认值：degradable=True 表示失败可降级到模板/规则
DEFAULT_CAPABILITIES: dict[str, dict[str, bool]] = {
    "greeting": {"enabled": True, "degradable": True},
    "insights": {"enabled": True, "degradable": False},
    "item_description": {"enabled": True, "degradable": False},
    "course_summary": {"enabled": True, "degradable": False},
    "moderation": {"enabled": True, "degradable": True},
}

# 内容预审规则引擎兜底（LLM 不可用时保证不阻塞发布）
_BLOCK_WORDS = ["代考", "替考", "枪手", "假证", "刷单", "走私", "毒品", "枪支"]
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "二手交易": ["转让", "二手", "闲置", "低价", "出掉"],
    "考研考公": ["考研", "考公", "上岸", "复试", "行测"],
    "竞赛组队": ["组队", "队友", "竞赛", "国赛", "建模"],
    "运动搭子": ["跑步", "健身", "羽毛球", "篮球", "搭子"],
    "实习就业": ["实习", "简历", "面试", "校招", "内推"],
    "学习交流": ["课程", "期末", "复习", "选课", "学分"],
    "社团活动": ["社团", "招新", "活动", "晚会"],
    "生活服务": ["拼车", "快递", "维修", "租房"],
}


# ------------------------------------------------------------------
# 配置读写（DB 优先，school.yaml/env 兜底）
# ------------------------------------------------------------------


def _yaml_ai() -> dict[str, Any]:
    return settings.ai or {}


def _default_ai_config() -> dict:
    """school.yaml 中 ``ai.feature`` 段的默认值（DB 未配置时使用）。"""
    cfg = (_yaml_ai() or {}).get("feature", {}) or {}
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "model": str(cfg.get("model") or ""),
    }


async def get_ai_feature_config(db: AsyncSession) -> dict:
    """读取 AI 功能开关：DB（后台配置）优先，缺省回退 school.yaml。"""
    default = _default_ai_config()
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _AI_FEATURE_KEY)
    )
    if not cfg:
        return default
    merged = dict(default)
    merged.update({k: cfg.value.get(k, v) for k, v in default.items()})
    return merged


async def update_ai_feature_config(db: AsyncSession, data: dict) -> dict:
    """后台更新 AI 功能开关（写 DB，实时生效）。"""
    model = str(data.get("model") or _default_ai_config()["model"]).strip()
    payload = {
        "enabled": bool(data.get("enabled", False)),
        "model": model,
    }
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _AI_FEATURE_KEY)
    )
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=_AI_FEATURE_KEY, value=payload))
    await db.commit()
    _logger.info("admin_update_ai_feature", config=payload)
    return payload


def _get_api_key() -> str:
    """解析 API Key：``AI_API_KEY`` > 旧 ``GEMINI_API_KEY`` > school.yaml ``ai.api_key``。"""
    for env_name in ("AI_API_KEY", "GEMINI_API_KEY"):
        val = os.environ.get(env_name, "").strip()
        if val:
            return val
    return str((_yaml_ai() or {}).get("api_key") or "").strip()


def _static_runtime() -> dict[str, Any]:
    """yaml + 环境变量构成的运行时配置（不含 DB 开关）。"""
    y = _yaml_ai()
    cb = y.get("circuit_breaker") or {}
    return {
        "provider": str(y.get("provider") or "openai_compatible"),
        "base_url": (os.environ.get("AI_BASE_URL") or "").strip()
        or str(y.get("base_url") or DEFAULT_BASE_URL),
        "model": (os.environ.get("AI_MODEL") or "").strip()
        or str(y.get("model") or "deepseek-chat"),
        "fallback_models": [str(m) for m in (y.get("fallback_models") or []) if str(m)],
        "timeout_ms": int(y.get("timeout_ms") or 8000),
        "max_retries": max(0, int(y.get("max_retries") or 1)),
        "cb_threshold": int(cb.get("threshold") or 5),
        "cb_cooldown": int(cb.get("cooldown_sec") or 60),
        "capabilities": y.get("capabilities") or DEFAULT_CAPABILITIES,
    }


async def _runtime(db: AsyncSession) -> dict[str, Any]:
    """完整运行时配置 = 静态配置 + DB 开关（DB 可覆盖 enabled / model）。"""
    cfg = _static_runtime()
    feat = await get_ai_feature_config(db)
    cfg["enabled"] = bool(feat.get("enabled"))
    cfg["primary_model"] = str(feat.get("model") or "").strip() or cfg["model"]
    return cfg


# ------------------------------------------------------------------
# 熔断器（进程内，防雪崩）
# ------------------------------------------------------------------

_breaker: dict[str, float | int] = {"failures": 0, "open_until": 0.0}


def breaker_open() -> bool:
    """熔断器是否打开（打开期间直接走降级，不再打上游）。"""
    return time.monotonic() < float(_breaker["open_until"])


def reset_breaker() -> None:
    """重置熔断器（供测试与后台「手动恢复」使用）。"""
    _breaker["failures"] = 0
    _breaker["open_until"] = 0.0


def _breaker_record_failure(threshold: int, cooldown: int) -> None:
    _breaker["failures"] = int(_breaker["failures"]) + 1
    if int(_breaker["failures"]) >= max(1, threshold):
        _breaker["open_until"] = time.monotonic() + max(1, cooldown)
        _breaker["failures"] = 0
        _logger.warning("ai_circuit_open", cooldown_sec=cooldown)


# ------------------------------------------------------------------
# 大模型调用：模型链 + 重试 + 熔断
# ------------------------------------------------------------------


def _is_fatal(exc: LLMError) -> bool:
    """判断是否无需重试/换模型（Key 无效、模型不存在等 4xx，重试无意义）。"""
    msg = str(exc)
    if msg.startswith(("missing ", "bad response")):
        return True
    if msg.startswith("http 4") and "http 429" not in msg:
        return True
    return False


async def _call_llm(
    messages: list[dict[str, str]],
    *,
    cfg: dict[str, Any],
    temperature: float = 0.7,
    max_tokens: int = 512,
    json_mode: bool = False,
) -> str:
    """按「主模型 → fallback_models」依次尝试，带重试与熔断。

    Raises:
        LLMError: 全部模型均失败（调用方据此决定是否降级）。
    """
    if breaker_open():
        raise LLMError("circuit open")

    client = OpenAICompatibleClient(cfg["base_url"], _get_api_key(), cfg["timeout_ms"])
    models = [cfg["primary_model"]] + [
        m for m in cfg["fallback_models"] if m != cfg["primary_model"]
    ]
    last: LLMError | None = None
    for model in models:
        for attempt in range(cfg["max_retries"] + 1):
            try:
                text = await client.chat(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
            except LLMError as exc:
                last = exc
                _logger.warning(
                    "llm_call_failed", model=model, attempt=attempt, error=str(exc)
                )
                if _is_fatal(exc):
                    break
                if attempt < cfg["max_retries"]:
                    await asyncio.sleep(0.2 * (2**attempt))
                continue
            reset_breaker()
            return text
        if last is not None and _is_fatal(last):
            break

    _breaker_record_failure(cfg["cb_threshold"], cfg["cb_cooldown"])
    raise last or LLMError("all models failed")


def _messages(system: str, user: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# ------------------------------------------------------------------
# 能力校验与状态
# ------------------------------------------------------------------


async def _ensure_capability(db: AsyncSession, name: str) -> dict[str, Any]:
    """调用大模型前的统一前置校验（开关 → 能力 → Key）。"""
    cfg = await _runtime(db)
    if not cfg["enabled"]:
        raise BizError(ErrorCode.FORBIDDEN, "AI 智能助手功能暂未开放，敬请期待")
    cap = cfg["capabilities"].get(name) or {}
    if not cap.get("enabled", True):
        raise BizError(ErrorCode.FORBIDDEN, "该 AI 能力暂未开放，敬请期待")
    if not _get_api_key():
        raise BizError(ErrorCode.INTERNAL, "AI 服务未配置 API Key，请联系管理员")
    return cfg


async def get_ai_status(db: AsyncSession) -> dict:
    """AI 功能运行状态：能力级粒度，供前端按能力条件渲染。"""
    cfg = await _runtime(db)
    enabled = bool(cfg["enabled"])
    key_configured = bool(_get_api_key())
    degraded = breaker_open()

    capabilities = {
        name: {
            "available": bool(enabled and key_configured and cap.get("enabled", True)),
            "degraded": degraded,
        }
        for name, cap in cfg["capabilities"].items()
    }

    if not enabled:
        message = "AI 智能助手功能未开放"
    elif not key_configured:
        message = "AI 功能已开启，但服务端尚未配置 AI_API_KEY"
    elif degraded:
        message = "AI 服务暂时降级中，已切换备用方案"
    else:
        message = "AI 智能助手运行中"

    return {
        "enabled": enabled,
        "available": enabled and key_configured,
        "provider": cfg["provider"],
        "model": cfg["primary_model"],
        "capabilities": capabilities,
        "message": message,
    }


# ------------------------------------------------------------------
# 可观测性
# ------------------------------------------------------------------


async def _log_generation(
    db: AsyncSession,
    *,
    user_id: str | None,
    capability: str,
    model: str,
    source: str,
    latency_ms: int,
    ok: bool,
    detail: str = "",
) -> None:
    """记录一次调用。落库失败绝不向上抛（可观测性不能拖垮主流程）。"""
    try:
        db.add(
            AiGenerationLog(
                user_id=user_id,
                capability=capability,
                model=model,
                source=source,
                latency_ms=latency_ms,
                ok=ok,
                detail=detail[:255],
            )
        )
        await db.commit()
    except Exception as exc:  # pragma: no cover - 仅日志路径
        _logger.warning("ai_log_failed", error=str(exc))
        try:
            await db.rollback()
        except Exception:  # pragma: no cover
            pass


# ------------------------------------------------------------------
# 业务能力：校园灵感 / 物品润色 / 课程画像（均不可降级到假数据）
# ------------------------------------------------------------------


async def smart_campus_insights(db: AsyncSession, topic: str) -> str:
    """首页「今日校园智能灵感」。失败即友好提示，不返回假文案。"""
    cfg = await _ensure_capability(db, "insights")
    topic = topic.strip()[:_MAX_INSIGHT_TOPIC_LEN]
    started = time.monotonic()
    try:
        text = await _call_llm(
            _messages(
                "你是校园生活助手，熟悉大学学习、生活与社交场景，回复精炼。",
                f"请围绕校园话题「{topic}」，给大学生一段 60-120 字的实用建议，"
                "语气亲切自然，直接输出建议正文，不要任何前缀、标题或解释。",
            ),
            cfg=cfg,
            temperature=0.8,
            max_tokens=256,
        )
    except LLMError as exc:
        await _log_generation(
            db, user_id=None, capability="insights", model=cfg["primary_model"],
            source="fallback", latency_ms=_elapsed(started), ok=False, detail=str(exc),
        )
        raise BizError(ErrorCode.INTERNAL, "AI 服务暂时不可用，请稍后重试") from exc
    await _log_generation(
        db, user_id=None, capability="insights", model=cfg["primary_model"],
        source="llm", latency_ms=_elapsed(started), ok=True,
    )
    return text


async def generate_item_description(db: AsyncSession, title: str, category: str) -> str:
    """闲置发布页「AI 智能润色文案」。失败即友好提示，绝不返回假文案。"""
    cfg = await _ensure_capability(db, "item_description")
    started = time.monotonic()
    try:
        text = await _call_llm(
            _messages(
                "你是校园二手市集的文案助手，擅长写真实可信的闲置转让描述。",
                f"请为二手闲置物品「{title}」（分类：{category}）写一段 80-150 字的转让描述，"
                "需包含成色说明、交易方式（校内面交）等要素，语气真诚，"
                "直接输出描述正文，不要任何前缀或解释。",
            ),
            cfg=cfg,
            temperature=0.7,
            max_tokens=384,
        )
    except LLMError as exc:
        await _log_generation(
            db, user_id=None, capability="item_description",
            model=cfg["primary_model"], source="fallback",
            latency_ms=_elapsed(started), ok=False, detail=str(exc),
        )
        raise BizError(ErrorCode.INTERNAL, "AI 服务暂时不可用，请稍后重试") from exc
    await _log_generation(
        db, user_id=None, capability="item_description", model=cfg["primary_model"],
        source="llm", latency_ms=_elapsed(started), ok=True,
    )
    return text


async def summarize_course_reviews(db: AsyncSession, review_texts: list[str]) -> str:
    """课程详情页「AI 评价提炼」。失败即友好提示，绝不返回假画像。"""
    cfg = await _ensure_capability(db, "course_summary")
    joined = "\n".join(
        f"{i + 1}. {t.strip()[:_MAX_REVIEW_TEXT_LEN]}"
        for i, t in enumerate(review_texts[:50])
        if t and t.strip()
    )
    if not joined:
        raise BizError(ErrorCode.BAD_REQUEST, "暂无有效评价可供汇总")
    started = time.monotonic()
    try:
        text = await _call_llm(
            _messages(
                "你是选课助手，善于从学生评价中提炼客观、平衡的课程画像。",
                f"以下是同学们对同一门课程的评价：\n{joined}\n\n"
                "请综合以上评价，输出 80-150 字的课程画像，涵盖讲课质量、作业量与给分情况，"
                "直接输出结论正文，不要列举编号。",
            ),
            cfg=cfg,
            temperature=0.4,
            max_tokens=384,
        )
    except LLMError as exc:
        await _log_generation(
            db, user_id=None, capability="course_summary", model=cfg["primary_model"],
            source="fallback", latency_ms=_elapsed(started), ok=False, detail=str(exc),
        )
        raise BizError(ErrorCode.INTERNAL, "AI 服务暂时不可用，请稍后重试") from exc
    await _log_generation(
        db, user_id=None, capability="course_summary", model=cfg["primary_model"],
        source="llm", latency_ms=_elapsed(started), ok=True,
    )
    return text


def _elapsed(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


# ------------------------------------------------------------------
# 业务能力：内容预审（可降级到规则引擎）
# ------------------------------------------------------------------


async def categorize_content(db: AsyncSession, content: str) -> dict:
    """内容自动分类与安全预审：category / isSafe / summary / source。

    可降级：LLM 不可用时转规则引擎（关键词分类 + 敏感词），保证**不阻塞发布**。
    """
    cfg = await _runtime(db)
    content = content.strip()[:_MAX_CONTENT_LEN]
    if not cfg["enabled"]:
        raise BizError(ErrorCode.FORBIDDEN, "AI 智能助手功能暂未开放，敬请期待")
    cap = cfg["capabilities"].get("moderation") or {}
    if not cap.get("enabled", True):
        raise BizError(ErrorCode.FORBIDDEN, "该 AI 能力暂未开放，敬请期待")

    started = time.monotonic()
    if _get_api_key():
        try:
            raw = await _call_llm(
                _messages(
                    "你是社区内容审核助手，仅输出 JSON，不要输出其他任何文字。",
                    "请分析以下校园社区帖子内容，按 JSON 输出：\n"
                    f'{{"category": "从[{"、".join(_POST_CATEGORIES)}]中选择一个", '
                    '"isSafe": true或false, "summary": "15字以内摘要"}}\n\n'
                    f"帖子内容：\n{content}",
                ),
                cfg=cfg,
                temperature=0.1,
                max_tokens=256,
                json_mode=True,
            )
            result = _parse_categorize_result(raw, content)
            result["source"] = "llm"
            await _log_generation(
                db, user_id=None, capability="moderation", model=cfg["primary_model"],
                source="llm", latency_ms=_elapsed(started), ok=True,
            )
            return result
        except (LLMError, BizError) as exc:
            _logger.warning("ai_moderation_degrade", error=str(exc))

    await _log_generation(
        db, user_id=None, capability="moderation", model=cfg["primary_model"],
        source="rule", latency_ms=_elapsed(started), ok=True,
    )
    return _rule_moderation(content)


def _parse_categorize_result(raw: str, content: str) -> dict:
    """解析分类 JSON（容忍模型输出带 markdown 围栏）。"""
    candidates = [raw]
    stripped = raw.strip().strip("`")
    if stripped.lower().startswith("json"):
        stripped = stripped[4:]
    candidates.append(stripped.strip())
    for text in candidates:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        category = str(data.get("category") or "其他")
        if category not in _POST_CATEGORIES:
            category = "其他"
        return {
            "category": category,
            "isSafe": bool(data.get("isSafe", True)),
            "summary": str(data.get("summary") or content[:15]),
        }
    _logger.warning("ai_categorize_parse_failed", raw=raw[:200])
    raise BizError(ErrorCode.INTERNAL, "AI 分类结果解析失败")


def _rule_moderation(content: str) -> dict:
    """规则引擎兜底：关键词分类 + 敏感词命中即标记不安全。"""
    is_safe = not any(word in content for word in _BLOCK_WORDS)
    category, best_hits = "其他", 0
    for name, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in content)
        if hits > best_hits:
            best_hits, category = hits, name
    return {
        "category": category,
        "isSafe": is_safe,
        "summary": content[:15],
        "source": "rule",
    }


async def check_content_safety(db: AsyncSession, text: str) -> dict:
    """业务发布路径统一安全预审入口。

    与 ``/api/ai/categorize`` 的差异：
    * 受独立开关 ``content.moderation`` 控制，**不依赖 AI 总开关**；
    * 即使 AI 总开关关闭或 API Key 未配，仍走规则引擎兜底；
    * 返回结构化结果，供调用方决定拒绝/通过。

    返回 ``{"safe": bool, "action": "pass"|"reject"|"pending", "category": str}``。
    """
    from app.modules.admin.service import get_content_moderation_config

    cfg = await get_content_moderation_config(db)
    if not cfg["enabled"]:
        return {"safe": True, "action": "pass", "category": ""}

    content = text.strip()[:_MAX_CONTENT_LEN]
    try:
        result = await categorize_content(db, content)
    except BizError as exc:
        # AI 总开关关闭或 moderation 能力关闭时，降级为纯规则引擎
        _logger.warning("content_safety_ai_disabled_fallback_rule", error=str(exc))
        result = _rule_moderation(content)

    if not result.get("isSafe", True):
        return {"safe": False, "action": cfg["action"], "category": result.get("category", "")}
    return {"safe": True, "action": "pass", "category": result.get("category", "")}


# ------------------------------------------------------------------
# 业务能力：首页问候（可降级到模板，永不阻塞）
# ------------------------------------------------------------------


def _period_of(hour: int) -> str:
    if 5 <= hour < 9:
        return "early"
    if 9 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "noon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def _term_phase(month: int) -> str:
    if month in (7, 8):
        return "暑假"
    if month == 2:
        return "寒假"
    if 3 <= month <= 6:
        return "春季学期"
    return "秋季学期"


def _weekday_cn(day: date) -> str:
    return "一二三四五六日"[day.weekday()]


def _greeting_slot(user_id: str, day_str: str, mood: str, focus: str) -> list:
    return [
        AiDailyGreeting.user_id == user_id,
        AiDailyGreeting.day == day_str,
        AiDailyGreeting.mood == mood,
        AiDailyGreeting.focus == focus,
    ]


async def generate_greeting(
    db: AsyncSession,
    *,
    user_id: str,
    mood: str = "",
    focus: str = "",
    client_seed: str = "",
    regenerate: bool = False,
    now: datetime | None = None,
) -> dict:
    """首页「每日问候 · 微采集」。

    降级策略：开关关闭 / 未配 Key / 熔断中 / 上游失败 / 超频 —— **一律返回模板**，
    ``source="fallback"``，前端正常渲染（不报错、不阻塞主流程）。
    """
    now = now or datetime.now()
    day_str = now.date().isoformat()
    period = _period_of(now.hour)

    # 白名单归一化（防 prompt 注入）
    mood = mood if mood in MOODS else ""
    focus = focus if focus in FOCUS else ""

    def _template(attempt: int = 0) -> dict:
        seed = stable_hash(
            f"{user_id}:{day_str}:{mood}:{focus}:{attempt}:{client_seed}"
        )
        text, emoji = pick_greeting_template(
            mood=mood, focus=focus, period=period, seed=seed
        )
        return _out(text, emoji, "fallback", period, mood, focus, attempt)

    cfg = await _runtime(db)
    cap = cfg["capabilities"].get("greeting") or {}
    usable = (
        cfg["enabled"]
        and bool(cap.get("enabled", True))
        and bool(_get_api_key())
        and not breaker_open()
    )
    if not usable:
        return _template()

    attempt = 0
    if regenerate:
        max_attempt = await db.scalar(
            select(func.coalesce(func.max(AiDailyGreeting.attempt), -1)).where(
                *_greeting_slot(user_id, day_str, mood, focus)
            )
        )
        # 注意：max_attempt 可能为 0，不能用 `or` 兜底（0 是 falsy）
        attempt = 0 if max_attempt is None else int(max_attempt) + 1
        if attempt >= _GREETING_MAX_ATTEMPT:
            row = await db.scalar(
                select(AiDailyGreeting)
                .where(*_greeting_slot(user_id, day_str, mood, focus))
                .order_by(AiDailyGreeting.attempt.desc())
            )
            if row:
                return _row_to_out(row)

    cached = await db.scalar(
        select(AiDailyGreeting).where(
            *_greeting_slot(user_id, day_str, mood, focus),
            AiDailyGreeting.attempt == attempt,
        )
    )
    if cached:
        return _row_to_out(cached)

    used = await db.scalar(
        select(func.count())
        .select_from(AiDailyGreeting)
        .where(AiDailyGreeting.user_id == user_id, AiDailyGreeting.day == day_str)
    )
    if int(used or 0) >= _GREETING_DAILY_LIMIT:
        return _template(attempt)

    hint = VARIATION_HINTS[
        stable_hash(f"{user_id}:{day_str}:{mood}:{focus}:{attempt}:{client_seed}")
        % len(VARIATION_HINTS)
    ]
    ctx = (
        f"时间：周{_weekday_cn(now.date())} {PERIODS.get(period, '')}，{_term_phase(now.month)}\n"
        f"状态：{MOODS.get(mood, '未采集')}\n"
        f"今日重点：{FOCUS.get(focus, '未采集')}\n"
        f"表达手法（必须体现）：{hint}\n"
    )
    started = time.monotonic()
    try:
        raw = await _call_llm(
            _messages(
                "你是校园助手，为大学生生成今日问候。只输出 JSON，不要其他文字。",
                f"{ctx}\n约束：40-60 字，中文，口语化，不说教，不空洞鸡汤，"
                '必须体现上述表达手法。\n输出 JSON：{"text":"...","emoji":"单个 emoji"}',
            ),
            cfg=cfg,
            temperature=1.0,
            max_tokens=128,
            json_mode=True,
        )
        parsed = _parse_greeting(raw)
        if not parsed:
            raise LLMError("bad greeting json")
        text = sanitize_text(parsed["text"], _MAX_GREETING_LEN)
        emoji = parsed["emoji"][:4]
        source = "llm"
    except LLMError as exc:
        _logger.warning("ai_greeting_degrade", error=str(exc))
        fb = _template(attempt)
        text, emoji, source = fb["text"], fb["emoji"], "fallback"

    await _log_generation(
        db, user_id=user_id, capability="greeting", model=cfg["primary_model"],
        source=source, latency_ms=_elapsed(started), ok=(source == "llm"),
    )
    await _upsert_greeting(
        db, user_id=user_id, day=day_str, mood=mood, focus=focus,
        attempt=attempt, period=period, text=text, emoji=emoji, source=source,
    )
    return _out(text, emoji, source, period, mood, focus, attempt)


def _out(
    text: str, emoji: str, source: str, period: str,
    mood: str, focus: str, attempt: int,
) -> dict:
    return {
        "text": text,
        "emoji": emoji,
        "source": source,
        "period": period,
        "mood": mood,
        "focus": focus,
        "attempt": attempt,
    }


def _parse_greeting(raw: str) -> dict | None:
    """解析问候 JSON（容忍 markdown 围栏）。"""
    stripped = raw.strip().strip("`")
    candidates = [raw, stripped]
    if stripped.lower().startswith("json"):
        candidates.append(stripped[4:].strip())
    for text in candidates:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and str(data.get("text") or "").strip():
            return {
                "text": str(data["text"]).strip(),
                "emoji": str(data.get("emoji") or "✨").strip(),
            }
    return None


async def _upsert_greeting(db: AsyncSession, **fields: Any) -> None:
    """写入当日问候缓存（存在则覆盖）。落库失败不影响响应。"""
    try:
        row = await db.scalar(
            select(AiDailyGreeting).where(
                *_greeting_slot(
                    fields["user_id"], fields["day"], fields["mood"], fields["focus"]
                ),
                AiDailyGreeting.attempt == fields["attempt"],
            )
        )
        if row:
            row.text = fields["text"]
            row.emoji = fields["emoji"]
            row.source = fields["source"]
            row.period = fields["period"]
        else:
            db.add(AiDailyGreeting(**fields))
        await db.commit()
    except Exception as exc:  # pragma: no cover - 仅缓存路径
        _logger.warning("ai_greeting_cache_failed", error=str(exc))
        try:
            await db.rollback()
        except Exception:  # pragma: no cover
            pass


def _row_to_out(row: AiDailyGreeting) -> dict:
    return _out(
        row.text, row.emoji, row.source, row.period, row.mood, row.focus, row.attempt
    )
