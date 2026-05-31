"""
HFOS v5.0 — Structured Logging
Loguru-based with rotation, retention, structured JSON for prod.
"""
import sys
from loguru import logger

from config.settings import LOG_LEVEL, LOG_DIR, LOG_ROTATION, LOG_RETENTION


def setup_logging():
    """Configure Loguru: console (dev) + file rotation (prod)."""
    logger.remove()  # Remove default handler

    # Console handler
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    )
    logger.add(
        sys.stderr,
        format=log_format,
        level=LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=False,  # Don't expose variable values in prod
    )

    # File handler (rotating)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_DIR / "hfos_{time:YYYY-MM-DD}.log",
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="gz",
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=False,
    )

    # Audit log (append-only, separate file)
    logger.add(
        LOG_DIR / "audit.log",
        rotation="1 week",
        retention="1 year",
        compression="gz",
        level="INFO",
        filter=lambda r: r["extra"].get("audit") is True,
        format="{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {message}",
    )

    return logger


def get_audit_logger():
    """Return a logger bound to the audit sink."""
    return logger.bind(audit=True)
