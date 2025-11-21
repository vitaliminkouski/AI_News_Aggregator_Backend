import logging

from app.core.config import get_settings

settings=get_settings()

def setup_logging():
    log_level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger=logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    formatter=logging.Formatter(settings.LOG_FORMAT)

    console_handler=logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger=logging.getLogger(__name__)
    logger.info(f"Logging configured: level={settings.LOG_LEVEL}")

def get_logger(name: str):
    return logging.getLogger(name)
