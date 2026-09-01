import logging
from pathlib import Path

import colorlog

__all__ = ["setup_logger", "configure_third_party_loggers"]


def setup_logger(
    log_dir: Path,
    logger_name: str = "root",
    file_name: str = "experiment.log",
    stream_level: int = logging.INFO,
    file_level: int = logging.INFO,
    file_mode: str = "a",
    log_filter: logging.Filter | None = None,
    configure_third_party: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger with colored console output and file logging.

    Args:
        log_dir: Directory to store log files
        logger_name: Name of the logger (use "root" for root logger)
        file_name: Name of the log file
        stream_level: Logging level for console output
        file_level: Logging level for file output
        file_mode: File open mode ('a' for append, 'w' for overwrite)
        log_filter: Optional filter to apply to the logger
        configure_third_party: Whether to configure third-party library loggers

    Returns:
        Configured logger instance
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get or create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(min(file_level, stream_level))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Colored console formatter
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-4s%(reset)s %(asctime)s [%(name)s] %(blue)s%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        style="%",
    )

    # Plain file formatter
    file_formatter = logging.Formatter(
        "%(levelname)-8s %(asctime)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    file_handler = logging.FileHandler(
        log_dir / file_name, encoding="utf-8", mode=file_mode
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(stream_level)
    console_handler.setFormatter(console_formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Add optional filter
    if log_filter is not None:
        logger.addFilter(log_filter)

    # Configure third-party loggers
    if configure_third_party:
        configure_third_party_loggers(stream_level)

    return logger


def configure_third_party_loggers(base_level: int = logging.INFO) -> None:
    """
    Configure logging levels for common third-party libraries to reduce noise.

    Args:
        base_level: Base logging level to use as reference
    """
    # OpenAI client logger - minimum INFO level
    logging.getLogger("openai._base_client").setLevel(max(logging.INFO, base_level))

    # httpx logger - minimum WARNING level to reduce verbosity
    logging.getLogger("httpx").setLevel(max(logging.WARNING, base_level))

    # httpcore logger - minimum INFO level
    logging.getLogger("httpcore").setLevel(max(logging.INFO, base_level))


# Backward compatibility alias
def _set_logger(
    exp_dir: Path,
    logger_name: str = "root",
    logging_level_stream: int = logging.INFO,
    logging_level_file: int = logging.INFO,
    logging_level: int | None = None,  # Alternative parameter name
    log_filter: logging.Filter | None = None,
    file_name: str = "experiment.log",
) -> logging.Logger:
    """
    Deprecated: Use setup_logger instead.

    Maintained for backward compatibility with existing code.
    """
    # Handle alternative parameter name
    if logging_level is not None:
        logging_level_stream = logging_level
        logging_level_file = logging_level

    return setup_logger(
        log_dir=exp_dir,
        logger_name=logger_name,
        file_name=file_name,
        stream_level=logging_level_stream,
        file_level=logging_level_file,
        file_mode="w",  # Original behavior was to overwrite
        log_filter=log_filter,
        configure_third_party=True,
    )
