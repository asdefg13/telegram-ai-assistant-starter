"""Logging setup.

Plain stdlib logging on purpose: one line per event, no extra dependency, and
it reads well in `docker compose logs` as well as in a hosted log drain.
"""

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger once, at process start."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # These are chatty and rarely useful above WARNING in production.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
