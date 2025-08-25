"""
memOS Application Instrumentation Example
This file shows how to add the metrics and structured logging
that the monitoring stack expects.
"""

import time
import json
import logging
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Flask, request, jsonify
import structlog

# Configure structured logging
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

# Create structured logger
logger = structlog.get_logger()

# Prometheus Metrics - Matching the dashboard configuration
# API Performance Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

http_requests_in_flight = Gauge(
    "http_requests_in_flight",
    "HTTP requests currently being processed",
    ["endpoint"],
)

# Memory Operations Metrics
memory_operations_total = Counter(
    "memory_operations_total",
    "Total memory operations",
    ["operation_type", "status"],
)

memory_operation_duration_seconds = Histogram(
    "memory_operation_duration_seconds",
    "Memory operation duration in seconds",
    ["operation_type"],
)

persistent_memory_size_bytes = Gauge(
    "persistent_memory_size_bytes",
    "Size of persistent memory in bytes",
    ["session_id"],
)

memory_search_results = Gauge(
    "memory_search_results",
    "Number of memory search results",
    ["query_type"],
)

# AI/ML Specific Metrics
ai_model_inference_duration_seconds = Histogram(
    "ai_model_inference_duration_seconds",
    "AI model inference duration in seconds",
    ["model", "operation"],
)

token_processing_rate = Gauge(
    "token_processing_rate",
    "Token processing rate per second",
    ["model"],
)

ai_service_requests_total = Counter(
    "ai_service_requests_total",
    "Total AI service requests",
    ["service", "status"],
)

queue_size = Gauge(
    "queue_size",
    "Current queue size",
    ["queue_name"],
)

app = Flask(__name__)


