import structlog
import logging
import sys


def setup_logging():
    """Настройка structlog"""
    
    # Процессоры для structlog
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

    # Настройка structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Форматтер для консоли (цветной вывод)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )

    # Настройка стандартного logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(console_formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Устанавливаем уровень для aiogram
    structlog.getLogger("aiogram").setLevel(logging.INFO)
    structlog.getLogger("httpx").setLevel(logging.WARNING)
    structlog.getLogger("httpcore").setLevel(logging.WARNING)