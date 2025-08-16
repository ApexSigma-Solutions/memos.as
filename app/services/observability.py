"""
Observability service for memOS.as integration with DevEnviro monitoring stack.

Integrates with:
- Prometheus (metrics)
- Loki (structured logging)
- Jaeger (distributed tracing)
- Grafana (dashboards)
"""

import os
import time
from typing import Dict, Any
from functools import wraps
from contextlib import contextmanager

import structlog
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor


class ObservabilityService:
    """
    Centralized observability service for memOS.as.

    Provides metrics, logging, and tracing integration with the DevEnviro
    monitoring stack (Prometheus, Loki, Jaeger, Grafana).
    """

    def __init__(self):
        self.service_name = "memos-as"
        self.version = "1.0.0"

        # Initialize components
        self._setup_logging()
        self._setup_metrics()
        self._setup_tracing()

        self.logger = structlog.get_logger()
        self.tracer = trace.get_tracer(self.service_name)

    def _setup_logging(self):
        """Configure structured logging for Loki integration."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def _setup_metrics(self):
        """Configure Prometheus metrics."""
        self.registry = CollectorRegistry()

        # Request metrics
        self.request_count = Counter(
            'memos_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'memos_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )

        # Memory operations metrics
        self.memory_operations = Counter(
            'memos_memory_operations_total',
            'Total memory operations',
            ['operation', 'status'],
            registry=self.registry
        )

        self.memory_storage_duration = Histogram(
            'memos_memory_storage_duration_seconds',
            'Memory storage operation duration',
            ['tier'],
            registry=self.registry
        )

        # Knowledge graph metrics
        self.knowledge_graph_operations = Counter(
            'memos_knowledge_graph_operations_total',
            'Knowledge graph operations',
            ['operation', 'node_type'],
            registry=self.registry
        )

        self.concepts_extracted = Histogram(
            'memos_concepts_extracted',
            'Number of concepts extracted per memory',
            buckets=[0, 1, 5, 10, 20, 50]
        )

        # System metrics
        self.active_connections = Gauge(
            'memos_active_connections',
            'Active database connections',
            ['database'],
            registry=self.registry
        )

        self.cache_hits = Counter(
            'memos_cache_hits_total',
            'Cache hit/miss statistics',
            ['cache_type', 'status'],
            registry=self.registry
        )

    def _setup_tracing(self):
        """Configure OpenTelemetry tracing for Jaeger."""
        # Set up tracer provider
        trace.set_tracer_provider(TracerProvider())

        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.environ.get("JAEGER_AGENT_HOST", "localhost"),
            agent_port=int(os.environ.get("JAEGER_AGENT_PORT", 14268)),
        )

        # Add span processor
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)

    def instrument_fastapi(self, app):
        """Instrument FastAPI application with observability."""
        # OpenTelemetry FastAPI instrumentation
        FastAPIInstrumentor.instrument_app(app)

        # Add metrics middleware
        @app.middleware("http")
        async def metrics_middleware(request, call_next):
            start_time = time.time()

            # Extract request info
            method = request.method
            path = request.url.path

            try:
                response = await call_next(request)
                status_code = response.status_code

                # Record metrics
                self.request_count.labels(
                    method=method,
                    endpoint=path,
                    status_code=status_code
                ).inc()

                duration = time.time() - start_time
                self.request_duration.labels(
                    method=method,
                    endpoint=path
                ).observe(duration)

                return response

            except Exception as e:
                # Record error metrics
                self.request_count.labels(
                    method=method,
                    endpoint=path,
                    status_code=500
                ).inc()

                # Log error
                self.logger.error(
                    "Request failed",
                    method=method,
                    path=path,
                    error=str(e),
                    duration=time.time() - start_time
                )
                raise

    def instrument_database_clients(self):
        """Instrument database clients for automatic tracing."""
        # SQLAlchemy instrumentation
        SQLAlchemyInstrumentor().instrument()

        # Redis instrumentation
        RedisInstrumentor().instrument()

    @contextmanager
    def trace_operation(self, operation_name: str, **attributes):
        """Context manager for tracing operations."""
        with self.tracer.start_as_current_span(operation_name) as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)

            start_time = time.time()
            try:
                yield span
                span.set_attribute("operation.success", True)
            except Exception as e:
                span.set_attribute("operation.success", False)
                span.set_attribute("operation.error", str(e))
                raise
            finally:
                span.set_attribute("operation.duration", time.time() - start_time)

    def record_memory_operation(self, operation: str, status: str, tier: str = None, duration: float = None):
        """Record memory operation metrics."""
        self.memory_operations.labels(operation=operation, status=status).inc()

        if tier and duration:
            self.memory_storage_duration.labels(tier=tier).observe(duration)

    def record_knowledge_graph_operation(self, operation: str, node_type: str):
        """Record knowledge graph operation metrics."""
        self.knowledge_graph_operations.labels(operation=operation, node_type=node_type).inc()

    def record_concepts_extracted(self, count: int):
        """Record number of concepts extracted."""
        self.concepts_extracted.observe(count)

    def record_cache_operation(self, cache_type: str, hit: bool):
        """Record cache hit/miss."""
        status = "hit" if hit else "miss"
        self.cache_hits.labels(cache_type=cache_type, status=status).inc()

    def log_structured(self, level: str, message: str, **kwargs):
        """Log structured message for Loki."""
        log_method = getattr(self.logger, level.lower())
        log_method(
            message,
            service=self.service_name,
            version=self.version,
            **kwargs
        )

    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest(self.registry).decode('utf-8')

    def health_check(self) -> Dict[str, Any]:
        """Health check with observability info."""
        return {
            "service": self.service_name,
            "version": self.version,
            "status": "healthy",
            "observability": {
                "metrics_enabled": True,
                "tracing_enabled": True,
                "logging_structured": True
            },
            "integrations": {
                "prometheus": True,
                "jaeger": True,
                "loki": True
            }
        }


# Global observability instance
observability = None


def get_observability() -> ObservabilityService:
    """FastAPI dependency to get observability service."""
    global observability
    if observability is None:
        observability = ObservabilityService()
    return observability


def trace_async(operation_name: str = None):
    """Decorator for tracing async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            obs = get_observability()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with obs.trace_operation(op_name, function=func.__name__):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def trace_sync(operation_name: str = None):
    """Decorator for tracing sync functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            obs = get_observability()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with obs.trace_operation(op_name, function=func.__name__):
                return func(*args, **kwargs)
        return wrapper
    return decorator
