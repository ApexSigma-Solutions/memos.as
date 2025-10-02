#!/usr/bin/env python3
"""
memOS Observability Integration Script

This script demonstrates how to integrate the observability instrumentation
into your existing memOS application.

Usage:
1. Install dependencies: pip install -r requirements-observability.txt
2. Import the instrumentation components into your main application
3. Add the metrics endpoints to your Flask/FastAPI routes
4. Configure structured logging in your application startup
"""

import os


def integrate_observability():
    """
    Integration steps for adding observability to memOS
    """

    print("🔧 memOS Observability Integration Guide")
    print("=" * 50)

    print("\n1. Install Dependencies:")
    print("   pip install -r requirements-observability.txt")

    print("\n2. Add to your main application file:")
    print(
        """
   from prometheus_client import generate_latest
   from instrumentation_example import (
       logger,
       http_requests_total,
       memory_operations_total,
       ai_model_inference_duration_seconds
   )

   # Add metrics endpoint
   @app.route('/metrics')
   def metrics():
       return generate_latest()
   """
    )

    print("\n3. Instrument your existing functions:")
    print(
        """
   # Before your memory operations:
   start_time = time.time()

   # After successful operation:
   memory_operations_total.labels(operation_type="store", status="success").inc()
   duration = time.time() - start_time
   memory_operation_duration_seconds.labels(operation_type="store").observe(duration)

   # Log with structured format:
   logger.info("Memory operation completed",
               operation="store",
               duration=duration*1000,
               session_id=session_id)
   """
    )

    print("\n4. Update your Docker configuration:")
    print(
        """
   # Add to docker-compose.yml:
   services:
     memos-app:
       ports:
         - "8090:8090"  # Expose metrics port
       environment:
         - METRICS_ENABLED=true
   """
    )

    print("\n5. Test the integration:")
    print("   curl http://localhost:8090/metrics")
    print("   curl http://localhost:8090/health")

    print("\n✅ Integration complete! Your memOS app will now expose:")
    print("   - Prometheus metrics at /metrics")
    print("   - Structured JSON logs for Promtail")
    print("   - Health check at /health")

    print("\n📊 View in Grafana:")
    print("   http://localhost:3001 (admin/memos123)")


def check_environment():
    """Check if the monitoring stack is running"""
    print("\n🔍 Checking monitoring environment...")

    # Check if docker containers are running
    os.system("docker ps --filter name=memos")

    print("\n📈 Expected services:")
    print("   - Grafana: http://localhost:3001")
    print("   - Prometheus: http://localhost:9091")
    print("   - Jaeger: http://localhost:16687")


if __name__ == "__main__":
    integrate_observability()
    check_environment()
