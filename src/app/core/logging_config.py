"""
Настройка structlog + стандартного logging.

ИСПРАВЛЕН БАГ: structlog не имеет метода .getLogger() — это метод стандартного
logging. Ошибка вызывала AttributeError при старте.
"""
import logging
import sys

import structlog


def setup_logging() -> None:
    """Настройка structlog с выводом в консоль."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(console_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # ИСПРАВЛЕНО: logging.getLogger(), не structlog.getLogger()
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)