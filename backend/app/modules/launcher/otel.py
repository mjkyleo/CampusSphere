"""OpenTelemetry 初始化（可选；缺失依赖时静默跳过）。"""

from __future__ import annotations

from app.core.logging import get_logger

_logger = get_logger("launcher.otel")

_initialized = False


def init_otel(app=None, service_name: str = "campus-life-platform") -> None:
    """初始化 OTel 追踪（生产环境）。开发依赖缺失时跳过。"""
    global _initialized
    if _initialized:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        _initialized = True
        _logger.info("otel_initialized", service=service_name)
    except Exception as exc:  # noqa: BLE001
        _logger.info("otel_skipped", reason=str(exc))
