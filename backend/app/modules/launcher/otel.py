"""OpenTelemetry 初始化（OTLP 导出；未配置/缺依赖时优雅降级）。

通过环境变量驱动，无需改代码即可切换导出目标：
- ``OTEL_EXPORTER_OTLP_ENDPOINT``：OTLP gRPC 端点，如 ``http://otel-collector:4317``。
  设置该变量即视为开启 OTLP（等效 ``OTEL_ENABLED=true``）。
- ``OTEL_ENABLED``：显式 ``true/false`` 强制开关。
- ``OTEL_EXPORTER_OTLP_INSECURE``：默认 ``true``（内网 collector 明文 4317）；
  公网/带 TLS 的 collector 请设为 ``false``。
- ``OTEL_SERVICE_NAME``：服务名（默认 campus-life-platform）。

缺失依赖或端点未配置时回退 ``ConsoleSpanExporter``（开发可读），绝不阻断启动。
"""

from __future__ import annotations

import os

from app.core.logging import get_logger

_logger = get_logger("launcher.otel")

_initialized = False


def init_otel(app=None, service_name: str = "campus-life-platform") -> None:
    """初始化 OTel 追踪并织入 FastAPI 路由（生产环境）。"""
    global _initialized
    if _initialized:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        svc = os.environ.get("OTEL_SERVICE_NAME", service_name)
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        enabled = os.environ.get("OTEL_ENABLED", "false").lower() == "true" or bool(endpoint)

        resource = Resource.create({"service.name": svc, "service.version": "1.0.0"})
        provider = TracerProvider(resource=resource)

        if enabled and endpoint:
            insecure = os.environ.get("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"
            exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            _logger.info("otel_otlp_initialized", service=svc, endpoint=endpoint, insecure=insecure)
        else:
            # 开发/未配置：控制台导出，保证可见且不阻断
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            _logger.info("otel_console_fallback", reason="OTEL_EXPORTER_OTLP_ENDPOINT not set")

        trace.set_tracer_provider(provider)

        # 真正织入 FastAPI 路由（此前仅设置 provider，未埋点）
        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

                FastAPIInstrumentor.instrument_app(app)
                _logger.info("otel_fastapi_instrumented")
            except Exception as exc:
                _logger.warning("otel_fastapi_instrument_failed", error=str(exc))

        _initialized = True
    except Exception as exc:
        _logger.info("otel_skipped", reason=str(exc))
