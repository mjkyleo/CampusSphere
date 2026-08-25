"""Prometheus 指标。"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from prometheus_client.registry import REGISTRY

REQUEST_COUNT = Counter(
    "campus_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "campus_http_request_latency_seconds", "HTTP request latency", ["endpoint"]
)


def get_metrics() -> bytes:
    return generate_latest(REGISTRY)


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST
