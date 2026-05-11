"""
Logging configuration for PDF RAG Chatbot application.
Provides structured logging with different log levels and formats.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from config.settings import settings


def setup_logging(app_name: str = settings.APP_NAME, log_level: str = "INFO"):
    """
    Configure application logging with file and console handlers.
    """
    # Create logs directory if it doesn't exist
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Create log filename with date
    log_filename = settings.LOGS_DIR / f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # File handler (detailed format)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Console handler (simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Error file handler
    error_filename = settings.LOGS_DIR / f"{app_name}_error_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_filename, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    """
    return logging.getLogger(name)


class ContextFilter(logging.Filter):
    """
    Custom filter to add context information to log records.
    """
    def __init__(self):
        super().__init__()
        self.context = {}

    def add_context(self, key: str, value: str):
        """Add context information"""
        self.context[key] = value

    def clear_context(self):
        """Clear all context information"""
        self.context.clear()

    def filter(self, record):
        """Add context to log record"""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


# Create context filter instance
context_filter = ContextFilter()


def add_log_context(key: str, value: str):
    """Add context to all subsequent log messages"""
    context_filter.add_context(key, value)


def clear_log_context():
    """Clear all log context"""
    context_filter.clear_context()