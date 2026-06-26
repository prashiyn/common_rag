from __future__ import annotations

import json
import logging
from time import perf_counter

LOGGER = logging.getLogger("raqe")


def log_stage(stage: str, payload: dict) -> None:
    envelope = {"stage": stage, **payload}
    LOGGER.info("%s", json.dumps(envelope, sort_keys=True))


def start_timer() -> float:
    return perf_counter()


def elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)
