from signal import (
    SIGABRT,
    SIGINT,
    SIGTERM,
)

__all__ = ['HANDLED_SIGNALS']

HANDLED_SIGNALS = SIGINT, SIGTERM, SIGABRT
