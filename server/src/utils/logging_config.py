import logging
import os
import sys


def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Configure root logger with detailed format for debug logs
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Configure Dask loggers with DEBUG level
    dask_loggers = [
        "distributed",
        "distributed.worker",
        "distributed.scheduler",
        "distributed.nanny",
        "distributed.core",
        "distributed.protocol",
        "distributed.comm",
        "distributed.metrics",
        "dask",
        "dask.distributed",
    ]

    for logger_name in dask_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
                )
            )
