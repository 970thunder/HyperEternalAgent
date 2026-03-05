"""
Logging system for HyperEternalAgent framework.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
) -> None:
    """
    Set up structured logging.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        json_format: Use JSON format for logs
    """
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure structlog processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_format:
        # JSON format for production
        renderer = structlog.processors.JSONRenderer()
    else:
        # Colorized console output for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (defaults to calling module)

    Returns:
        Bound logger instance
    """
    return structlog.get_logger(name)


class LoggerAdapter:
    """Adapter for legacy logging compatibility."""

    def __init__(self, name: str):
        self._logger = get_logger(name)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        self._logger.exception(message, **kwargs)

    def with_context(self, **kwargs: Any) -> "LoggerAdapter":
        """Create a new adapter with additional context."""
        adapter = LoggerAdapter.__new__(LoggerAdapter)
        adapter._logger = self._logger.bind(**kwargs)
        return adapter


class LogContext:
    """Context manager for logging context."""

    def __init__(self, **kwargs: Any):
        self._context = kwargs
        self._token: Optional[Any] = None

    def __enter__(self) -> "LogContext":
        self._token = structlog.contextvars.bind_contextvars(**self._context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._token:
            structlog.contextvars.unbind_contextvars(*self._context.keys())


def log_execution(logger: structlog.stdlib.BoundLogger, operation: str):
    """
    Decorator for logging function execution.

    Usage:
        @log_execution(logger, "process_task")
        async def process_task(task):
            ...
    """

    def decorator(func):
        import asyncio
        import functools
        import time

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            logger.info(f"{operation}_started")
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"{operation}_completed", duration_seconds=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation}_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=duration,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            logger.info(f"{operation}_started")
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"{operation}_completed", duration_seconds=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation}_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=duration,
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
