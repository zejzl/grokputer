"""
Centralized logging configuration for Grokputer.

Provides structured logging with rotation, multiple handlers,
and configurable levels for different components.
"""
from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Any, Dict


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path = Path("logs"),
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_json: bool = False
) -> None:
    """
    Setup centralized logging configuration.

    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        max_bytes: Max size per log file before rotation
        backup_count: Number of backup files to keep
        enable_json: Use JSON format for structured logging
    """
    log_dir.mkdir(exist_ok=True)

    # Formatter configurations
    formatters = {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    }

    if enable_json:
        formatters['json'] = {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(message)s'
        }

    # Handler configurations
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': str(log_dir / 'grokputer.log'),
            'maxBytes': max_bytes,
            'backupCount': backup_count,
            'encoding': 'utf-8'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': str(log_dir / 'grokputer_error.log'),
            'maxBytes': max_bytes,
            'backupCount': backup_count,
            'encoding': 'utf-8'
        }
    }

    if enable_json:
        handlers['json_file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': str(log_dir / 'grokputer.json'),
            'maxBytes': max_bytes,
            'backupCount': backup_count,
            'encoding': 'utf-8'
        }

    # Logger configurations
    loggers = {
        'src': {
            'level': log_level,
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'src.agents': {
            'level': log_level,
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'src.core': {
            'level': log_level,
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'src.collaboration': {
            'level': log_level,
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'src.memory': {
            'level': log_level,
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'src.safety': {
            'level': 'WARNING',  # More restrictive for safety
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        }
    }

    if enable_json:
        for logger_name in loggers:
            loggers[logger_name]['handlers'].append('json_file')

    # Root logger
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'handlers': handlers,
        'loggers': loggers,
        'root': {
            'level': log_level,
            'handlers': ['console', 'file', 'error_file']
        }
    }

    if enable_json:
        config['root']['handlers'].append('json_file')

    logging.config.dictConfig(config)

    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, dir={log_dir}, json={enable_json}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger
    """
    return logging.getLogger(name)


# Convenience functions for common log levels
def log_performance(logger: logging.Logger, operation: str, duration: float, **kwargs):
    """Log performance metrics."""
    extra = {'operation': operation, 'duration_ms': duration * 1000, **kwargs}
    logger.info(f"Performance: {operation} took {duration:.3f}s", extra=extra)


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None):
    """Log error with additional context."""
    context = context or {}
    extra = {'error_type': type(error).__name__, 'error_message': str(error), **context}
    logger.error(f"Error occurred: {error}", exc_info=True, extra=extra)