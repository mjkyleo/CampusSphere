"""AI 智能助手业务逻辑：功能开关（AppConfig）+ Gemini REST 调用。

设计要点：
- 功能开关走 ``app_config`` 表（key=``ai.feature``），DB 值优先于 school.yaml
  默认值，与管理端「邮箱注册配置」「发布审核开关」同一套机制，后台改动实时生效。
- 默认 ``enabled=False``：个人开发者无大模型 API 额度时不向前端暴露 AI 入口，
  从根源上替代原先前端硬编码假文案的演示行为。
- Gemini 通过 REST（httpx）直调，不引入 google-generativeai SDK；
  API Key 仅存在后端（环境变量 ``GEMINI_API_KEY`` 优先，其次 school.yaml ``ai.api_key``），
  绝不下发到浏览器。
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.admin.models import AppConfig

_logger = get_logger("ai.service")

# AppConfig 存储 key
_AI_FEATURE_KEY = "ai.feature"

# Gemini REST 端点
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# 允许的帖子分类（与前端分类保持一致，超出范围归入「其他」）
_POST_CATEGORIES = [
    "学习交流", "竞赛组队", "运动搭子", "考研考公",
    "实习就业", "社团活动", "生活服务", "二手交易", "其他",
]

# 输入规模限制（防止 prompt 过长导致 token 消耗失控）
_MAX_REVIEW_TEXT_LEN = 500
_MAX_INSIGHT_TOPIC_LEN = 200
_MAX_CONTENT_LEN = 3000


# ------------------------------------------------------------------
# 配置读写（DB 优先，school.yaml 兜底）
# ------------------------------------------------------------------


def _default_ai_config() -> dict:
    """school.yaml 中 ``ai`` 段的默认值。"""
    cfg = (settings.ai or {}).get("feature", {}) or {}
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "model": str(cfg.get("model") or "gemini-2.0-flash"),
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
        "model": model or "gemini-2.0-flash",
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
    """解析 Gemini API Key：环境变量优先，其次 school.yaml。"""
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    return str((settings.ai or {}).get("api_key") or "").strip()


async def get_ai_status(db: AsyncSession) -> dict:
    """AI 功能运行状态（供公开状态端点与管理后台展示）。"""
    cfg = await get_ai_feature_config(db)
    enabled = bool(cfg.get("enabled"))
    key_configured = bool(_get_api_key())
    if not enabled:
        message = "AI 智能助手功能未开放"
    elif not key_configured:
        message = "AI 功能已开启，但服务端尚未配置 GEMINI_API_KEY"
    else:
        message = "AI 智能助手运行中"
    return {
        "enabled": enabled,
        "available": enabled and key_configured,
        "message": message,
    }


async def _ensure_ai_ready(db: AsyncSession) -> dict:
    """调用大模型前的统一前置校验。

    开关未开 / Key 未配置均抛业务异常；通过则返回当前配置（含 model 名）。
    """
    cfg = await get_ai_feature_config(db)
    if not cfg.get("enabled"):
        raise BizError(ErrorCode.FORBIDDEN, "AI 智能助手功能暂未开放，敬请期待")
    if not _get_api_key():
        raise BizError(ErrorCode.INTERNAL, "AI 服务未配置 API Key，请联系管理员")
    return cfg


# ------------------------------------------------------------------
# Gemini REST 调用
# ------------------------------------------------------------------


async def _call_gemini(
    prompt: str,
    *,
    model: str = "gemini-2.0-flash",
    system_instruction: str = "",
    temperature: float = 0.7,
    max_output_tokens: int = 512,
    json_mode: bool = False,
) -> str:
    """调用 Gemini generateContent 并返回纯文本结果。

    Raises:
        BizError: 网络/配额/响应解析失败等一切上游异常（统一转译为友好提示）。
    """
    api_key = _get_api_key()
    if not api_key:
        raise BizError(ErrorCode.INTERNAL, "AI 服务未配置 API Key，请联系管理员")

    body: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    url = f"{_GEMINI_BASE}/{model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params={"key": api_key}, json=body)
    except httpx.HTTPError as exc:
        _logger.warning("gemini_request_failed", error=str(exc))
        raise BizError(ErrorCode.INTERNAL, "AI 服务连接失败，请稍后重试") from exc

    if resp.status_code != 200:
        # 429=配额耗尽 403=Key 无效等，避免把原始报错直接透给用户
        _logger.warning(
            "gemini_api_error", status=resp.status_code, body=resp.text[:500]
        )
        raise BizError(ErrorCode.INTERNAL, "AI 服务暂时不可用，请稍后重试")

    try:
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError) as exc:
        _logger.warning("gemini_response_parse_failed", error=str(exc))
        raise BizError(ErrorCode.INTERNAL, "AI 服务返回异常，请稍后重试") from exc
    return (text or "").strip()


# ------------------------------------------------------------------
# 业务能力
# ------------------------------------------------------------------


async def smart_campus_insights(db: AsyncSession, topic: str) -> str:
    """首页「今日校园智能灵感」：围绕主题生成一段简短校园建议。"""
    cfg = await _ensure_ai_ready(db)
    topic = topic.strip()[:_MAX_INSIGHT_TOPIC_LEN]
    return await _call_gemini(
        f"请围绕校园话题「{topic}」，给大学生一段 60-120 字的实用建议，语气亲切自然，"
        "直接输出建议正文，不要任何前缀、标题或解释。",
        model=cfg["model"],
        system_instruction="你是校园生活助手，熟悉大学学习、生活与社交场景，回复精炼。",
        temperature=0.8,
        max_output_tokens=256,
    )


async def generate_item_description(db: AsyncSession, title: str, category: str) -> str:
    """闲置发布页「AI 智能润色文案」：生成一段二手物品转让描述。"""
    cfg = await _ensure_ai_ready(db)
    return await _call_gemini(
        f"请为二手闲置物品「{title}」（分类：{category}）写一段 80-150 字的转让描述，"
        "需包含成色说明、交易方式（校内面交）等要素，语气真诚，"
        "直接输出描述正文，不要任何前缀或解释。",
        model=cfg["model"],
        system_instruction="你是校园二手市集的文案助手，擅长写真实可信的闲置转让描述。",
        temperature=0.7,
        max_output_tokens=384,
    )


async def summarize_course_reviews(db: AsyncSession, review_texts: list[str]) -> str:
    """课程详情页「AI 评价提炼」：汇总多条评课内容为一段画像。"""
    cfg = await _ensure_ai_ready(db)
    joined = "\n".join(
        f"{i + 1}. {t.strip()[:_MAX_REVIEW_TEXT_LEN]}"
        for i, t in enumerate(review_texts[:50])
        if t and t.strip()
    )
    if not joined:
        raise BizError(ErrorCode.BAD_REQUEST, "暂无有效评价可供汇总")
    return await _call_gemini(
        f"以下是同学们对同一门课程的评价：\n{joined}\n\n"
        "请综合以上评价，输出 80-150 字的课程画像，涵盖讲课质量、作业量与给分情况，"
        "直接输出结论正文，不要列举编号。",
        model=cfg["model"],
        system_instruction="你是选课助手，善于从学生评价中提炼客观、平衡的课程画像。",
        temperature=0.4,
        max_output_tokens=384,
    )


async def categorize_content(db: AsyncSession, content: str) -> dict:
    """内容自动分类与安全预审：返回 category / isSafe / summary。"""
    cfg = await _ensure_ai_ready(db)
    content = content.strip()[:_MAX_CONTENT_LEN]
    categories = "、".join(_POST_CATEGORIES)
    raw = await _call_gemini(
        f"请分析以下校园社区帖子内容，按 JSON 输出：\n"
        f'{{"category": "从[{categories}]中选择一个", "isSafe": true或false, "summary": "15字以内摘要"}}\n\n'
        f"帖子内容：\n{content}",
        model=cfg["model"],
        system_instruction="你是社区内容审核助手，仅输出 JSON，不要输出其他任何文字。",
        temperature=0.1,
        max_output_tokens=256,
        json_mode=True,
    )
    return _parse_categorize_result(raw, content)


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
