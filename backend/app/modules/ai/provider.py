"""大模型接入层：OpenAI Chat Completions 标准（httpx 直调，不引入任何 SDK）。

设计要点：
- **协议标准化**：只认 ``POST {base_url}/chat/completions`` +``Bearer`` 鉴权，
  因此 OpenAI / DeepSeek / 通义 Qwen / Kimi / 智谱 GLM / Groq / 本地 Ollama、vLLM
  可零改动切换，仅改 ``ai.base_url`` 与 ``ai.model``。
- **不引入 SDK**：避免依赖树膨胀与版本锁定（与既有 httpx 直调思路一致）。
- **只抛 ``LLMError``**：网络/超时/配额/解析失败统一收敛，由 ``service`` 转译为业务异常，
  上层据此决定是否降级。
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger

_logger = get_logger("ai.provider")

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


class LLMError(RuntimeError):
    """上游大模型调用失败。message 仅用于内部日志，不直接下发给用户。"""


class OpenAICompatibleClient:
    """OpenAI 兼容端点的最小客户端。"""

    def __init__(self, base_url: str = "", api_key: str = "", timeout_ms: int = 8000):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = (api_key or "").strip()
        self.timeout = max(1.0, (timeout_ms or 8000) / 1000)

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        json_mode: bool = False,
    ) -> str:
        """发起一次对话，返回 assistant 消息正文。

        Raises:
            LLMError: 未配置 Key / 网络失败 / 非 200 / 响应结构异常。
        """
        if not self.api_key:
            raise LLMError("missing api key")
        if not model:
            raise LLMError("missing model")

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            # 部分厂商（如 DeepSeek/OpenAI）要求提示词中出现 "json" 字样才允许该模式，
            # 调用方 prompt 已包含 JSON 说明，这里仅设置响应格式。
            body["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.endpoint,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
        except httpx.HTTPError as exc:
            raise LLMError(f"network error: {exc}") from exc

        if resp.status_code != 200:
            _logger.warning(
                "llm_http_error",
                status=resp.status_code,
                model=model,
                body=resp.text[:300],
            )
            raise LLMError(f"http {resp.status_code}")

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError(f"bad response: {exc}") from exc
        return (content or "").strip()
