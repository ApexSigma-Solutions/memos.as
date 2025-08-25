"""
Enhanced observability decorators and utilities for memOS LLM operations.
"""

import functools
import time
from typing import Any, Dict, Optional
from app.services.observability import get_observability


def trace_llm_operation(
    operation_name: str = None, model: str = None, include_io: bool = True
):
    """
    Decorator to trace LLM operations with comprehensive observability.

    Args:
        operation_name: Name of the operation (auto-detected if None)
        model: Model name for the LLM operation
        include_io: Whether to include input/output in traces
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            obs = get_observability()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            start_time = time.time()

            # Extract common parameters
            user_id = kwargs.get("user_id") or getattr(
                args[0] if args else None, "user_id", None
            )
            session_id = kwargs.get("session_id") or getattr(
                args[0] if args else None, "session_id", None
            )

            try:
                # Start observability tracing
                with obs.trace_operation(
                    op_name, operation=op_name, model=model, user_id=user_id
                ) as span:
                    result = await func(*args, **kwargs)

                    # Record successful operation
                    duration = time.time() - start_time

                    # Trace with Langfuse if available
                    if include_io and obs.langfuse:
                        input_data = (
                            str(args[1:]) if len(args) > 1 else str(kwargs)
                        )
                        output_data = str(result) if result else "No output"

                        obs.trace_llm_call(
                            model=model or "unknown",
                            input_text=input_data[:1000],  # Limit input size
                            output_text=output_data[
                                :1000
                            ],  # Limit output size
                            user_id=user_id,
                            session_id=session_id,
                            operation=op_name,
                            metadata={
                                "duration": duration,
                                "function": func.__name__,
                                "success": True,
                            },
                        )

                    # Record metrics
                    obs.record_memory_operation(
                        op_name, "success", duration=duration
                    )

                    obs.log_structured(
                        "info",
                        f"LLM operation completed",
                        operation=op_name,
                        duration=duration,
                        user_id=user_id,
                    )

                    return result

            except Exception as e:
                # Record failed operation
                duration = time.time() - start_time
                obs.record_memory_operation(
                    op_name, "error", duration=duration
                )

                obs.log_structured(
                    "error",
                    f"LLM operation failed",
                    operation=op_name,
                    error=str(e),
                    duration=duration,
                    user_id=user_id,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            obs = get_observability()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            start_time = time.time()

            # Extract common parameters
            user_id = kwargs.get("user_id") or getattr(
                args[0] if args else None, "user_id", None
            )
            session_id = kwargs.get("session_id") or getattr(
                args[0] if args else None, "session_id", None
            )

            try:
                with obs.trace_operation(
                    op_name, operation=op_name, model=model, user_id=user_id
                ) as span:
                    result = func(*args, **kwargs)

                    duration = time.time() - start_time

                    if include_io and obs.langfuse:
                        input_data = (
                            str(args[1:]) if len(args) > 1 else str(kwargs)
                        )
                        output_data = str(result) if result else "No output"

                        obs.trace_llm_call(
                            model=model or "unknown",
                            input_text=input_data[:1000],
                            output_text=output_data[:1000],
                            user_id=user_id,
                            session_id=session_id,
                            operation=op_name,
                            metadata={
                                "duration": duration,
                                "function": func.__name__,
                                "success": True,
                            },
                        )

                    obs.record_memory_operation(
                        op_name, "success", duration=duration
                    )

                    obs.log_structured(
                        "info",
                        f"LLM operation completed",
                        operation=op_name,
                        duration=duration,
                        user_id=user_id,
                    )

                    return result

            except Exception as e:
                duration = time.time() - start_time
                obs.record_memory_operation(
                    op_name, "error", duration=duration
                )

                obs.log_structured(
                    "error",
                    f"LLM operation failed",
                    operation=op_name,
                    error=str(e),
                    duration=duration,
                    user_id=user_id,
                )
                raise

        # Return appropriate wrapper based on function type
        if hasattr(func, "__await__"):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def trace_memory_operation(operation_type: str = None):
    """Decorator for memory storage/retrieval operations."""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            obs = get_observability()
            op_type = operation_type or func.__name__

            start_time = time.time()

            try:
                with obs.trace_operation(f"memory-{op_type}") as span:
                    result = await func(*args, **kwargs)

                    duration = time.time() - start_time
                    obs.record_memory_operation(
                        op_type, "success", duration=duration
                    )

                    return result

            except Exception as e:
                duration = time.time() - start_time
                obs.record_memory_operation(
                    op_type, "error", duration=duration
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            obs = get_observability()
            op_type = operation_type or func.__name__

            start_time = time.time()

            try:
                with obs.trace_operation(f"memory-{op_type}") as span:
                    result = func(*args, **kwargs)

                    duration = time.time() - start_time
                    obs.record_memory_operation(
                        op_type, "success", duration=duration
                    )

                    return result

            except Exception as e:
                duration = time.time() - start_time
                obs.record_memory_operation(
                    op_type, "error", duration=duration
                )
                raise

        if hasattr(func, "__await__"):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def trace_user_session(action: str = None):
    """Decorator for user session tracking."""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            obs = get_observability()

            # Extract user and session info
            user_id = kwargs.get("user_id") or getattr(
                args[0] if args else None, "user_id", None
            )
            session_id = kwargs.get("session_id") or getattr(
                args[0] if args else None, "session_id", None
            )

            if user_id and session_id:
                obs.trace_user_session(
                    user_id=user_id,
                    session_id=session_id,
                    action=action or func.__name__,
                    metadata={"function": func.__name__},
                )

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            obs = get_observability()

            user_id = kwargs.get("user_id") or getattr(
                args[0] if args else None, "user_id", None
            )
            session_id = kwargs.get("session_id") or getattr(
                args[0] if args else None, "session_id", None
            )

            if user_id and session_id:
                obs.trace_user_session(
                    user_id=user_id,
                    session_id=session_id,
                    action=action or func.__name__,
                    metadata={"function": func.__name__},
                )

            return func(*args, **kwargs)

        if hasattr(func, "__await__"):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class ObservabilityContext:
    """Context manager for complex operations requiring detailed tracking."""

    def __init__(
        self, operation_name: str, user_id: str = None, session_id: str = None
    ):
        self.operation_name = operation_name
        self.user_id = user_id
        self.session_id = session_id
        self.obs = get_observability()
        self.start_time = None
        self.trace_id = None

    def __enter__(self):
        self.start_time = time.time()

        # Start session tracking if available
        if self.user_id and self.session_id:
            self.trace_id = self.obs.trace_user_session(
                user_id=self.user_id,
                session_id=self.session_id,
                action=self.operation_name,
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0

        if exc_type is None:
            # Success
            self.obs.record_memory_operation(
                self.operation_name, "success", duration=duration
            )
            self.obs.log_structured(
                "info",
                f"Operation completed",
                operation=self.operation_name,
                duration=duration,
                user_id=self.user_id,
            )
        else:
            # Error
            self.obs.record_memory_operation(
                self.operation_name, "error", duration=duration
            )
            self.obs.log_structured(
                "error",
                f"Operation failed",
                operation=self.operation_name,
                error=str(exc_val),
                duration=duration,
                user_id=self.user_id,
            )

        # Flush Langfuse data
        self.obs.flush_langfuse()

    def add_metadata(self, **metadata):
        """Add metadata to the current operation."""
        if self.trace_id and self.obs.langfuse:
            # Add metadata to existing trace
            pass  # Implementation depends on Langfuse API

    def log_step(self, step_name: str, data: Any = None):
        """Log a step within the operation."""
        self.obs.log_structured(
            "debug",
            f"Operation step: {step_name}",
            operation=self.operation_name,
            step=step_name,
            data=str(data) if data else None,
            user_id=self.user_id,
        )
