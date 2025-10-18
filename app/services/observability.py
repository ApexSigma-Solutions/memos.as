"""
Observability service for memOS.as integration with DevEnviro monitoring stack.

Integrates with:
- Prometheus (metrics)
- Loki (structured logging)
- Jaeger (distributed tracing)
- Grafana (dashboards)
- Langfuse (LLM tracing)
"""

import os
import time
from typing import Dict, Any
from functools import wraps
from contextlib import contextmanager

import structlog
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
)
# Optional OpenTelemetry imports - keep them lazy and guarded so unit tests
# don't fail when tracing exporters are not installed in the test environment.
trace = None
TracerProvider = None
BatchSpanProcessor = None
JaegerExporter = None
FastAPIInstrumentor = None
SQLAlchemyInstrumentor = None
RedisInstrumentor = None


class ObservabilityService:
    """
    Centralized observability service for memOS.as.

    Provides metrics, logging, and tracing integration with the DevEnviro
    monitoring stack (Prometheus, Loki, Jaeger, Grafana, Langfuse).
    """

    def __init__(self):
        """
        Initialize an ObservabilityService instance and configure logging, metrics, tracing, and Langfuse integration.
        
        Sets service_name and version, prepares the Langfuse client placeholder, and runs setup routines for logging, Prometheus metrics, OpenTelemetry tracing, and Langfuse. After setup it binds a structured logger to self.logger and attempts to obtain an OpenTelemetry tracer; self.tracer will be None if OpenTelemetry is not available.
        """
        self.service_name = "memos-as"
        self.version = "1.0.0"

        # Initialize langfuse first (may be None)
        self.langfuse = None

        # Initialize components
        self._setup_logging()
        self._setup_metrics()
        self._setup_tracing()
        self._setup_langfuse()

        # Set logger and tracer after setup
        self.logger = structlog.get_logger()
        # Try to obtain a tracer if OpenTelemetry is available
        try:
            from opentelemetry import trace as _trace

            self.tracer = _trace.get_tracer(self.service_name)
        except Exception:
            self.tracer = None

    def _setup_logging(self):
        """
        Configure structured JSON logging suitable for Loki ingestion.
        
        Sets up structlog to produce timestamped, exception-aware, Unicode-safe JSON logs and caches the configured logger for first use.
        """
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
                structlog.processors.JSONRenderer(),
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
            "memos_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            "memos_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            registry=self.registry,
        )

        # Memory operations metrics
        self.memory_operations = Counter(
            "memos_memory_operations_total",
            "Total memory operations",
            ["operation", "status"],
            registry=self.registry,
        )

        self.memory_storage_duration = Histogram(
            "memos_memory_storage_duration_seconds",
            "Memory storage operation duration",
            ["tier"],
            registry=self.registry,
        )

        # Knowledge graph metrics
        self.knowledge_graph_operations = Counter(
            "memos_knowledge_graph_operations_total",
            "Knowledge graph operations",
            ["operation", "node_type"],
            registry=self.registry,
        )

        self.concepts_extracted = Histogram(
            "memos_concepts_extracted",
            "Number of concepts extracted per memory",
            buckets=[0, 1, 5, 10, 20, 50],
            registry=self.registry,
        )

        # System metrics
        self.active_connections = Gauge(
            "memos_active_connections",
            "Active database connections",
            ["database"],
            registry=self.registry,
        )

        # MCP-specific metrics
        self.mcp_auth_attempts = Counter(
            "memos_mcp_auth_attempts_total",
            "MCP authentication attempts",
            ["service_account", "result"],
            registry=self.registry,
        )

        self.mcp_requests_total = Counter(
            "memos_mcp_requests_total",
            "Total MCP requests",
            ["method", "endpoint", "service_account", "status"],
            registry=self.registry,
        )

        self.mcp_request_duration = Histogram(
            "memos_mcp_request_duration_seconds",
            "MCP request duration in seconds",
            ["method", "endpoint", "service_account"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry,
        )

        self.mcp_rate_limit_hits = Counter(
            "memos_mcp_rate_limit_hits_total",
            "MCP rate limit hits",
            ["service_account"],
            registry=self.registry,
        )

        self.mcp_tool_usage = Counter(
            "memos_mcp_tool_usage_total",
            "MCP tool usage",
            ["tool_name", "service_account", "result"],
            registry=self.registry,
        )

        self.mcp_active_connections = Gauge(
            "memos_mcp_active_connections",
            "Active MCP connections",
            ["service_account"],
            registry=self.registry,
        )

        self.mcp_memory_operations = Counter(
            "memos_mcp_memory_operations_total",
            "MCP memory operations",
            ["operation", "tier", "service_account", "result"],
            registry=self.registry,
        )

        self.mcp_audit_events = Counter(
            "memos_mcp_audit_events_total",
            "MCP audit events",
            ["event_type", "service_account", "severity"],
            registry=self.registry,
        )

    def _setup_tracing(self):
        """
        Configure OpenTelemetry tracing and attach a Jaeger exporter when available.
        
        Attempts to lazily import OpenTelemetry and set a tracer provider. If a Jaeger exporter is installed, attaches a BatchSpanProcessor configured with
        JAEGER_AGENT_HOST and JAEGER_AGENT_PORT environment variables. If OpenTelemetry or the Jaeger exporter is not present or fails to initialize,
        the function logs the condition and leaves tracing unexported without raising.
        """
        try:
            # Import OpenTelemetry components lazily
            from opentelemetry import trace as _trace
            from opentelemetry.sdk.trace import TracerProvider as _TracerProvider
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor as _BatchSpanProcessor,
            )
            # Try to import Jaeger exporter; if missing, skip tracer exporter setup
            try:
                from opentelemetry.exporter.jaeger.thrift import (
                    JaegerExporter as _JaegerExporter,
                )
            except Exception:
                _JaegerExporter = None

            # Set up tracer provider
            _trace.set_tracer_provider(_TracerProvider())

            if _JaegerExporter is not None:
                jaeger_exporter = _JaegerExporter(
                    agent_host_name=os.environ.get("JAEGER_AGENT_HOST", "localhost"),
                    agent_port=int(os.environ.get("JAEGER_AGENT_PORT", 14268)),
                )
                span_processor = _BatchSpanProcessor(jaeger_exporter)
                _trace.get_tracer_provider().add_span_processor(span_processor)
            else:
                # Exporter not installed; tracing will be available but not exported
                self.logger = structlog.get_logger()
                self.logger.debug("Jaeger exporter not installed; skipping exporter setup")
        except Exception as e:
            # OpenTelemetry not installed or failed to initialize - continue without tracing
            try:
                structlog.get_logger().warning(
                    f"OpenTelemetry tracing not configured: {e}"
                )
            except Exception:
                pass

    def _setup_langfuse(self):
        """
        Initialize the Langfuse client when valid API keys are available and record a startup event.
        
        Reads LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY from the environment (uses LANGFUSE_HOST with default https://cloud.langfuse.com if set) and, if both keys are present and authentication succeeds, assigns a Langfuse client to self.langfuse and attempts to create and flush a "memos-startup" event. If keys are missing, authentication fails, or any error occurs during initialization or event creation, self.langfuse is set to None and the function logs status messages via print.
        """
        try:
            # Use the correct environment variable names
            secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
            public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
            host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

            if secret_key and public_key:
                self.langfuse = Langfuse(
                    secret_key=secret_key, public_key=public_key, host=host
                )

                # Test authentication
                if self.langfuse.auth_check():
                    print("✅ Langfuse integration enabled and authenticated")
                    # Create startup event to activate observability
                    try:
                        self.langfuse.create_event(
                            name="memos-startup",
                            input="memOS observability initialization",
                            output="Langfuse successfully connected",
                            metadata={
                                "service": self.service_name,
                                "version": self.version,
                                "event": "startup",
                            },
                        )
                        self.langfuse.flush()
                        print("🚀 Startup event created successfully")
                    except Exception as trace_error:
                        print(f"⚠️ Could not create startup event: {trace_error}")
                        # Continue anyway - Langfuse is still available
                else:
                    self.langfuse = None
                    print("❌ Langfuse authentication failed")
            else:
                self.langfuse = None
                print("⚠️ Langfuse API keys not provided - LLM tracing disabled")
        except Exception as e:
            self.langfuse = None
            print(f"❌ Failed to initialize Langfuse: {str(e)}")

    def instrument_fastapi(self, app):
        """
        Configure a FastAPI application for observability by attempting OpenTelemetry instrumentation and adding Prometheus metrics middleware.
        
        Attempts to instrument the app with OpenTelemetry FastAPI instrumentation if the package is available; if instrumentation is unavailable or fails, continues silently. Adds an HTTP middleware that:
        - Increments the request counter metric with labels `method`, `endpoint`, and `status_code`.
        - Observes request duration in the request duration histogram with labels `method` and `endpoint`.
        - On unhandled exceptions, increments the counter with `status_code` 500 and logs the error with method, path, error, and duration.
        
        Parameters:
            app: The FastAPI application instance to instrument.
        """
        # OpenTelemetry FastAPI instrumentation (optional)
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor as _FastAPIInstrumentor

            _FastAPIInstrumentor.instrument_app(app)
        except Exception:
            # Instrumentation not installed or failed - continue silently
            try:
                self.logger.debug("FastAPI instrumentation not available")
            except Exception:
                pass

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
                    method=method, endpoint=path, status_code=status_code
                ).inc()

                duration = time.time() - start_time
                self.request_duration.labels(method=method, endpoint=path).observe(
                    duration
                )

                return response

            except Exception as e:
                # Record error metrics
                self.request_count.labels(
                    method=method, endpoint=path, status_code=500
                ).inc()

                # Log error
                self.logger.error(
                    "Request failed",
                    method=method,
                    path=path,
                    error=str(e),
                    duration=time.time() - start_time,
                )
                raise

    def instrument_database_clients(self):
        """
        Attempt to enable OpenTelemetry instrumentation for SQLAlchemy and Redis clients.
        
        If OpenTelemetry instrumentation packages for SQLAlchemy or Redis are available, they will be instrumented; if not, the method logs a debug message and returns without raising.
        """
        try:
            from opentelemetry.instrumentation.sqlalchemy import (
                SQLAlchemyInstrumentor as _SQLAlchemyInstrumentor,
            )
            from opentelemetry.instrumentation.redis import (
                RedisInstrumentor as _RedisInstrumentor,
            )

            _SQLAlchemyInstrumentor().instrument()
            _RedisInstrumentor().instrument()
        except Exception:
            try:
                self.logger.debug("OTel instrumentation for DB/Redis not available")
            except Exception:
                pass

    @contextmanager
    def trace_operation(self, operation_name: str, **attributes):
        """
        Create a tracing span context for an operation and record success, error, and duration metadata.
        
        The created span will have any provided attributes attached. On normal exit the span receives
        the attribute `operation.success = True`; if an exception is raised the span receives
        `operation.success = False` and `operation.error` with the exception string. The span always
        receives `operation.duration` with the operation elapsed time in seconds. Exceptions are re-raised.
        
        Parameters:
            operation_name (str): Name of the operation/span.
            **attributes: Any additional span attributes to set on enter (key-value pairs).
        
        Returns:
            span: The active tracing span for the operation.
        """
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

    def record_memory_operation(
        self,
        operation: str,
        status: str,
        tier: str = None,
        duration: float = None,
    ):
        """Record memory operation metrics."""
        self.memory_operations.labels(operation=operation, status=status).inc()

        if tier and duration:
            self.memory_storage_duration.labels(tier=tier).observe(duration)

    def record_knowledge_graph_operation(self, operation: str, node_type: str):
        """Record knowledge graph operation metrics."""
        self.knowledge_graph_operations.labels(
            operation=operation, node_type=node_type
        ).inc()

    def record_concepts_extracted(self, count: int):
        """Record number of concepts extracted."""
        self.concepts_extracted.observe(count)

    def record_cache_operation(self, cache_type: str, hit: bool):
        """Record cache hit/miss."""
        status = "hit" if hit else "miss"
        self.cache_hits.labels(cache_type=cache_type, status=status).inc()

    def record_mcp_auth_attempt(self, service_account: str, success: bool):
        """Record MCP authentication attempt."""
        result = "success" if success else "failure"
        self.mcp_auth_attempts.labels(
            service_account=service_account, result=result
        ).inc()

    def record_mcp_request(
        self,
        method: str,
        endpoint: str,
        service_account: str,
        status_code: int,
        duration: float = None,
    ):
        """Record MCP request metrics."""
        status = str(status_code)
        self.mcp_requests_total.labels(
            method=method,
            endpoint=endpoint,
            service_account=service_account,
            status=status,
        ).inc()

        if duration is not None:
            self.mcp_request_duration.labels(
                method=method,
                endpoint=endpoint,
                service_account=service_account,
            ).observe(duration)

    def record_mcp_rate_limit_hit(self, service_account: str):
        """Record MCP rate limit hit."""
        self.mcp_rate_limit_hits.labels(service_account=service_account).inc()

    def record_mcp_tool_usage(
        self, tool_name: str, service_account: str, success: bool
    ):
        """Record MCP tool usage."""
        result = "success" if success else "failure"
        self.mcp_tool_usage.labels(
            tool_name=tool_name, service_account=service_account, result=result
        ).inc()

    def update_mcp_active_connections(self, service_account: str, count: int):
        """Update active MCP connections gauge."""
        self.mcp_active_connections.labels(service_account=service_account).set(count)

    def record_mcp_memory_operation(
        self, operation: str, tier: str, service_account: str, success: bool
    ):
        """Record MCP memory operation."""
        result = "success" if success else "failure"
        self.mcp_memory_operations.labels(
            operation=operation,
            tier=tier,
            service_account=service_account,
            result=result,
        ).inc()

    def record_mcp_audit_event(
        self, event_type: str, service_account: str, severity: str = "info"
    ):
        """Record MCP audit event."""
        self.mcp_audit_events.labels(
            event_type=event_type, service_account=service_account, severity=severity
        ).inc()

    def log_structured(self, level: str, message: str, **kwargs):
        """Log structured message for Loki."""
        log_method = getattr(self.logger, level.lower())
        log_method(message, service=self.service_name, version=self.version, **kwargs)

    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest(self.registry).decode("utf-8")

    def health_check(self) -> Dict[str, Any]:
        """Health check with observability info."""
        return {
            "service": self.service_name,
            "version": self.version,
            "status": "healthy",
            "observability": {
                "metrics_enabled": True,
                "tracing_enabled": True,
                "logging_structured": True,
            },
            "integrations": {
                "prometheus": True,
                "jaeger": True,
                "loki": True,
                "langfuse": self.langfuse is not None,
            },
        }

    def trace_llm_call(
        self,
        model: str,
        input_text: str,
        output_text: str = None,
        user_id: str = None,
        session_id: str = None,
        operation: str = "completion",
        metadata: Dict[str, Any] = None,
    ):
        """Trace LLM calls with Langfuse."""
        if not self.langfuse:
            return None

        try:
            # Create generation using the new API
            generation = self.langfuse.start_generation(
                name=f"memos-{operation}",
                model=model,
                input=input_text,
                metadata={
                    "service": self.service_name,
                    "operation": operation,
                    "user_id": user_id,
                    "session_id": session_id,
                    **(metadata or {}),
                },
            )

            # Update with output if available
            if output_text:
                generation.update(output=output_text)

            generation.end()

            return generation.id
        except Exception as e:
            self.log_structured("error", "Failed to trace LLM call", error=str(e))
            return None

    def trace_user_session(
        self,
        user_id: str,
        session_id: str,
        action: str,
        metadata: Dict[str, Any] = None,
    ):
        """Trace user session events."""
        if not self.langfuse:
            return None

        try:
            session_data = {
                "id": session_id,
                "user_id": user_id,
                "metadata": {
                    "action": action,
                    "service": self.service_name,
                    **(metadata or {}),
                },
            }

            session = self.langfuse.trace(**session_data)
            return session.id
        except Exception as e:
            self.log_structured("error", "Failed to trace session", error=str(e))
            return None

    def trace_memory_operation_detailed(
        self,
        operation: str,
        memory_content: str,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
    ):
        """Trace detailed memory operations."""
        if not self.langfuse:
            return None

        try:
            trace_data = {
                "name": f"memory-{operation}",
                "input": memory_content,
                "metadata": {
                    "operation": operation,
                    "user_id": user_id,
                    "service": self.service_name,
                    **(metadata or {}),
                },
            }

            trace = self.langfuse.trace(**trace_data)
            return trace.id
        except Exception as e:
            self.log_structured(
                "error", "Failed to trace memory operation", error=str(e)
            )
            return None

    def flush_langfuse(self):
        """Flush Langfuse data immediately."""
        if self.langfuse:
            try:
                self.langfuse.flush()
                self.log_structured("debug", "Langfuse data flushed")
            except Exception as e:
                self.log_structured("error", "Failed to flush Langfuse", error=str(e))


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