class MemoryService:
    """Example Memory Service with instrumentation"""

    def __init__(self):
        self.sessions = {}

    def store_memory(
        self, session_id: str, content: str, memory_type: str = "episodic"
    ):
        """Store memory with full instrumentation"""
        start_time = time.time()

        try:
            # Log the operation start
            logger.info(
                "Memory operation started",
                operation="store",
                session_id=session_id,
                memory_type=memory_type,
                service="memory-service",
            )

            # Simulate memory storage
            if session_id not in self.sessions:
                self.sessions[session_id] = []

            self.sessions[session_id].append(
                {
                    "content": content,
                    "type": memory_type,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Update metrics
            duration = time.time() - start_time
            memory_operations_total.labels(
                operation_type="store", status="success"
            ).inc()

            memory_operation_duration_seconds.labels(
                operation_type="store"
            ).observe(duration)

            # Update memory size
            memory_size = len(
                json.dumps(self.sessions[session_id]).encode("utf-8")
            )
            persistent_memory_size_bytes.labels(session_id=session_id).set(
                memory_size
            )

            # Log success
            logger.info(
                "Memory stored successfully",
                operation="store",
                duration=duration * 1000,  # milliseconds
                memory_type=memory_type,
                session_id=session_id,
                service="memory-service",
            )

            return True

        except Exception as e:
            memory_operations_total.labels(
                operation_type="store", status="error"
            ).inc()

            logger.error(
                "Memory operation failed",
                operation="store",
                error=str(e),
                session_id=session_id,
                memory_type=memory_type,
                service="memory-service",
                level="error",
            )
            return False

    def search_memory(
        self, session_id: str, query: str, query_type: str = "semantic"
    ):
        """Search memory with instrumentation"""
        start_time = time.time()

        try:
            logger.info(
                "Memory search started",
                operation="search",
                session_id=session_id,
                query_type=query_type,
                service="memory-service",
            )

            # Simulate search
            results = []
            if session_id in self.sessions:
                for memory in self.sessions[session_id]:
                    if query.lower() in memory["content"].lower():
                        results.append(memory)

            # Update metrics
            duration = time.time() - start_time
            memory_operations_total.labels(
                operation_type="search", status="success"
            ).inc()

            memory_operation_duration_seconds.labels(
                operation_type="search"
            ).observe(duration)

            memory_search_results.labels(query_type=query_type).set(
                len(results)
            )

            logger.info(
                "Memory search completed",
                operation="search",
                duration=duration * 1000,
                memory_type="search_result",
                session_id=session_id,
                results_count=len(results),
                service="memory-service",
            )

            return results

        except Exception as e:
            memory_operations_total.labels(
                operation_type="search", status="error"
            ).inc()

            logger.error(
                "Memory search failed",
                operation="search",
                error=str(e),
                session_id=session_id,
                service="memory-service",
                level="error",
            )
            return []


class AIService:
    """Example AI Service with instrumentation"""

    def __init__(self):
        self.processing_queue = []

    def process_request(self, model: str, prompt: str, session_id: str):
        """Process AI request with full instrumentation"""
        start_time = time.time()

        try:
            # Update queue size
            self.processing_queue.append({"model": model, "prompt": prompt})
            queue_size.labels(queue_name="ai_processing").set(
                len(self.processing_queue)
            )

            logger.info(
                "AI inference started",
                model=model,
                session_id=session_id,
                service="ai-tool-api",
            )

            # Simulate AI processing
            time.sleep(0.1)  # Simulate processing time

            # Generate response
            response = f"AI response for: {prompt[:50]}..."
            tokens_processed = len(prompt.split()) + len(response.split())

            # Update metrics
            duration = time.time() - start_time
            ai_model_inference_duration_seconds.labels(
                model=model, operation="inference"
            ).observe(duration)

            token_processing_rate.labels(model=model).set(
                tokens_processed / duration
            )

            ai_service_requests_total.labels(
                service="inference", status="success"
            ).inc()

            # Remove from queue
            self.processing_queue.pop(0)
            queue_size.labels(queue_name="ai_processing").set(
                len(self.processing_queue)
            )

            logger.info(
                "AI inference completed",
                model=model,
                session_id=session_id,
                duration=duration * 1000,
                tokens_processed=tokens_processed,
                service="ai-tool-api",
            )

            return response

        except Exception as e:
            ai_service_requests_total.labels(
                service="inference", status="error"
            ).inc()

            logger.error(
                "AI inference failed",
                model=model,
                error=str(e),
                session_id=session_id,
                service="ai-tool-api",
                level="error",
            )
            return None


# Initialize services
memory_service = MemoryService()
ai_service = AIService()


@app.before_request
def before_request():
    """Track request start"""
    request.start_time = time.time()
    endpoint = request.endpoint or request.path
    http_requests_in_flight.labels(endpoint=endpoint).inc()


@app.after_request
def after_request(response):
    """Track request completion with full instrumentation"""
    if hasattr(request, "start_time"):
        duration = time.time() - request.start_time
        endpoint = request.endpoint or request.path
        method = request.method
        status = str(response.status_code)

        # Update metrics
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()

        http_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

        http_requests_in_flight.labels(endpoint=endpoint).dec()

        # Log API access
        logger.info(
            "API request completed",
            method=method,
            endpoint=endpoint,
            status_code=int(status),
            response_time=duration * 1000,  # milliseconds
            session_id=request.headers.get("X-Session-ID", "unknown"),
            service="ai-tool-api",
        )

    return response


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify(
        {"status": "healthy", "timestamp": datetime.now().isoformat()}
    )


@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()


@app.route("/api/memory/store", methods=["POST"])
def store_memory():
    """Store memory endpoint"""
    data = request.get_json()
    session_id = request.headers.get("X-Session-ID", "default")

    success = memory_service.store_memory(
        session_id=session_id,
        content=data.get("content", ""),
        memory_type=data.get("type", "episodic"),
    )

    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error"}), 500


@app.route("/api/memory/search", methods=["POST"])
def search_memory():
    """Search memory endpoint"""
    data = request.get_json()
    session_id = request.headers.get("X-Session-ID", "default")

    results = memory_service.search_memory(
        session_id=session_id,
        query=data.get("query", ""),
        query_type=data.get("type", "semantic"),
    )

    return jsonify({"results": results})


@app.route("/api/ai/inference", methods=["POST"])
def ai_inference():
    """AI inference endpoint"""
    data = request.get_json()
    session_id = request.headers.get("X-Session-ID", "default")

    response = ai_service.process_request(
        model=data.get("model", "gpt-4"),
        prompt=data.get("prompt", ""),
        session_id=session_id,
    )

    if response:
        return jsonify({"response": response})
    else:
        return jsonify({"error": "AI processing failed"}), 500


if __name__ == "__main__":
    # Configure logging for container output
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",  # Structured logs will be JSON
    )

    logger.info(
        "memOS application starting",
        service="ai-tool-app",
        level="info",
        message="Application startup complete",
    )

    app.run(host="0.0.0.0", port=8090, debug=False)
