"""
NexusAI Platform - Logging Configuration
Structured logging with request IDs, performance tracking, and multiple outputs
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from backend.core.config import settings


def setup_logging():
    """
    Configure structured logging for the application.
    
    Sets up:
    - JSON formatting for production
    - Console output for development
    - File rotation
    - Request ID tracking
    - Performance metrics
    """
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[],  # We'll add custom handlers
    )
    
    # Create formatters
    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # File handler with rotation
    log_dir = Path("/var/log/nexusai")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=104857600,  # 100MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure structlog
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
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class RequestIDFilter(logging.Filter):
    """Add request ID to log records."""
    
    def filter(self, record):
        record.request_id = getattr(record, "request_id", "N/A")
        return True


# Add request ID filter to all handlers
for handler in logging.root.handlers:
    handler.addFilter(RequestIDFilter())
