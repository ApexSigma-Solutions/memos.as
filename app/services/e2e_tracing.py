"""
End-to-End Distributed Tracing for Memos.as - ApexSigma Agent Memory Service

This module implements comprehensive E2E tracing for the Memos service in the ApexSigma ecosystem.
Handles memory operations, chat thread management, and cross-service agent interactions.
"""

import uuid
from typing import Dict, Any, Optional
from contextlib import contextmanager

from opentelemetry import trace, baggage
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import extract, inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.propagators.b3 import B3MultiFormat, B3SingleFormat
from opentelemetry.propagators.composite import CompositePropagator
from fastapi import Request, Response
from structlog import get_logger

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

# Composite propagator for maximum compatibility
propagator = CompositePropagator(
    [
        TraceContextTextMapPropagator(),
        B3MultiFormat(),
        B3SingleFormat(),
        JaegerPropagator(),
        W3CBaggagePropagator(),
    ]
)


class MemosE2ETracing:
    """End-to-end distributed tracing for Memos.as service."""

    def __init__(self):
        self.service_name = "memos.as"
        self.service_version = "1.0.0"

    def extract_request_context(self, request: Request) -> Dict[str, Any]:
        """Extract tracing context from incoming HTTP request."""
        headers = dict(request.headers)

        # Extract OpenTelemetry context
        context = extract(headers)

        # Extract ApexSigma correlation headers
        correlation_id = headers.get("x-apexsigma-correlation-id")
        workflow_id = headers.get("x-apexsigma-workflow-id")
        agent_chain = headers.get("x-apexsigma-agent-chain", "")

        return {
            "context": context,
            "correlation_id": correlation_id,
            "workflow_id": workflow_id,
            "agent_chain": agent_chain,
            "source_service": headers.get("x-apexsigma-source-service"),
            "request_id": headers.get("x-request-id", str(uuid.uuid4())),
        }

    def inject_response_context(
        self, response: Response, correlation_id: str, workflow_id: Optional[str] = None
    ):
        """Inject tracing context into outgoing HTTP response."""
        carrier = {}
        inject(carrier)

        # Add OpenTelemetry headers
        for key, value in carrier.items():
            response.headers[key] = value

        # Add ApexSigma correlation headers
        response.headers["x-apexsigma-correlation-id"] = correlation_id
        if workflow_id:
            response.headers["x-apexsigma-workflow-id"] = workflow_id
        response.headers["x-apexsigma-service"] = self.service_name

    @contextmanager
    def trace_memory_operation(
        self,
        operation_name: str,
        memory_type: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace memory operations (store, retrieve, update, delete)."""
        span_name = f"memos.memory.{operation_name}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation_name)
                span.set_attribute("memory.type", memory_type)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("operation", operation_name)

                logger.info(
                    "Memory operation started",
                    operation=operation_name,
                    memory_type=memory_type,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Memory operation completed successfully",
                    operation=operation_name,
                    memory_type=memory_type,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Memory operation failed",
                    operation=operation_name,
                    memory_type=memory_type,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_chat_thread(
        self,
        thread_id: str,
        operation: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace chat thread operations (create, update, summarize)."""
        span_name = f"memos.chat_thread.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("chat_thread.id", thread_id)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("chat_thread_id", thread_id)

                logger.info(
                    "Chat thread operation started",
                    operation=operation,
                    thread_id=thread_id,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Chat thread operation completed",
                    operation=operation,
                    thread_id=thread_id,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Chat thread operation failed",
                    operation=operation,
                    thread_id=thread_id,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_agent_memory_access(
        self,
        agent_id: str,
        access_type: str,
        memory_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace agent memory access patterns for the ApexSigma society."""
        span_name = f"memos.agent_memory.{access_type}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", access_type)
                span.set_attribute("agent.id", agent_id)

                if memory_key:
                    span.set_attribute("memory.key", memory_key)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("agent_id", agent_id)
                baggage.set_baggage("access_type", access_type)

                logger.info(
                    "Agent memory access started",
                    agent_id=agent_id,
                    access_type=access_type,
                    memory_key=memory_key,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Agent memory access completed",
                    agent_id=agent_id,
                    access_type=access_type,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Agent memory access failed",
                    agent_id=agent_id,
                    access_type=access_type,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    def prepare_outbound_headers(
        self,
        target_service: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_chain: Optional[str] = None,
    ) -> Dict[str, str]:
        """Prepare headers for outbound HTTP requests to other services."""
        headers = {}

        # Inject OpenTelemetry context
        inject(headers)

        # Add ApexSigma correlation headers
        if correlation_id:
            headers["x-apexsigma-correlation-id"] = correlation_id
        if workflow_id:
            headers["x-apexsigma-workflow-id"] = workflow_id
        if agent_chain:
            headers["x-apexsigma-agent-chain"] = f"{agent_chain}->{self.service_name}"
        else:
            headers["x-apexsigma-agent-chain"] = self.service_name

        headers["x-apexsigma-source-service"] = self.service_name
        headers["x-request-id"] = str(uuid.uuid4())

        logger.debug(
            "Prepared outbound headers",
            target_service=target_service,
            correlation_id=correlation_id,
            headers=list(headers.keys()),
        )

        return headers

    @contextmanager
    def trace_cross_service_call(
        self,
        target_service: str,
        operation: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Trace outbound calls to other ApexSigma services."""
        span_name = f"memos.outbound.{target_service}.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("target.service", target_service)
                span.set_attribute("call.direction", "outbound")

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)

                logger.info(
                    "Cross-service call initiated",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Cross-service call completed",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Cross-service call failed",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise


# Global instance
memos_e2e_tracing = MemosE2ETracing()


def get_memos_e2e_tracing() -> MemosE2ETracing:
    """Get the global Memos E2E tracing instance."""
    return memos_e2e_tracing
